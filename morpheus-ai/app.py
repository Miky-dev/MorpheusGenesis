import streamlit as st
import json
import logging
import re
from dotenv import load_dotenv
import os
import random

import concurrent.futures
from contracts.schemas import NavigationResult, QuestUpdate, LootResponse, MemorySnapshot

# Import dei vostri moduli
from agents.rules_agent import rules_agent
from agents.dm_agent import dm_agent
from agents.loot_agent import loot_agent
from agents.memory_agent import memory_agent
from agents.quest_agent import quest_agent
from agents.map_agent import map_generator_agent, map_navigator_agent
from agents.npc_agent import npc_agent
from dataclasses import asdict
from agents.spawner_agent import spawner_agent
from agents.lore_agent import generate_story_bible, save_bible_to_memory
from knowledge.chroma_store import DungeonMemory
from contracts.schemas import WorldState, Character, Enemy, StoryScene, WorldMap, LocationPopulation, StoryBible
from setup_page import render_setup_page

# Caricamento variabili d'ambiente
load_dotenv()

CLASS_MOVES = {
    "Warrior": [
        {"name": "Attacco Pesante", "damage": "1d10+4", "desc": "Un fendente brutale."},
        {"name": "Scudo d'Acciaio", "damage": "1d4+4", "desc": "Colpisci col bordo dello scudo."}
    ],
    "Mage": [
        {"name": "Dardo Incantato", "damage": "2d4+5", "desc": "Dardi di pura energia magica."},
        {"name": "Esplosione Arcana", "damage": "1d12+2", "desc": "Un'onda d'urto distruttiva."}
    ],
    "Rogue": [
        {"name": "Attacco Furtivo", "damage": "1d6+6", "desc": "Colpisci i punti vitali."},
        {"name": "Lama Veloce", "damage": "2d4+3", "desc": "Due fendenti rapidissimi."}
    ]
}


logger = logging.getLogger("morpheus_ai")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

required_env_vars = ["GROQ_API_KEY", "GOOGLE_API_KEY"]
missing_env = [var for var in required_env_vars if not os.environ.get(var)]
if missing_env:
    st.error(
        "Variabili d'ambiente mancanti: "
        + ", ".join(missing_env)
        + ". Copia `.env.example` in `.env` e aggiungi le chiavi richieste."
    )
    logger.error("Missing environment variables: %s", missing_env)
    st.stop()

if "page" not in st.session_state:
    st.session_state.page = "setup"

if st.session_state.page == "setup":
    render_setup_page()
    st.stop() # Ferma l'esecuzione qui, non disegna il resto del gioco


def extract_first_json(raw: str) -> str:
    start = raw.find("{")
    if start == -1:
        return raw

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(raw)):
        char = raw[index]
        if char == '"' and not escape:
            in_string = not in_string
        if char == '\\' and not escape:
            escape = True
            continue
        escape = False

        if not in_string:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return raw[start:index + 1]
    return raw


def normalize_agent_output(raw: str) -> str:
    if not isinstance(raw, str):
        return ""
    cleaned = raw.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    cleaned = extract_first_json(cleaned)
    return cleaned


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


def parse_json_response(raw: str, context: str = ""):
    if not isinstance(raw, str):
        return None
    raw = normalize_agent_output(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        fallback = extract_first_json(raw)
        if fallback != raw:
            try:
                return json.loads(fallback)
            except json.JSONDecodeError:
                pass
        st.error(f"Risposta non valida da {context}. Riprova.")
        with st.expander("Debug risposta LLM"):
            st.code(raw)
            st.code(str(exc))
        logger.error("JSON decode failed for %s: %s", context, exc)
        return None


def safe_agent_run(agent, prompt, schema=None, context_name=""):
    try:
        result = agent.run(prompt)
        content = getattr(result, "content", result)
        raw = normalize_agent_output(content) if isinstance(content, str) else content
        if schema:
            if isinstance(raw, str):
                try:
                    if hasattr(schema, "model_validate_json"):
                        return schema.model_validate_json(raw)
                    return schema(**json.loads(raw))
                except Exception as exc:
                    parsed = parse_json_response(raw, context_name)
                    if parsed is not None:
                        try:
                            if hasattr(schema, "model_validate"):
                                return schema.model_validate(parsed)
                            return schema(**parsed)
                        except Exception as exc2:
                            exc = exc2
                    st.error(f"Errore di validazione della risposta {context_name}. Controlla il formato della risposta.")
                    with st.expander("Debug validazione"):
                        st.code(raw)
                        st.code(str(exc))
                    logger.error("Schema validation failed for %s: %s", context_name, exc)
                    return None
            elif isinstance(raw, dict):
                try:
                    if hasattr(schema, "model_validate"):
                        return schema.model_validate(raw)
                    return schema(**raw)
                except Exception as exc:
                    st.error(f"Errore di validazione della risposta {context_name}. Controlla il formato della risposta.")
                    with st.expander("Debug validazione"):
                        st.code(raw)
                        st.code(str(exc))
                    logger.error("Schema validation failed for %s: %s", context_name, exc)
                    return None
        return raw
    except Exception as exc:
        st.error(f"Errore durante la chiamata {context_name}. Riprova.")
        with st.expander("Debug errore agente"):
            st.code(str(exc))
        logger.exception("Agent run failed for %s", context_name)
        return None


#Inizializziamo la memoria PRIMA della generazione del mondo
if "memory" not in st.session_state:
    st.session_state.memory = DungeonMemory(session_id="test_session_001")


def resolve_combat_round(move_name, d20_roll=None):
    hero = st.session_state.world_state.party[0]
    enemy = st.session_state.world_state.active_enemies[0]
    
    # 1. TURNO GIOCATORE: d20 + bonus (fisso a +4 per ora) vs CA Nemico
    roll = d20_roll if d20_roll is not None else random.randint(1, 20)
    total_atk = roll + 4
    hit = total_atk >= enemy.ac
    
    if hit:
        dmg = random.randint(4, 12) # Danno variabile
        enemy.hp -= dmg
        st.session_state.world_state.combat_log.append(f"💥 **{hero.name}** usa {move_name}: COLPITO! ({total_atk} vs CA {enemy.ac}) per {dmg} danni.")
    else:
        st.session_state.world_state.combat_log.append(f"🛡️ **{hero.name}** usa {move_name}: MANCATO! ({total_atk} vs CA {enemy.ac}).")

    if enemy.hp <= 0:
        enemy.hp = 0
        st.session_state.world_state.combat_log.append(f"💀 **{enemy.name}** è stato sconfitto!")
        return "vittoria"

    # 2. TURNO NEMICO: Il nemico attacca sempre dopo il giocatore
    e_roll = random.randint(1, 20)
    e_total = e_roll + 3
    if e_total >= hero.ac:
        e_dmg = random.randint(3, 8)
        hero.hp -= e_dmg
        st.session_state.world_state.combat_log.append(f"⚠️ **{enemy.name}** colpisce: {e_dmg} danni subiti!")
    else:
        st.session_state.world_state.combat_log.append(f"💨 **{enemy.name}** manca il colpo.")
    
    return "continua"


# 1. Inizializzazione Session State (Membro B)
if "world_state" not in st.session_state:
    # Recuperiamo i dati dalla Setup Page
    p1_name = st.session_state.get("setup_p1_name", "Valerius")
    p1_class = st.session_state.get("setup_p1_class", "Warrior")
    theme = st.session_state.get("setup_theme", "Medievale")
    
    # --- Generazione Story Bible (La Musa) PRIMA di tutto ---
    if "story_bible" not in st.session_state:
        with st.spinner("📖 La Musa sta scrivendo la storia del mondo..."):
            # Generiamo la nuova bibbia usando i parametri dello state
            bible = generate_story_bible(
                theme_id=theme,
                theme_description=f"Un mondo oscuro ed epico a tema {theme}",
                difficulty="Normale",
                session_name=f"Le Cronache di {p1_name}",
                session_id="test_session_001"
            )
            
            # Salviamo la Bible nella memoria ChromaDB per gli altri agenti
            save_bible_to_memory(bible, st.session_state.memory)
            
            st.session_state.story_bible = bible
            activate_first_locked_quest_if_none()

    # --- Generazione Mappa (Atlas) ---
    if "world_map" not in st.session_state:
        with st.spinner("Atlas sta disegnando i confini del mondo..."):
            bible = st.session_state.story_bible
            # NOTA: Ho cambiato herald_location_id in starting_location_id per rispettare la nuova dataclass
            map_prompt = f"Tema: {theme}. Titolo avventura: {bible.title}. Hub iniziale: {bible.herald_location_id}. Genera una mappa coerente."
            world_map = safe_agent_run(
                map_generator_agent,
                map_prompt,
                schema=WorldMap,
                context_name="World Map"
            )
            if world_map is None:
                st.stop()
            st.session_state.world_map = world_map

            st.session_state.current_location_id = st.session_state.world_map.spawn_location_id
    
    
    # Inizializziamo il registro delle location visitate
    if "visited_locations" not in st.session_state:
        st.session_state.visited_locations = {}

    # Creiamo uno stato iniziale basato sull'input
    hero = Character(name=p1_name, char_class=p1_class, hp=24, max_hp=24)
    
    st.session_state.world_state = WorldState(
        theme=theme,
        party=[hero],
        active_enemies=[],
        current_location=st.session_state.current_location_id
    )
    
    # Sblocco location iniziali: spawn + vicini diretti visibili
    if st.session_state.world_map:
        spawn_loc = next((l for l in st.session_state.world_map.locations 
                          if l.id_name == st.session_state.current_location_id), None)
        if spawn_loc:
            initial_known = [spawn_loc.id_name] + spawn_loc.connected_to
            st.session_state.world_state.known_locations = list(set(initial_known))

if "last_narrative" not in st.session_state:
    st.session_state.last_narrative = ""

if "current_scene" not in st.session_state:
    st.session_state.current_scene = None  # Conterrà l'ultimo StoryScene

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None

if "pending_combat_move" not in st.session_state:
    st.session_state.pending_combat_move = None

if "current_user_input" not in st.session_state:
    st.session_state.current_user_input = ""

if "cinematic_seen" not in st.session_state:
    st.session_state.cinematic_seen = False


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

    # 1. PREPARAZIONE PROMPT TECNICI
    atlas_prompt = f"Azione: {user_input}\nPosizione attuale: {world_state.current_location}\nLocation conosciute: {world_state.known_locations}"
    
    # Passiamo a Chronos lo stato attuale delle missioni
    quest_status = [{"id": sq.id, "status": sq.status, "giver": sq.giver_npc, "hint": sq.location_hint} for sq in bible.quest_chain] if bible else []
    chronos_prompt = f"Azione: {user_input}\nPosizione attuale: {world_state.current_location}\nQuest Chain: {json.dumps(quest_status)}"

    # 2. ESECUZIONE PARALLELA (Atlas & Chronos girano nello stesso momento)
    atlas_data = None
    chronos_data = None
    
    # Capiamo se è un'azione puramente discorsiva
    dialogue_triggers = ["parlare con", "congedarsi", "dico", "chiedo", "rispondo"]
    is_pure_dialogue = any(user_input.lower().startswith(trigger) for trigger in dialogue_triggers)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Chronos gira SEMPRE (perché i dialoghi sbloccano le quest)
        future_chronos = executor.submit(safe_agent_run, quest_agent, chronos_prompt, QuestUpdate, "Chronos")
        
        # Atlas gira SOLO se NON è un dialogo puro
        future_atlas = None
        if not is_pure_dialogue:
            future_atlas = executor.submit(safe_agent_run, map_navigator_agent, atlas_prompt, NavigationResult, "Atlas")        
        # Raccogliamo i risultati
        chronos_data = future_chronos.result()
        if future_atlas:
            atlas_data = future_atlas.result()

    # 3. AGGIORNAMENTO STATO DEL MONDO
    # Mappa:
    if atlas_data and atlas_data.success and atlas_data.new_location_id:
        world_state.current_location = atlas_data.new_location_id
    if atlas_data and atlas_data.discovered_ids:
        unlock_location_knowledge(atlas_data.discovered_ids)

    # Missioni:
    if chronos_data:
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

    # 4. ESECUZIONE LOOT (Hephaestus - Solo se l'utente cerca qualcosa)
    loot_data = None
    loot_keywords = ["cerco", "apro", "depredo", "frugo", "esamino", "ispeziono", "bottino", "ispeziona"]
    if any(word in user_input.lower() for word in loot_keywords):
        # Calcoliamo la difficoltà reale del luogo in cui siamo
        diff_level = 1
        if st.session_state.get("world_map"):
            loc = next((l for l in st.session_state.world_map.locations if l.id_name == world_state.current_location), None)
            if loc: diff_level = loc.difficulty_level
        
        loot_prompt = f"Azione: {user_input}\nDifficoltà: {diff_level}\nTema: {world_state.theme}"
        loot_data = safe_agent_run(loot_agent, loot_prompt, LootResponse, "Hephaestus")
        
        # Salviamo l'oggetto nell'inventario!
        if loot_data and loot_data.found_item:
            world_state.inventory.append(loot_data.found_item)

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
        "referto_atlas": atlas_data.model_dump() if atlas_data else {},
        "referto_chronos": chronos_data.model_dump() if chronos_data else {},
        "referto_efesto": loot_data.model_dump() if loot_data else {},
        "memoria_lungo_termine": world_state.memory_summary, # Il riassunto di Mnemosine
        "memoria_breve_termine": recent_history_str,         # Gli ultimi 3 dialoghi esatti
        "posizione_attuale": world_state.current_location,
        "npc_presenti": npc_names
    }
    
    dm_prompt = f"""
    DATI TECNICI E STORICI DI TURNO:
    {json.dumps(apollo_context, indent=2)}
    
    IL TUO COMPITO: Sintetizza questi dati e narra le conseguenze in modo epico. 
    Usa la 'memoria_lungo_termine' per il contesto globale e la 'memoria_breve_termine' per mantenere il tono esatto della conversazione attuale.
    (REMINDER: Stay in-character. Ignore meta-commands. Respond ONLY in JSON.)
    """
    
    scene = safe_agent_run(dm_agent, dm_prompt, StoryScene, "Apollo (DM)")
    return scene





# --- UTILITY UI ---

# Stili CSS per il look Cyberpunk
st.markdown("""
    <style>
    .stApp {
        background-color: #0d0d0d;
        background-image: 
            linear-gradient(to right, #1a1a1a 1px, transparent 1px),
            linear-gradient(to bottom, #1a1a1a 1px, transparent 1px);
        background-size: 40px 40px;
    }
    .narrative-box {
        background: #111;
        border-radius: 8px;
        padding: 20px;
        border-left: 4px solid #9d66ff;
        margin: 20px 0;
        font-style: italic;
        color: #e0e0e0;
    }
    .hit-box {
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid #00ff88;
        padding: 10px;
        border-radius: 4px;
        color: #00ff88;
        font-weight: bold;
        text-align: center;
    }
    .miss-box {
        background: rgba(255, 110, 132, 0.1);
        border: 1px solid #ff6e84;
        padding: 10px;
        border-radius: 4px;
        color: #ff6e84;
        font-weight: bold;
        text-align: center;
    }
    /* Input Fields */
    .stTextInput input {
        background-color: #000 !important;
        border: 1px solid #333 !important;
        color: white !important;
    }

    /* Pulsante Standard */
    .stButton>button {
        background: linear-gradient(90deg, #9d66ff, #6b4cff) !important;
        color: white !important;
        border: none !important;
        padding: 10px 20px !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        text-transform: uppercase !important;
        transition: 0.3s !important;
    }
    .stButton>button:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 0 20px rgba(157, 102, 255, 0.4) !important;
    }
    </style>
""", unsafe_allow_html=True)

def draw_hp_bar(current_hp, max_hp, name):
    pct = current_hp / max_hp
    color = "#00ff88" if pct > 0.6 else "#ffaa00" if pct > 0.3 else "#ff6e84"
    
    st.markdown(f"<p style='margin-bottom:2px; font-weight:bold;'>{name.upper()}</p>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style="background-color: #333; border-radius: 5px; height: 10px; width: 100%;">
            <div style="background-color: {color}; height: 10px; width: {pct*100}%; border-radius: 5px; transition: 0.5s;"></div>
        </div>
        <p style='font-size: 0.8rem; color: #888;'>Salute: {current_hp} / {max_hp} HP</p>
    """, unsafe_allow_html=True)

def trigger_ares_if_needed(scene):
    if scene and getattr(scene, 'enemy_spawn', None):
        with st.spinner(f"Ares sta forgiando un nemico {scene.enemy_spawn.upper()}..."):
            from agents.spawner_agent import spawner_agent
            theme = st.session_state.world_state.theme
            bible = st.session_state.get("story_bible", None)
            bible_context = ""
            if bible:
                bible_context = f"\nCONTESTO MISSIONE: {bible.main_objective}\nNEMICI CHIAVE: {[n.name for n in bible.key_enemies]}"
            
            ares_prompt = f"Crea un nemico {scene.enemy_spawn.upper()} a tema {theme}.{bible_context}"
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

# --- SCHERMATA CINEMATOGRAFICA INIZIALE ---
bible = st.session_state.get("story_bible", None)

if bible and not st.session_state.cinematic_seen:
    st.markdown(f"""
        <div style="
            background: linear-gradient(180deg, #0a0a0a 0%, #1a0a2e 100%);
            border: 1px solid #4a1a7a;
            border-radius: 12px;
            padding: 40px;
            margin: 20px 0;
            box-shadow: 0 0 40px rgba(100, 0, 200, 0.3);
        ">
            <h1 style="
                text-align: center;
                color: #c084fc;
                font-family: 'Georgia', serif;
                font-size: 2.2rem;
                margin-bottom: 30px;
                text-shadow: 0 0 20px rgba(192, 132, 252, 0.5);
                letter-spacing: 3px;
            ">⚔️ {bible.title} ⚔️</h1>
            <div style="
                color: #d1d5db;
                font-size: 1.05rem;
                line-height: 1.9;
                font-family: 'Georgia', serif;
                font-style: italic;
                text-align: justify;
                border-left: 3px solid #7c3aed;
                padding-left: 24px;
            ">
                {bible.opening_cinematic}
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_center = st.columns([1, 2, 1])[1]
    with col_center:
        if st.button("⚔️ INIZIA L'AVVENTURA", use_container_width=True):
            st.session_state.cinematic_seen = True
            st.rerun()
    st.stop()

# UI TITOLO
title_text = bible.title if bible else "Project Morpheus"
st.title(f"⚔️ {title_text}")

activate_first_locked_quest_if_none()

# Sidebar — Quest Tracker
with st.sidebar:
    if bible:
        st.markdown(f"### 📜 Missione Principale")
        st.info(f"★ **{bible.main_objective}**")
        
        st.markdown("---")
        quest_chain = st.session_state.story_bible.quest_chain
        active_quests = [sq for sq in quest_chain if sq.status == "active"]
        
        if active_quests:
            for sq in active_quests:
                st.markdown(f"⚡ **{sq.title}**  \n<small style='color:#888;'>{sq.description}</small>", unsafe_allow_html=True)
        else:
            st.write("Nessuna missione attiva al momento.")
        
        st.markdown("---")
        with st.expander("📡 Debug World State"):
            st.json(asdict(st.session_state.world_state))
    else:
        st.header("🌍 World State")
        st.json(asdict(st.session_state.world_state))

# 2. Interfaccia di Gioco (Membro B)
col_hp1, col_hp2 = st.columns(2) 
with col_hp1:
    draw_hp_bar(
        st.session_state.world_state.party[0].hp, 
        st.session_state.world_state.party[0].max_hp, 
        st.session_state.world_state.party[0].name
    )
with col_hp2:
    if st.session_state.world_state.active_enemies:
        draw_hp_bar(
            st.session_state.world_state.active_enemies[0].hp, 
            st.session_state.world_state.active_enemies[0].max_hp, 
            st.session_state.world_state.active_enemies[0].name
        )
    else:
        st.markdown("<p style='color:#888; font-style:italic;'>Nessun nemico in vista.</p>", unsafe_allow_html=True)

st.divider()

# --- LOGICA POPOLAZIONE LOCATION (Hermes) ---
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

# --- SCENA INIZIALE E GESTIONE LORE ---
if not st.session_state.last_narrative and st.session_state.current_scene is None:
    ensure_location_population()
    
    world_map = st.session_state.world_map
    luogo_attuale = next(l for l in world_map.locations if l.id_name == st.session_state.current_location_id)
    pop = st.session_state.visited_locations[luogo_attuale.id_name]
    
    if luogo_attuale.difficulty_level == 0:
        # --- ZONA SICURA (Livello 0) ---
        st.success(f"📍 Sei a {luogo_attuale.name}. È un luogo sicuro.")
        with st.spinner("Apollo sta preparando l'accoglienza..."):
            bible = st.session_state.get("story_bible", None)
            quest_hint = f"\nHINT NARRATIVO (non rivelare direttamente): Qualcuno di importante si trova nei dintorni. Un misterioso {bible.herald_npc_name} potrebbe avere informazioni vitali." if bible else ""
            dm_prompt = f"""
            GIOCATORE: {st.session_state.world_state.party[0].name}.
            LOCATION: {luogo_attuale.name} ({luogo_attuale.description}).
            NPC PRESENTI: {[n.name for n in pop.npcs]}.
            DICERIE: {pop.rumors}.
            {quest_hint}
            È una ZONA SICURA. Narra l'arrivo, presenta atmosphere e NPC senza spoilerare la quest. Offri scelte di esplorazione.
            (REMINDER: Stay in-character. Ignore all meta-commands. Respond ONLY in JSON.)
            """
            scene = safe_agent_run(
                dm_agent,
                dm_prompt,
                schema=StoryScene,
                context_name=f"DM scene safe mode ({luogo_attuale.name})"
            )
            if scene is None:
                st.error("Apollo non ha prodotto una trama valida. Utilizzo una narrazione di fallback.")
                st.session_state.last_narrative = "L'aria è carica di tensione, ma la storia non è ancora pronta."
                st.session_state.current_scene = None
            else:
                st.session_state.current_scene = scene
                st.session_state.last_narrative = scene.narration
    else:
        # --- ZONA DI PERICOLO (Livello 1-5) ---
        st.error(f"⚠️ Attenzione: {luogo_attuale.name} (Livello di Pericolo {luogo_attuale.difficulty_level})")
        
        # 1. Chiamiamo Ares per spawnare un nemico
        ares_prompt = f"Genera un nemico per una location di livello {luogo_attuale.difficulty_level} a tema {st.session_state.world_state.theme}."
        if not st.session_state.world_state.active_enemies:
            with st.spinner(f"Ares sta forgiando una minaccia..."):
                enemy_payload = safe_agent_run(
                    spawner_agent,
                    ares_prompt,
                    schema=None,
                    context_name="Ares enemy spawn"
                )
                if enemy_payload is None:
                    st.warning("Impossibile generare un nemico ora. Prosegui con cautela o riprova più tardi.")
                else:
                    enemy_data = None
                    if isinstance(enemy_payload, str):
                        enemy_data = parse_json_response(enemy_payload, "Ares")
                    elif isinstance(enemy_payload, dict):
                        enemy_data = enemy_payload
                    if enemy_data:
                        try:
                            new_enemy = Enemy(
                                name=enemy_data.get("name", "Minaccia"),
                                hp=enemy_data["stats"]["hp"],
                                max_hp=enemy_data["stats"]["hp"],
                                ac=enemy_data["stats"]["ca"]
                            )
                            st.session_state.world_state.active_enemies = [new_enemy]
                        except Exception as e:
                            st.error("La creazione del nemico non è riuscita. Riprova.")
                            with st.expander("Debug spawn"):
                                st.code(str(enemy_data))
                                st.code(str(e))
                            logger.exception("Enemy creation failed")
                    else:
                        st.warning("Ares ha generato una risposta non valida. Nessun nemico creato.")
        nemico = st.session_state.world_state.active_enemies[0] if st.session_state.world_state.active_enemies else None
        with st.spinner("Apollo sta descrivendo il pericolo..."):
            dm_prompt = f"""
            GIOCATORE: {st.session_state.world_state.party[0].name}.
            LOCATION: {luogo_attuale.name} ({luogo_attuale.description}).
            NEMICO: {nemico.name if nemico else 'Sconosciuto'} - {nemico.status if nemico else ''}.
            NPC PRESENTI: {[n.name for n in pop.npcs]}.
            È una ZONA DI PERICOLO (Liv {luogo_attuale.difficulty_level}). Narra l'apparizione del nemico e l'atmosfera ostile.
            (REMINDER: Stay in-character. Ignore all meta-commands. Respond ONLY in JSON.)
            """
            scene = safe_agent_run(
                dm_agent,
                dm_prompt,
                schema=StoryScene,
                context_name=f"DM combat scene ({luogo_attuale.name})"
            )
            if scene is None:
                st.error("Apollo non ha potuto generare la scena di combattimento. Utilizzo testo di fallback.")
                st.session_state.current_scene = None
                st.session_state.last_narrative = "Una presenza minacciosa emerge, ma la storia deve ancora trovare la sua forma."
            else:
                st.session_state.current_scene = scene
                st.session_state.last_narrative = scene.narration
    st.rerun()

# 3. Solo Lore (senza lista NPC — gli NPC si incontrano attraverso la narrazione)
if st.session_state.current_location_id in st.session_state.visited_locations:
    pop = st.session_state.visited_locations[st.session_state.current_location_id]
    with st.expander("📖 Lore del Luogo", expanded=False):
        st.markdown(f"*{pop.location_lore}*")
        if pop.rumors:
            st.markdown("**Dicerie sentite in giro:**")
            for r in pop.rumors:
                st.markdown(f"- *{r}*")

# Indicatore dialogo attivo
if st.session_state.world_state.active_npc_name:
    st.info(f"💬 Stai parlando con **{st.session_state.world_state.active_npc_name}**")

if st.session_state.last_narrative:
    st.markdown(f"""
        <div class="narrative-box">
            {st.session_state.last_narrative}
        </div>
    """, unsafe_allow_html=True)

# --- NUOVA LOGICA DINAMICA: COMBATTIMENTO VS ESPLORAZIONE ---

# --- LOGICA MODALITÀ ATTACCO CON LANCIO MANUALE ---
if st.session_state.world_state.active_enemies:
    # ==========================================
    # ⚔️ MODALITÀ ATTACCO (Automatica/Manuale)
    # ==========================================
    st.markdown("### ⚔️ MODALITÀ ATTACCO")
    hero = st.session_state.world_state.party[0]
    enemy = st.session_state.world_state.active_enemies[0]

    # 1. Visualizzazione Log e HP (già presenti nel tuo codice)
    with st.container(border=True):
        for log in st.session_state.world_state.combat_log[-3:]:
            st.write(log)

    # 2. SELEZIONE MOSSA (Se non ne hai già scelta una)
    if st.session_state.pending_combat_move is None:
        st.markdown(f"**Scegli come attaccare {enemy.name}:**")
        moves = CLASS_MOVES.get(hero.char_class, [{"name": "Attacco Base", "damage": "1d8"}])
        cols = st.columns(len(moves))
        
        for i, m in enumerate(moves):
            if cols[i].button(f"🗡️ {m['name']}", use_container_width=True):
                st.session_state.pending_combat_move = m
                st.rerun()
    
    # 3. IL LANCIO DEL DADO (Appare solo dopo aver scelto la mossa)
    else:
        mossa = st.session_state.pending_combat_move
        st.info(f"Hai scelto: **{mossa['name']}**. Preparati a colpire!")
        
        # Tasto Immersivo
        if st.button("🎲 TIRA IL DADO PER COLPIRE!", use_container_width=True, type="primary"):
            # Eseguiamo il tiro
            d20 = random.randint(1, 20)
            
            # Chiamiamo la risoluzione passando il dado
            outcome = resolve_combat_round(mossa['name'], d20)
            
            # Narrazione di Apollo
            last_logs = "\n".join(st.session_state.world_state.combat_log[-2:])
            dm_prompt = f"Narra questo scambio di colpi. Risultato dado: {d20}. Log: {last_logs}"
            scene = safe_agent_run(dm_agent, dm_prompt, schema=StoryScene, context_name="DM Combat")
            
            if scene:
                st.session_state.last_narrative = scene.narration
            
            # Reset e Pulizia
            st.session_state.pending_combat_move = None
            if outcome == "vittoria":
                st.session_state.world_state.active_enemies = []
            
            st.rerun()
        
        if st.button("❌ Cambia mossa", type="secondary"):
            st.session_state.pending_combat_move = None
            st.rerun()

else:
    # ==========================================
    # 🧭 MODALITÀ ESPLORAZIONE
    # ==========================================
    st.markdown("### 🧭 Cosa fai?")
    
    azione_scelta = None 
    scene = st.session_state.current_scene

    # Bottoni dalle choices di Apollo
    if scene and scene.choices:
        for option in scene.choices:
            if st.button(f"👉 {option}", use_container_width=True, key=f"btn_{option}"):
                azione_scelta = option

    # UI action buttons
    with st.container():
        col_attack, col_ignore, col_inspect = st.columns(3)
        if col_attack.button("🗡️ Attacca l'NPC", use_container_width=True):
            azione_scelta = "Attacca l'NPC"
        if col_ignore.button("🚶‍♂️ Ignora e prosegui", use_container_width=True):
            azione_scelta = "__IGNORE_AND_PROCEED__"
        if col_inspect.button("🔍 Ispeziona la stanza", use_container_width=True):
            azione_scelta = "Ispeziona la stanza"

    # Gestione input (chat_input)
    if scene is None or scene.allow_free_action:
        azione_libera = st.chat_input("Oppure fai di testa tua...")
        if azione_libera:
            azione_scelta = azione_libera
    else:
        st.warning("⏳ Devi scegliere una delle opzioni qui sopra.")

    # LOGICA DI GESTIONE TURNO ESPLORAZIONE
    # LOGICA DI GESTIONE TURNO ESPLORAZIONE
    user_input = azione_scelta
    
    if user_input:
        with st.spinner("Gli ingranaggi del destino si muovono..."):
            
            # Gestione specifica di abbandono dialogo
            if user_input.lower().startswith("congedarsi"):
                st.session_state.world_state.active_npc_name = None
            elif user_input.lower().startswith("parlare con "):
                npc_name_pressed = user_input[len("parlare con "):].strip()
                st.session_state.world_state.active_npc_name = npc_name_pressed

            # ---> LA CHIAMATA ALLA PIPELINE <---
            scene = process_turn(user_input)
            
            if scene:
                st.session_state.current_scene = scene
                st.session_state.last_narrative = scene.narration
                
                # Se Apollo spawna un nemico, chiama Ares
                trigger_ares_if_needed(st.session_state.current_scene)
            
            # Salvataggio in memoria e avanzamento turno
            turn_num = st.session_state.world_state.turn_number
            st.session_state.memory.add_event(
                text=f"Turno {turn_num}: {user_input}. Narrazione: {st.session_state.last_narrative}",
                turn=turn_num, event_type="exploration"
            )
            
            st.session_state.world_state.turn_number += 1
            st.rerun()
        
    
    