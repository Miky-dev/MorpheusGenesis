import streamlit as st
from dotenv import load_dotenv
import os

# Import dei vostri moduli
from agents.rules_agent import rules_agent
from agents.dm_agent import dm_agent
from knowledge.chroma_store import DungeonMemory
from contracts.schemas import WorldState, Character, Enemy, StoryScene
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
    
    # Creiamo uno stato iniziale basato sull'input
    hero = Character(name=p1_name, char_class=p1_class, hp=24, max_hp=24)
    skeleton = Enemy(name="Scheletro", hp=20, max_hp=20, ac=13)
    
    st.session_state.world_state = WorldState(
        party=[hero],
        active_enemies=[skeleton]
    )

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
st.title("⚔️ Project Morpheus — Test Sprint 1")
st.subheader("Integrazione Rules Agent + World State + ChromaDB")

# Sidebar con lo Stato del Mondo (Visualizzazione per debug)
with st.sidebar:
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

# --- SCENA INIZIALE: Apollo genera l'ambientazione al primo avvio ---
if not st.session_state.last_narrative and st.session_state.current_scene is None:
    world = st.session_state.world_state
    player = world.party[0]
    enemy = world.active_enemies[0] if world.active_enemies else None
    
    opening_context = f"""
    INIZIO SESSIONE.
    TEMA: {world.theme}
    GIOCATORE: {player.name}, {player.char_class} ({player.hp}/{player.max_hp} HP).
    SCENA: {world.current_location}.
    {"NEMICO PRESENTE: " + enemy.name + " (" + str(enemy.hp) + " HP, CA " + str(enemy.ac) + ")." if enemy else "Nessun nemico in vista."}
    
    Descrivi l'ambientazione iniziale e dai al giocatore 2-3 scelte per cominciare.
    """
    
    with st.spinner("Apollo sta preparando la scena..."):
        import json as _json
        dm_raw = dm_agent.run(opening_context)
        try:
            clean = dm_raw.content.replace('```json', '').replace('```', '').strip()
            dm_data = _json.loads(clean)
            st.session_state.current_scene = StoryScene(**dm_data)
            st.session_state.last_narrative = st.session_state.current_scene.narration
            trigger_ares_if_needed(st.session_state.current_scene)
        except Exception:
            st.session_state.last_narrative = dm_raw.content
        st.rerun()

# 3. Narrativa precedente + UI Dinamica derivata dalla scena
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
        # --- PERCORSO ESPLORAZIONE: direttamente ad Apollo, skip Athena ---
        with st.spinner("Apollo sta narrando..."):
            import json as _json_exp
            exp_context = f"""
            AZIONE GIOCATORE: {user_input}
            GIOCATORE: {st.session_state.world_state.party[0].name}
            SCENA PRECEDENTE: {st.session_state.last_narrative}
            Non c'è combattimento. Narra l'esito dell'azione e proponi nuove scelte.
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
