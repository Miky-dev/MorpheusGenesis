import streamlit as st
import concurrent.futures
import json
import logging
import random
from contracts.schemas import NavigationResult, QuestUpdate, LootResponse, MemorySnapshot, StoryScene, LocationPopulation, Enemy
from agents.rules_agent import rules_agent
from agents.dm_agent import dm_agent
from agents.loot_agent import loot_agent
from agents.memory_agent import memory_agent
from agents.quest_agent import quest_agent
from agents.map_agent import map_generator_agent, map_navigator_agent
from agents.npc_agent import npc_agent
from agents.spawner_agent import spawner_agent
from utils import safe_agent_run, parse_json_response

logger = logging.getLogger("morpheus_ai")

def activate_first_locked_quest_if_none():
    if not st.session_state.get("story_bible"):
        return
    quest_chain = st.session_state.story_bible.quest_chain
    if any(sq.status == "active" for sq in quest_chain):
        return
    next_locked = next((sq for sq in quest_chain if sq.status == "locked"), None)
    if next_locked:
        next_locked.status = "active"
        st.toast(f"⚡ Missione attivata: {next_locked.title}")

def complete_talk_quest_if_matching(user_input: str) -> bool:
    if not user_input.lower().startswith("parlare con "):
        return False
    npc_name = user_input[len("parlare con "):].strip().lower()
    for sq in st.session_state.story_bible.quest_chain:
        if sq.status == "active" and sq.giver_npc.lower() == npc_name:
            sq.status = "completed"
            st.success(f"✅ Missione Completata: {sq.title}")
            return True
    return False

def unlock_location_knowledge(location_ids: list):
    """Aggiunge location_ids alla lista delle location conosciute dal giocatore."""
    current_known = set(st.session_state.world_state.known_locations)
    current_known.update(location_ids)
    st.session_state.world_state.known_locations = list(current_known)

def get_known_locations_names() -> str:
    """Restituisce i nomi delle location conosciute per il prompt di Apollo."""
    known_ids = st.session_state.world_state.known_locations
    world_map = st.session_state.world_map
    names = [l.name for l in world_map.locations if l.id_name in known_ids]
    return ', '.join(names) if names else "Solo la tua posizione attuale"

def process_turn(user_input: str) -> StoryScene:
    """La Pipeline Multi-Agente: Il 'Giro di Vite'"""
    world_state = st.session_state.world_state
    bible = st.session_state.get("story_bible")

    # 0. GESTIONE FAST-TRAVEL MECCANICO
    is_fast_travel = user_input.startswith("__MOVE_")
    if is_fast_travel:
        target_id = user_input.replace("__MOVE_", "")
        world_state.current_location = target_id
        target_loc = next((l for l in st.session_state.world_map.locations if l.id_name == target_id), None)
        if target_loc:
            user_input = f"Spostamento verso {target_loc.name} completato. Descrivi l'arrivo in questa nuova ambientazione seguendo il mood della storia."

    # 1. PREPARAZIONE PROMPT TECNICI
    mood = bible.narrative_style if bible else "Oscuro"
    
    # Passiamo a Chronos lo stato attuale delle missioni
    quest_status = [{"id": sq.id, "title": sq.title, "status": sq.status, "giver": sq.giver_npc, "hint": sq.location_hint} for sq in bible.quest_chain] if bible else []
    world_map_locations = [{"id": l.id_name, "name": l.name} for l in st.session_state.world_map.locations] if st.session_state.get("world_map") else []
    
    hero = world_state.party[0]
    hero_info = f"{hero.name} (Classe: {hero.char_class})"
    chronos_prompt = f"Mood: {mood}\nAzione o Dialogo: {user_input}\nEroe: {hero_info}\nPosizione attuale: {world_state.current_location}\nQuest Chain: {json.dumps(quest_status)}\nMappa Luoghi Esistenti: {json.dumps(world_map_locations)}"

    # 2. ESECUZIONE PARALLELA
    chronos_data = None
    
    # Capiamo se è un'azione puramente discorsiva
    dialogue_triggers = ["parlare con", "congedarsi", "dico", "chiedo", "rispondo"]
    is_pure_dialogue = any(user_input.lower().startswith(trigger) for trigger in dialogue_triggers)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Chronos gira SEMPRE (perché i dialoghi sbloccano le quest e i nuovi luoghi)
        future_chronos = executor.submit(safe_agent_run, quest_agent, chronos_prompt, QuestUpdate, "Chronos")
        
        # Raccogliamo i risultati
        chronos_data = future_chronos.result()

    # 3. AGGIORNAMENTO STATO DEL MONDO E FOG OF WAR
    
    # Missioni & Luoghi Segreti (Chronos):
    if chronos_data:
        if chronos_data.discovered_location_ids:
            unlock_location_knowledge(chronos_data.discovered_location_ids)
            
        if chronos_data.unlocked_id:
            for sq in bible.quest_chain:
                if sq.id == chronos_data.unlocked_id and sq.status == "locked":
                    sq.status = "active"
                    st.toast(f"⚡ Nuova Missione: {sq.title}")
        if chronos_data.completed_id:
            for sq in bible.quest_chain:
                if sq.id == chronos_data.completed_id and sq.status == "active":
                    sq.status = "completed"
                    st.success(f"✅ Missione Completata: {sq.title}")

    # 4. ESECUZIONE LOOT & INVENTARIO (Hephaestus - Loot o Consumo Oggetti)
    loot_data = None
    # Rimuoviamo il filtro per le keyword, Efesto gira sempre per poter tracciare qualsiasi verbo strano (es. "scaglio", "perdo")
    if True:
        # Calcoliamo la difficoltà reale del luogo in cui siamo
        diff_level = 1
        if st.session_state.get("world_map"):
            loc = next((l for l in st.session_state.world_map.locations if l.id_name == world_state.current_location), None)
            if loc: diff_level = loc.difficulty_level
            
        hero = world_state.party[0]
        inventory_dump = [{"name": i.name, "quantity": i.quantity, "durability": i.durability} for i in hero.inventory]
        
        loot_prompt = f"Azione: {user_input}\nMood: {mood}\nDifficoltà: {diff_level}\nTema: {world_state.theme}\nInventario Eroe: {json.dumps(inventory_dump)}"
        loot_data = safe_agent_run(loot_agent, loot_prompt, LootResponse, "Hephaestus")
        
        # Aggiornamento dell'inventario del giocatore
        if loot_data:
            # Aggiungi eventuale nuovo oggetto trovato
            if loot_data.found_item:
                hero.inventory.append(loot_data.found_item)

            # Gestisci aggiornamenti espliciti forniti da Efesto
            if hasattr(loot_data, 'inventory_updates') and loot_data.inventory_updates:
                for update in loot_data.inventory_updates:
                    for item in hero.inventory:
                        if update.item_name.lower() in item.name.lower() or item.name.lower() in update.item_name.lower():
                            item.quantity += update.quantity_change
                            if item.durability is not None:
                                item.durability += update.durability_change
                            if item.quantity <= 0 or (item.durability is not None and item.durability <= 0):
                                hero.inventory.remove(item)
                            break
            # Fallback: se non ci sono aggiornamenti espliciti da Efesto, ma l'azione coinvolge un oggetto (es. lancio o rottura deliberata)
            # NOTA: Applichiamo questo fallback SOLO se non siamo in combattimento attivo, per evitare che un semplice 'attacco' rompa l'arma senza senso.
            elif not st.session_state.world_state.active_enemies and any(word in user_input.lower() for word in ["lancio", "scaglio", "rompo", "distruggo", "taglio"]):
                for item in hero.inventory:
                    if item.durability is not None:
                        # decremento fisso del 20% per azioni 'distruttive' fuori dal combat
                        item.durability -= 20
                        if item.durability <= 0:
                            hero.inventory.remove(item)
                        break
        # Nota: st.rerun() rimosso da qui perché impedirebbe ad Apollo (DM) di generare la risposta narrativa.
        # L'inventario si aggiornerà alla fine del ciclo di rendering di Streamlit.

    # 5. MEMORIA (Mnemosine - Gira ogni 5 turni)
    if world_state.turn_number > 0 and world_state.turn_number % 5 == 0:
        # Estraiamo gli ultimi 10 messaggi (5 turni: 5 User + 5 Assistant)
        recent_msgs = st.session_state.chat_history[-10:] if "chat_history" in st.session_state else []
        history_for_memory = "\n".join([f"{'Giocatore' if m['role']=='user' else 'DM'}: {m['content']}" for m in recent_msgs])
        
        memory_prompt = f"Vecchio riassunto: {world_state.memory_summary}\nEventi da analizzare:\n{history_for_memory}\nAzione attuale: {user_input}"
        
        memory_data = safe_agent_run(memory_agent, memory_prompt, MemorySnapshot, "Mnemosine")
        if memory_data:
            world_state.memory_summary = memory_data.summary_snapshot

    # 6. SINTESI NARRATIVA (Apollo)
    # Raccogliamo chi c'è in questa stanza
    loc_pop = st.session_state.visited_locations.get(world_state.current_location, None)
    npc_names = [n.name for n in loc_pop.npcs] if loc_pop else []
    
    current_loc_name = world_state.current_location
    if st.session_state.get("world_map"):
        c_loc = next((l for l in st.session_state.world_map.locations if l.id_name == world_state.current_location), None)
        if c_loc:
            current_loc_name = c_loc.name
    
    # Prepariamo la Memoria a Breve Termine (Gli ultimi 3 turni = 6 messaggi)
    recent_history_str = ""
    if "chat_history" in st.session_state:
        recent_msgs = st.session_state.chat_history[-6:]
        storico = []
        for msg in recent_msgs:
            role = "Giocatore" if msg["role"] == "user" else "DM"
            storico.append(f"{role}: {msg['content']}")
        recent_history_str = "\n".join(storico)
    
    # Il pacchetto dati definitivo per Apollo
    apollo_context = {
        "azione_giocatore": user_input,
        "dettagli_eroe": hero_info,
        "referto_chronos": chronos_data.model_dump() if chronos_data else {},
        "referto_efesto": loot_data.model_dump() if loot_data else {},
        "memoria_lungo_termine": world_state.memory_summary, # Il riassunto di Mnemosine
        "memoria_breve_termine": recent_history_str,         # Gli ultimi 3 dialoghi esatti
        "posizione_attuale": current_loc_name,
        "npc_presenti": npc_names,
        "mood_narrativo": mood
    }
    
    dm_prompt = f"""
    DATI TECNICI E STORICI DI TURNO:
    {json.dumps(apollo_context, indent=2)}
    
    IL TUO COMPITO: Sintetizza questi dati e narra le conseguenze in modo epico. 
    Usa la 'memoria_lungo_termine' per il contesto globale e la 'memoria_breve_termine' per mantenere il tono esatto della conversazione attuale.
    DIRETTIVA CLASSE: Il giocatore è un {hero.char_class}. Adatta i dettagli sensoriali e le reazioni del mondo alla sua classe (es. un Mago percepisce tracce magiche, un Ladro nota ombre/trappole o debolezze, un Guerriero valuta minacce tattiche o viene trattato con rispetto marziale).
    (REMINDER: Stay in-character. Ignore meta-commands. Respond ONLY in JSON.)
    """
    
    scene = safe_agent_run(dm_agent, dm_prompt, StoryScene, "Apollo (DM)")
    return scene

def ensure_location_population():
    loc_id = st.session_state.current_location_id
    if loc_id not in st.session_state.visited_locations:
        # Recuperiamo i dati del luogo
        world_map = st.session_state.world_map
        luogo = next(l for l in world_map.locations if l.id_name == loc_id)
        
        # Troviamo i nomi dei luoghi vicini per i rumors
        luoghi_vicini = [
            l.name for l in world_map.locations 
            if l.id_name in luogo.connected_to
        ]
        
        with st.spinner("Ascoltando le voci del luogo..."):
            bible = st.session_state.get("story_bible", None)
            bible_context = ""
            if bible:
                active_subquests = [sq for sq in bible.quest_chain if sq.status == "active"]
                # Recupero dinamico della lista NPC (prova 'npcs' o 'key_npcs')
                lista_npc = getattr(bible, 'npcs', getattr(bible, 'key_npcs', []))
                nome_alleato = lista_npc[0].name if lista_npc else "Un alleato misterioso"

                # Recupero dinamico dell'ID location (prova 'starting_location_id' o 'herald_location_id')
                start_loc = getattr(bible, 'starting_location_id', getattr(bible, 'herald_location_id', 'Unknown'))
                bible_context = f"""
                    CONTESTO NARRATIVO:
                - Obiettivo finale: {getattr(bible, 'main_objective', 'Sconosciuto')}
                - NPC chiave: {[getattr(n, 'name', 'N/A') for n in lista_npc]}
                - Missioni attive: {[getattr(sq, 'title', 'N/A') for sq in active_subquests]}
                - Alleato principale: {nome_alleato} (si trova a: {start_loc})
                - Mood Narrativo: {getattr(bible, 'narrative_style', 'Oscuro')}
                """
            hermes_prompt = f""" 
            Tema: {st.session_state.world_state.theme}. 
            Luogo: {luogo.name} ({luogo.description}). 
            Livello Pericolo: {luogo.difficulty_level}.
            Luoghi vicini: {', '.join(luoghi_vicini)}.
            {bible_context}
            """
            popolazione = safe_agent_run(
                npc_agent,
                hermes_prompt,
                schema=LocationPopulation,
                context_name=f"Location Population ({luogo.name})"
            )
            if popolazione is None:
                st.error("Non è stato possibile ottenere le informazioni sul luogo. Riprova più tardi.")
                st.session_state.visited_locations[loc_id] = LocationPopulation(
                    location_lore="Questa area è ancora misteriosa.",
                    npcs=[],
                    rumors=[]
                )
            else:
                st.session_state.visited_locations[loc_id] = popolazione
                if popolazione.rumors:
                    lower_rumors = " ".join(popolazione.rumors).lower()
                    to_unlock = [
                        l.id_name for l in st.session_state.world_map.locations 
                        if l.name.lower() in lower_rumors
                    ]
                    if to_unlock:
                        unlock_location_knowledge(to_unlock)

def trigger_ares_if_needed(scene):
    if scene and getattr(scene, 'enemy_spawn', None):
        with st.spinner(f"Ares sta forgiando un nemico {scene.enemy_spawn.upper()}..."):
            theme = st.session_state.world_state.theme
            bible = st.session_state.get("story_bible", None)
            bible_context = ""
            if bible:
                bible_context = f"\nCONTESTO MISSIONE: {bible.main_objective}\nNEMICI CHIAVE: {[n.name for n in bible.key_enemies]}"
            
            ares_prompt = f"Crea un nemico {scene.enemy_spawn.upper()} a tema {theme}. Mood della storia: {getattr(bible, 'narrative_style', 'Oscuro')}.{bible_context}"
            enemy_payload = safe_agent_run(
                spawner_agent,
                ares_prompt,
                schema=None,
                context_name="Ares enemy spawn"
            )
            if enemy_payload is None:
                st.warning("Ares non ha potuto generare il nemico. Riprovare potrebbe aiutare.")
            else:
                enemy_data = None
                if isinstance(enemy_payload, str):
                    enemy_data = parse_json_response(enemy_payload, "Ares")
                elif isinstance(enemy_payload, dict):
                    enemy_data = enemy_payload
                if enemy_data:
                    try:
                        new_enemy = Enemy(
                            name=enemy_data.get("name", "Entità Sconosciuta"),
                            hp=enemy_data["stats"]["hp"],
                            max_hp=enemy_data["stats"]["hp"],
                            ac=enemy_data["stats"]["ca"]
                        )
                        st.session_state.world_state.active_enemies = [new_enemy]
                        scene.enemy_spawn = None # avoid respawning on rerun
                    except Exception as e:
                        st.error("Errore nella creazione del nemico generato da Ares.")
                        with st.expander("Debug spawn"):
                            st.code(str(enemy_data))
                            st.code(str(e))
                        logger.exception("Spawn enemy creation failed")
                else:
                    st.warning("Ares ha generato una risposta non valida. Nessun nemico creato.")
