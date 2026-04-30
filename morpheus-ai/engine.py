import streamlit as st
import concurrent.futures
import json
import logging
import random
from contracts.schemas import NavigationResult, QuestUpdate, LootResponse, MemorySnapshot, StoryScene, LocationPopulation, Enemy, RulesCheck
from agents.rules_agent import rules_agent
from agents.dm_agent import dm_agent
from agents.loot_agent import generate_random_loot
from agents.lore_agent import lore_agent
from utils import safe_agent_run, parse_json_response

logger = logging.getLogger("morpheus_ai")

# --- NUOVA FUNZIONE: GESTIONE DEI TURNI MULTIPLAYER ---
def advance_turn():
    """Sposta l'active_player_id al giocatore successivo nel party."""
    # Controllo di sicurezza: se la sessione non è ancora inizializzata, esci.
    if "world_state" not in st.session_state or not st.session_state.world_state.party:
        return

    party = st.session_state.world_state.party
    
    # Se per qualche motivo active_player_id non esiste, settalo al primo
    if "active_player_id" not in st.session_state or st.session_state.active_player_id is None:
        st.session_state.active_player_id = party[0].id
        return

    current_index = 0
    # Troviamo l'indice del giocatore che ha appena agito
    for i, char in enumerate(party):
        if char.id == st.session_state.active_player_id:
            current_index = i
            break
            
    # Calcoliamo il prossimo indice (ritornando a 0 se siamo all'ultimo)
    next_index = (current_index + 1) % len(party)
    
    # Aggiorniamo lo stato
    st.session_state.active_player_id = party[next_index].id


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
    # Rimuoviamo il prefisso e eventuali riferimenti al nome del giocatore che abbiamo aggiunto
    # es: "[Valerius]: parlare con..."
    input_text = user_input.lower()
    if "]: " in input_text:
        input_text = input_text.split("]: ")[1]
        
    npc_name = input_text[len("parlare con "):].strip()
    
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

def process_turn(user_input: str, bypass_rules: bool = False) -> StoryScene:
    """La Pipeline Multi-Agente: Il 'Giro di Vite'"""
    world_state = st.session_state.world_state
    bible = st.session_state.get("story_bible")

    # --- MODIFICA: IDENTIFICA IL GIOCATORE ATTIVO ---
    # Invece di usare sempre party[0], cerchiamo il giocatore il cui turno è attualmente in corso.
    # Se fallisce per qualche motivo di init, fa un fallback su party[0]
    active_player = next((p for p in world_state.party if p.id == st.session_state.get("active_player_id")), world_state.party[0])

    # 0. GESTIONE FAST-TRAVEL MECCANICO
    is_fast_travel = user_input.startswith("__MOVE_")
    if is_fast_travel:
        target_id = user_input.replace("__MOVE_", "")
        world_state.current_location = target_id
        target_loc = next((l for l in st.session_state.world_map.locations if l.id_name == target_id), None)
        if target_loc:
            # Modificato per includere chi si sposta
            user_input = f"[{active_player.name}]: Spostamento verso {target_loc.name} completato. Descrivi l'arrivo in questa nuova ambientazione seguendo il mood della storia."
    else:
        # ==========================================
        # FASE 3: IL CONTROLLO REGOLE (ARBITRO)
        # ==========================================
        if not bypass_rules and not st.session_state.world_state.active_enemies:
            rules_prompt = f"""
            SEI IL MAESTRO DELLE REGOLE (ARBITRO) DI UN GIOCO SIMILE A D&D.
            GIOCATORE ATTIVO: {active_player.name} (Classe: {active_player.char_class})
            AZIONE RICHIESTA: "{user_input}"
            
            IL TUO COMPITO:
            Analizza l'azione del giocatore. 
            - Se è una normale conversazione ("Ciao oste"), un'osservazione ("Guardo la stanza") o un'azione automatica ("Mi siedo"), NON richiede un tiro.
            - Se l'azione ha un rischio di fallimento, richiede uno sforzo fisico, destrezza, conoscenza o abilità sociale (es. rubare, mentire, saltare, decifrare, sfondare, muoversi in modo furtivo), ALLORA richiede un tiro.
            
            Scegli la caratteristica più adatta tra: Forza, Destrezza, Costituzione, Intelligenza, Saggezza, Carisma.
            Scegli una CD (Classe Difficoltà) tra 10 (Facile) e 20 (Molto Difficile).
            
            REGOLE JSON TASSATIVE:
            - Restituisci ESCLUSIVAMENTE un oggetto JSON con questo schema:
            {{
              "richiede_tiro": true/false,
              "caratteristica": "Nome Caratteristica o null",
              "cd_suggerita": numero o null,
              "motivo": "Spiegazione breve o null"
            }}
            """
            
            with st.spinner("Il Game Master sta valutando l'azione..."):
                try:
                    rules_response = safe_agent_run(rules_agent, rules_prompt, schema=RulesCheck, context_name="Arbitro Regole")
                    
                    if rules_response and rules_response.richiede_tiro:
                        # Blocchiamo l'engine e salviamo la richiesta di tiro in sessione
                        st.session_state.pending_skill_check = {
                            "caratteristica": rules_response.caratteristica,
                            "cd": rules_response.cd_suggerita,
                            "motivo": rules_response.motivo,
                            "azione_originale": user_input
                        }
                        # Ritorniamo una scena "fittizia" per fermare la narrazione
                        return StoryScene(
                            narration=f"🎲 Il DM richiede una prova di {rules_response.caratteristica} per: {rules_response.motivo}.", 
                            choices=[], 
                            is_combat=False, 
                            allow_free_action=False
                        )
                except Exception as e:
                    logger.error(f"Errore nel check delle regole: {e}")
        # ==========================================

    # 1. PREPARAZIONE PROMPT TECNICI
    mood = bible.narrative_style if bible else "Oscuro"
    
    # Passiamo a Chronos lo stato attuale delle missioni
    quest_status = [{"id": sq.id, "title": sq.title, "status": sq.status, "giver": sq.giver_npc, "hint": sq.location_hint} for sq in bible.quest_chain] if bible else []
    world_map_locations = [{"id": l.id_name, "name": l.name} for l in st.session_state.world_map.locations] if st.session_state.get("world_map") else []
    
    # --- MODIFICA: L'INFO DEVE ESSERE SUL GIOCATORE ATTIVO ---
    hero_info = f"{active_player.name} (Classe: {active_player.char_class})"
    chronos_prompt = f"Mood: {mood}\nAzione o Dialogo: {user_input}\nPersonaggio Attivo: {hero_info}\nPosizione attuale: {world_state.current_location}\nQuest Chain: {json.dumps(quest_status)}\nMappa Luoghi Esistenti: {json.dumps(world_map_locations)}"

    # 2. ESECUZIONE PARALLELA
    chronos_data = None
    
    dialogue_triggers = ["parlare con", "congedarsi", "dico", "chiedo", "rispondo"]
    is_pure_dialogue = any(user_input.lower().startswith(trigger) for trigger in dialogue_triggers)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_chronos = executor.submit(safe_agent_run, lore_agent, chronos_prompt, None, "Lore/Chronos")
        chronos_data = None  # gestione quest procedurale sotto
        future_chronos.result() 

    # 3. AGGIORNAMENTO STATO DEL MONDO E FOG OF WAR
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
    if True:
        diff_level = 1
        if st.session_state.get("world_map"):
            loc = next((l for l in st.session_state.world_map.locations if l.id_name == world_state.current_location), None)
            if loc: diff_level = loc.difficulty_level
            
        # --- MODIFICA: GLI OGGETTI VANNO NELLO ZAINO DEL GIOCATORE ATTIVO ---
        inventory_dump = [{"name": i.name, "quantity": i.quantity, "durability": i.durability} for i in active_player.inventory]
        
        loot_dict = generate_random_loot(diff_level, world_state.theme, user_input)
        try:
            loot_data = LootResponse(**loot_dict) if loot_dict else None
        except Exception:
            loot_data = None
        
        if loot_data:
            if loot_data.found_item:
                active_player.inventory.append(loot_data.found_item)
                st.toast(f"🎒 {active_player.name} ha trovato: {loot_data.found_item.name}!")

            if hasattr(loot_data, 'inventory_updates') and loot_data.inventory_updates:
                for update in loot_data.inventory_updates:
                    for item in active_player.inventory:
                        if update.item_name.lower() in item.name.lower() or item.name.lower() in update.item_name.lower():
                            item.quantity += update.quantity_change
                            if item.durability is not None:
                                item.durability += update.durability_change
                            if item.quantity <= 0 or (item.durability is not None and item.durability <= 0):
                                active_player.inventory.remove(item)
                            break
                            
            elif not st.session_state.world_state.active_enemies and any(word in user_input.lower() for word in ["lancio", "scaglio", "rompo", "distruggo", "taglio"]):
                for item in active_player.inventory:
                    if item.durability is not None:
                        item.durability -= 20
                        if item.durability <= 0:
                            active_player.inventory.remove(item)
                        break

    # 5. MEMORIA 
    pass

    # 6. SINTESI NARRATIVA (Apollo)
    loc_pop = st.session_state.visited_locations.get(world_state.current_location, None)
    npc_names = [n.name for n in loc_pop.npcs] if loc_pop else []
    
    current_loc_name = world_state.current_location
    if st.session_state.get("world_map"):
        c_loc = next((l for l in st.session_state.world_map.locations if l.id_name == world_state.current_location), None)
        if c_loc:
            current_loc_name = c_loc.name
    
    recent_history_str = ""
    if "chat_history" in st.session_state:
        recent_msgs = st.session_state.chat_history[-6:]
        storico = []
        for msg in recent_msgs:
            role = "Giocatore" if msg["role"] == "user" else "DM"
            storico.append(f"{role}: {msg['content']}")
        recent_history_str = "\n".join(storico)
    
    apollo_context = {
        "azione_giocatore": user_input,
        "dettagli_personaggio_attivo": hero_info, # Modificato il nome per chiarezza
        # --- AGGIUNTA IMPORTANTE: STATO DEL PARTY PER IL DM ---
        "stato_party": [f"{p.name} ({p.char_class}) - HP: {p.hp}/{p.max_hp}" for p in world_state.party],
        "referto_chronos": chronos_data.model_dump() if chronos_data else {},
        "referto_efesto": loot_data.model_dump() if loot_data else {},
        "memoria_lungo_termine": world_state.memory_summary, 
        "memoria_breve_termine": recent_history_str,         
        "posizione_attuale": current_loc_name,
        "npc_presenti": npc_names,
        "mood_narrativo": mood
    }
    
    dm_prompt = f"""
    DATI TECNICI E STORICI DI TURNO:
    {json.dumps(apollo_context, indent=2)}
    
    IL TUO COMPITO: Sintetizza questi dati e narra le conseguenze in modo epico. 
    Usa la 'memoria_lungo_termine' per il contesto globale e la 'memoria_breve_termine' per mantenere il tono esatto della conversazione attuale.
    
    ATTENZIONE ALLE PROVE DI ABILITÀ: Se nell'azione del giocatore vedi un "[RISULTATO DADO: ...]", DEVI narrare ESATTAMENTE quell'esito. Se c'è scritto SUCCESSO, il giocatore riesce in modo spettacolare. Se c'è scritto FALLIMENTO, il giocatore sbaglia e ne subisce le conseguenze negative.
    
    DIRETTIVA PARTY: Il party è composto da vari avventurieri (vedi 'stato_party'). L'azione in corso è eseguita SPECIFICAMENTE da {active_player.name}. 
    DIRETTIVA CLASSE: Adatta i dettagli sensoriali e le reazioni del mondo alla classe di {active_player.name} ({active_player.char_class}).
    
    REGOLE JSON TASSATIVE:
    - Rispondi SOLO in JSON seguendo questo schema:
    {{
      "narration": "Testo della narrazione...",
      "choices": ["Opzione 1", "Opzione 2"],
      "is_combat": false,
      "allow_free_action": true,
      "enemy_spawn": null
    }}
    """
    
    scene = safe_agent_run(dm_agent, dm_prompt, StoryScene, "Apollo (DM)")
    return scene

def ensure_location_population():
    loc_id = st.session_state.current_location_id
    if loc_id not in st.session_state.visited_locations:
        world_map = st.session_state.world_map
        luogo = next(l for l in world_map.locations if l.id_name == loc_id)
        
        luoghi_vicini = [
            l.name for l in world_map.locations 
            if l.id_name in luogo.connected_to
        ]
        
        with st.spinner("Ascoltando le voci del luogo..."):
            bible = st.session_state.get("story_bible", None)
            bible_context = ""
            if bible:
                active_subquests = [sq for sq in bible.quest_chain if sq.status == "active"]
                lista_npc = getattr(bible, 'npcs', getattr(bible, 'key_npcs', []))
                nome_alleato = lista_npc[0].name if lista_npc else "Un alleato misterioso"

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
                lore_agent,
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
        with st.spinner(f"Generazione nemica procedurale ({scene.enemy_spawn.upper()})..."):
            theme = st.session_state.world_state.theme
            
            enemy_name = f"Nemico {theme} {scene.enemy_spawn.capitalize()}"
            hp = 20 if scene.enemy_spawn == "base" else 50
            ac = 12 if scene.enemy_spawn == "base" else 15
            
            new_enemy = Enemy(
                name=enemy_name,
                hp=hp,
                max_hp=hp,
                ac=ac
            )
            st.session_state.world_state.active_enemies = [new_enemy]
            scene.enemy_spawn = None

def genera_scena_di_apertura(active_player) -> StoryScene:
    """Genera la prima vera descrizione del mondo e l'evento scatenante."""
    world_state = st.session_state.world_state
    bible = st.session_state.story_bible
    
    # Recuperiamo il nome del luogo di spawn
    loc_id = st.session_state.current_location_id
    ensure_location_population() # Ci assicuriamo di sapere chi c'è
    pop = st.session_state.visited_locations[loc_id]
    luogo = next(l for l in st.session_state.world_map.locations if l.id_name == loc_id)

    # Prompt specifico per l'Inizio Avventura
    prompt_apertura = f"""
    SEI IL DUNGEON MASTER. QUESTA È LA PRIMA SCENA DELLA CAMPAGNA.
    
    CONTESTO MONDIALE:
    - Titolo: {bible.title}
    - Mood: {bible.narrative_style}
    - Cinematic Precedente: {bible.opening_cinematic}
    
    SITUAZIONE ATTUALE:
    - Luogo: {luogo.name} ({luogo.description})
    - NPC presenti: {[n.name for n in pop.npcs]}
    - Party: {[p.name + ' (' + p.char_class + ')' for p in world_state.party]}
    
    IL TUO COMPITO:
    1. Descrivi l'ambiente circostante con dettagli sensoriali (odori, suoni, luci).
    2. Spiega come e perché il party si trova lì insieme in questo momento.
    3. Introduci un EVENTO IMPROVVISO (il Gancio) che interrompe la quiete.
    4. Concludi rivolgendoti a {active_player.name} chiedendo: "Cosa fai?"
    
    REGOLE JSON TASSATIVE:
    - Rispondi ESCLUSIVAMENTE in JSON seguendo questo schema:
    {{
      "narration": "Testo della narrazione...",
      "choices": ["Opzione 1", "Opzione 2"],
      "is_combat": false,
      "allow_free_action": true,
      "enemy_spawn": null
    }}
    """

    return safe_agent_run(dm_agent, prompt_apertura, schema=StoryScene, context_name="Apertura Avventura")