import streamlit as st
import json
from dotenv import load_dotenv
import os

# Import dei vostri moduli
from agents.rules_agent import rules_agent
from agents.dm_agent import dm_agent
from agents.map_agent import map_agent
from agents.npc_agent import npc_agent
from agents.spawner_agent import spawner_agent
from agents.lore_agent import lore_agent
from knowledge.chroma_store import DungeonMemory
from contracts.schemas import WorldState, Character, Enemy, StoryScene, WorldMap, LocationPopulation, StoryBible
from setup_page import render_setup_page

# Caricamento variabili d'ambiente
load_dotenv()

# Inizializzazione della pagina di defaut
if "page" not in st.session_state:
    st.session_state.page = "setup"

if st.session_state.page == "setup":
    render_setup_page()
    st.stop() # Ferma l'esecuzione qui, non disegna il resto del gioco

# 1. Inizializzazione Session State (Membro B)
if "world_state" not in st.session_state:
    # Recuperiamo i dati dalla Setup Page
    p1_name = st.session_state.get("setup_p1_name", "Valerius")
    p1_class = st.session_state.get("setup_p1_class", "Warrior")
    theme = st.session_state.get("setup_theme", "Medievale")
    
    # --- Generazione Story Bible (La Musa) PRIMA di tutto ---
    if "story_bible" not in st.session_state:
        with st.spinner("📖 La Musa sta scrivendo la storia del mondo..."):
            lore_prompt = f"Tema: {theme}. Crea la Story Bible per questa avventura."
            lore_res = lore_agent.run(lore_prompt)
            raw_lore = lore_res.content
            if isinstance(raw_lore, str):
                clean_lore = raw_lore.strip().removeprefix("```json").removesuffix("```").strip()
                st.session_state.story_bible = StoryBible.model_validate_json(clean_lore)
            else:
                st.session_state.story_bible = raw_lore

    # --- Generazione Mappa (Atlas) ---
    if "world_map" not in st.session_state:
        with st.spinner("Atlas sta disegnando i confini del mondo..."):
            bible = st.session_state.story_bible
            map_prompt = f"Tema: {theme}. Titolo avventura: {bible.title}. Araldo in posizione: {bible.herald_location_id}. Genera una mappa coerente."
            map_res = map_agent.run(map_prompt)
            
            raw_content = map_res.content
            if isinstance(raw_content, str):
                clean_content = raw_content.strip().removeprefix("```json").removesuffix("```").strip()
                st.session_state.world_map = WorldMap.model_validate_json(clean_content)
            else:
                st.session_state.world_map = raw_content

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

if "memory" not in st.session_state:
    st.session_state.memory = DungeonMemory(session_id="test_session_001")

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None

if "current_user_input" not in st.session_state:
    st.session_state.current_user_input = ""

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
            ares_prompt = f"Crea un nemico {scene.enemy_spawn.upper()} a tema {theme}"
            ares_raw = spawner_agent.run(ares_prompt)
            try:
                clean_ares = ares_raw.content.replace('```json', '').replace('```', '').strip()
                import json as _j
                enemy_data = _j.loads(clean_ares)
                from contracts.schemas import Enemy
                new_enemy = Enemy(
                    name=enemy_data.get("name", "Entità Sconosciuta"),
                    hp=enemy_data["stats"]["hp"],
                    max_hp=enemy_data["stats"]["hp"],
                    ac=enemy_data["stats"]["ca"]
                )
                st.session_state.world_state.active_enemies = [new_enemy]
                scene.enemy_spawn = None # avoid respawning on rerun
            except Exception as e:
                st.error(f"Errore nello spawn del nemico: {e}")

# UI TITOLO
bible = st.session_state.get("story_bible", None)
title_text = bible.title if bible else "Project Morpheus"
st.title(f"⚔️ {title_text}")

# Sidebar — Quest Tracker
with st.sidebar:
    if bible:
        st.markdown(f"### 📜 Missione Principale")
        st.info(f"★ **{bible.main_objective}**")
        
        st.markdown("---")
        st.markdown("### 🗺️ Sub-Missioni")
        quest_chain = st.session_state.story_bible.quest_chain
        for sq in quest_chain:
            if sq.status == "completed":
                badge = "✅"
                label_style = "~~"
            elif sq.status == "active":
                badge = "⚡"
                label_style = "**"
            else:
                badge = "🔒"
                label_style = ""
            st.markdown(f"{badge} {label_style}{sq.title}{label_style}  \n<small style='color:#888;'>{sq.description if sq.status != 'locked' else '???'}</small>", unsafe_allow_html=True)
        
        st.markdown("---")
        with st.expander("📡 Debug World State"):
            st.json(st.session_state.world_state.model_dump())
    else:
        st.header("🌍 World State")
        st.json(st.session_state.world_state.model_dump())

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
                bible_context = f"""
CONTESTO NARRATIVO:
- Obiettivo finale: {bible.main_objective}
- NPC chiave: {[n.name + ' (' + n.role + ')' for n in bible.key_npcs]}
- Missioni attive: {[sq.title for sq in active_subquests]}
- Araldo della quest: {bible.herald_npc_name} (si trova a: {bible.herald_location_id})
"""
            hermes_prompt = f"""
            Tema: {st.session_state.world_state.theme}. 
            Luogo: {luogo.name} ({luogo.description}). 
            Livello Pericolo: {luogo.difficulty_level}.
            Luoghi vicini: {', '.join(luoghi_vicini)}.
            {bible_context}
            """
            popolazione_res = npc_agent.run(hermes_prompt)
            st.session_state.visited_locations[loc_id] = popolazione_res.content

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
            """
            dm_raw = dm_agent.run(dm_prompt)
            try:
                clean = dm_raw.content.replace('```json', '').replace('```', '').strip()
                import json as _j
                dm_data = _j.loads(clean)
                st.session_state.current_scene = StoryScene(**dm_data)
                st.session_state.last_narrative = st.session_state.current_scene.narration
            except Exception:
                st.session_state.last_narrative = dm_raw.content
    else:
        # --- ZONA DI PERICOLO (Livello 1-5) ---
        st.error(f"⚠️ Attenzione: {luogo_attuale.name} (Livello di Pericolo {luogo_attuale.difficulty_level})")
        
        # 1. Chiamiamo Ares per spawnare un nemico
        if not st.session_state.world_state.active_enemies:
            with st.spinner(f"Ares sta forgiando una minaccia..."):
                ares_prompt = f"Genera un nemico per una location di livello {luogo_attuale.difficulty_level} a tema {st.session_state.world_state.theme}."
                ares_res = spawner_agent.run(ares_prompt)
                try:
                    clean_ares = ares_res.content.replace('```json', '').replace('```', '').strip()
                    import json as _j_ares
                    enemy_data = _j_ares.loads(clean_ares)
                    new_enemy = Enemy(
                        name=enemy_data.get("name", "Minaccia"),
                        hp=enemy_data["stats"]["hp"],
                        max_hp=enemy_data["stats"]["hp"],
                        ac=enemy_data["stats"]["ca"]
                    )
                    st.session_state.world_state.active_enemies = [new_enemy]
                except Exception as e:
                    st.error(f"Errore spawn: {e}")

        # 2. Chiamiamo Apollo per narrare l'incontro
        nemico = st.session_state.world_state.active_enemies[0] if st.session_state.world_state.active_enemies else None
        with st.spinner("Apollo sta descrivendo il pericolo..."):
            dm_prompt = f"""
            GIOCATORE: {st.session_state.world_state.party[0].name}.
            LOCATION: {luogo_attuale.name} ({luogo_attuale.description}).
            NEMICO: {nemico.name if nemico else 'Sconosciuto'} - {nemico.status if nemico else ''}.
            NPC PRESENTI: {[n.name for n in pop.npcs]}.
            È una ZONA DI PERICOLO (Liv {luogo_attuale.difficulty_level}). Narra l'apparizione del nemico e l'atmosfera ostile.
            """
            dm_raw = dm_agent.run(dm_prompt)
            try:
                clean = dm_raw.content.replace('```json', '').replace('```', '').strip()
                import json as _j2
                dm_data = _j2.loads(clean)
                st.session_state.current_scene = StoryScene(**dm_data)
                st.session_state.last_narrative = st.session_state.current_scene.narration
            except Exception:
                st.session_state.last_narrative = dm_raw.content
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

st.markdown("### 🧭 Cosa fai?")

azione_scelta = None
scene = st.session_state.current_scene

# Bottoni dalle choices di Apollo (sempre visibili quando c'è una scena)
if scene and scene.choices:
    for option in scene.choices:
        if st.button(f"👉 {option}", use_container_width=True):
            azione_scelta = option

# Scelta libera: visibile solo se Apollo lo permette
if scene is None or scene.allow_free_action:
    azione_libera = st.chat_input("Oppure fai di testa tua...")
    if azione_libera:
        azione_scelta = azione_libera
else:
    st.warning("⏳ Non c'è tempo per pensare! Devi scegliere una delle opzioni qui sopra.")

# Prima partita: nessuna scena caricata, mostriamo solo la chat
if scene is None and not st.session_state.last_narrative:
    azione_libera = st.chat_input("Cosa vuoi fare? (es. Attacco lo scheletro con la spada)")
    if azione_libera:
        azione_scelta = azione_libera

# --- LOGICA DI GESTIONE TURNO ---

user_input = azione_scelta
if user_input:
    scene = st.session_state.current_scene
    is_combat_action = scene.is_combat if scene else True  # Default: tratta come combattimento

    if not is_combat_action:
        # --- PERCORSO ESPLORAZIONE / DIALOGO: direttamente ad Apollo ---
        with st.spinner("Apollo sta narrando..."):
            import json as _json_exp
            
            # Recuperiamo il contesto NPC del luogo corrente
            loc_pop = st.session_state.visited_locations.get(st.session_state.current_location_id, None)
            npc_context = ""
            active_npc = st.session_state.world_state.active_npc_name
            
            # Gestiamo il caso "Congedarsi da [NPC]"
            if user_input.lower().startswith("congedarsi"):
                st.session_state.world_state.active_npc_name = None
                active_npc = None
            
            # Aggiornamento dialogo attivo se il giocatore sceglie "Parlare con [Nome NPC]"
            elif user_input.lower().startswith("parlare con ") and loc_pop:
                npc_name_pressed = user_input[len("parlare con "):].strip()
                match = next((n for n in loc_pop.npcs if n.name.lower() == npc_name_pressed.lower()), None)
                if match:
                    st.session_state.world_state.active_npc_name = match.name
                    active_npc = match.name
            
            # Costruiamo il contesto NPC
            if active_npc and loc_pop:
                npc_data = next((n for n in loc_pop.npcs if n.name == active_npc), None)
                if npc_data:
                    npc_context = f"""
DIALOGO ATTIVO CON: {npc_data.name}
RUOLO: {npc_data.role}
ASPETTO: {npc_data.appearance}
PERSONALITÀ: {npc_data.personality}
PRIMA BATTUTA (se prima interazione): {npc_data.first_line}
"""
            elif loc_pop and loc_pop.npcs:
                npc_names = [n.name for n in loc_pop.npcs]
                npc_context = f"NPC PRESENTI NEL LUOGO (non ancora in dialogo): {npc_names}\n"
            
            exp_context = f"""
AZIONE/RISPOSTA DEL GIOCATORE: {user_input}
GIOCATORE: {st.session_state.world_state.party[0].name}
LOCATION ATTUALE: {st.session_state.world_state.current_location}
LOCATION CONOSCIUTE (il giocatore può raggiungere solo queste): {get_known_locations_names()}
SCENA PRECEDENTE: {st.session_state.last_narrative}
{npc_context}
"""
            dm_raw = dm_agent.run(exp_context)
            try:
                clean = dm_raw.content.replace('```json', '').replace('```', '').strip()
                dm_data = _json_exp.loads(clean)
                st.session_state.current_scene = StoryScene(**dm_data)
                st.session_state.last_narrative = st.session_state.current_scene.narration
                trigger_ares_if_needed(st.session_state.current_scene)
            except Exception:
                st.session_state.last_narrative = dm_raw.content
                st.session_state.current_scene = None
            # Salva in memoria
            turn_num = st.session_state.world_state.turn_number
            st.session_state.memory.add_event(
                text=f"Turno {turn_num}: {user_input}. Narrazione: {st.session_state.last_narrative}",
                turn=turn_num, event_type="exploration"
            )
            st.session_state.world_state.turn_number += 1
            st.rerun()
    else:
        # --- PERCORSO COMBATTIMENTO: passa ad Athena ---
        with st.spinner("Athena sta decidendo il destino..."):
            response = rules_agent.run(user_input)
        
        # --- PARSING ROBUSTO ---
        content = response.content
        if isinstance(content, str):
            import json
            try:
                clean_str = content.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_str)
                
                if "error" in data:
                    error_msg = data["error"].get("message", "Errore sconosciuto")
                    if data["error"].get("code") == 429:
                        st.error("⏳ **Limite superato!** Aspetta circa 60 secondi.")
                    else:
                        st.error(f"❌ Errore API: {error_msg}")
                    st.stop()
                
                # --- PULIZIA DATI RESILIENTE ---
                if "damage" in data and isinstance(data["damage"], dict):
                    data["damage"] = data["damage"].get("result") or data["damage"].get("total") or 0
                
                from contracts.schemas import RulesResult
                result = RulesResult(**data)
                
                # --- CASO NON-ATTACCO: hit è null, non serve tiro dado ---
                # Athena dice che non è un attacco: Apollo narra l'esito direttamente
                if result.hit is None and not result.needs_clarification:
                    import json as _json_na
                    na_context = f"""
                    AZIONE GIOCATORE: {user_input}
                    GIOCATORE: {st.session_state.world_state.party[0].name}
                    SCENA PRECEDENTE: {st.session_state.last_narrative}
                    NOTA ARBITRO: {result.narrative_hint}
                    Non c'è stato un attacco. Narra l'esito dell'azione e proponi nuove scelte.
                    """
                    with st.spinner("Apollo sta narrando..."):
                        dm_raw = dm_agent.run(na_context)
                        try:
                            clean_na = dm_raw.content.replace('```json', '').replace('```', '').strip()
                            dm_data = _json_na.loads(clean_na)
                            st.session_state.current_scene = StoryScene(**dm_data)
                            st.session_state.last_narrative = st.session_state.current_scene.narration
                            trigger_ares_if_needed(st.session_state.current_scene)
                        except Exception:
                            st.session_state.last_narrative = result.narrative_hint
                            st.session_state.current_scene = None
                    st.session_state.world_state.turn_number += 1
                    st.rerun()
                    
            except Exception as e:
                st.error("⚠️ Risposta non standard. Riprova tra poco.")
                with st.expander("Debug"):
                    st.code(content)
                    st.code(str(e))
                st.stop()
        else:
            result = content
        # --- FINE PARSING ---
        
        st.session_state.pending_action = result
        st.session_state.current_user_input = user_input

# Fase 2: Il Lancio del Dado (Manuale del giocatore)
if st.session_state.pending_action:
    res = st.session_state.pending_action
    
    if res.needs_clarification:
        st.warning(f"🤔 {res.narrative_hint}")
        st.session_state.pending_action = None
    elif res.hit is None:
        # Azione non è un attacco ma è pending: mostra il suggerimento narrativo
        st.info(f"💬 {res.narrative_hint}")
        st.session_state.pending_action = None
    else:
        st.divider()
        st.write(f"### ⚔️ Azione: {st.session_state.current_user_input}")
        
        # Determiniamo il nemico e la sua CA (Classe Armatura)
        enemy = st.session_state.world_state.active_enemies[0]
        st.info(f"Per riuscire devi superare la CA di **{enemy.name}** ({enemy.ac})")
        
        if st.button("🎲 TIRA IL DADO!"):
            # Qui il tiro è manuale ma gestito dal codice Python
            import random
            d20_roll = random.randint(1, 20)
            
            # Usiamo il modificatore di Athena se presente, altrimenti +3 (default character FOR)
            modifier = res.roll.modifier if (res.roll and res.roll.modifier is not None) else 3
            total = d20_roll + modifier
            
            # Calcolo esito usando la CA del nemico reale
            hit = total >= enemy.ac
            damage = (random.randint(1, 8) + modifier) if hit else 0
            
            # Mostriamo il risultato
            col1, col2 = st.columns(2)
            col1.metric("Risultato Dado", f"{d20_roll} + {modifier}", delta=total)
            
            if hit:
                col2.error(f"COLPITO! 💥 {damage} danni")
                # Aggiornamento HP del nemico
                enemy.hp -= damage
                if enemy.hp <= 0:
                    enemy.hp = 0
                    enemy.status = "dead"
            else:
                col2.info("🛡️ MANCATO!")
                
            # 7. CHIAMATA AL DM AGENT (Apollo)
            dm_context = f"""
            GIOCATORE: {st.session_state.world_state.party[0].name} ({st.session_state.world_state.party[0].char_class})
            AZIONE TENTATA: {st.session_state.current_user_input}
            ESITO TECNICO: {'Colpito' if hit else 'Mancato'} con un totale di {total}.
            DANNI INFLITTI: {damage}
            STATO NEMICO: {enemy.name} ha {enemy.hp}/{enemy.max_hp} HP rimanenti.
            SCENA: {res.narrative_hint}
            """
            
            with st.spinner("Apollo sta narrando l'esito..."):
                dm_raw = dm_agent.run(dm_context)
                dm_content = dm_raw.content
                
                # --- PARSING StoryScene ---
                import json as _json
                try:
                    clean_dm = dm_content.replace('```json', '').replace('```', '').strip()
                    dm_data = _json.loads(clean_dm)
                    st.session_state.current_scene = StoryScene(**dm_data)
                    st.session_state.last_narrative = st.session_state.current_scene.narration
                    trigger_ares_if_needed(st.session_state.current_scene)
                except Exception:
                    # Fallback: salviamo il testo grezzo come narrazione
                    st.session_state.current_scene = None
                    st.session_state.last_narrative = dm_content
            
            # Salvataggio in Memoria
            turn_num = st.session_state.world_state.turn_number
            event_text = f"Turno {turn_num}: {st.session_state.current_user_input}. "
            event_text += f"Esito: {'Colpito' if hit else 'Mancato'}. "
            event_text += f"Narrazione: {st.session_state.last_narrative}"
            
            st.session_state.memory.add_event(
                text=event_text, 
                turn=turn_num, 
                event_type="combat"
            )
            
            # Avanzamento Turno
            st.session_state.world_state.turn_number += 1
            
            # Puliamo l'azione pendente per il prossimo turno
            st.session_state.pending_action = None
            st.session_state.current_user_input = ""
            st.rerun()
