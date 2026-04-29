import streamlit as st
import logging
import os
import random
import uuid
from dotenv import load_dotenv
from dataclasses import asdict

# Import utilities e logica modulare
from utils import safe_agent_run, parse_json_response
from combat import CLASS_MOVES, resolve_combat_round
from engine import (
    activate_first_locked_quest_if_none,
    complete_talk_quest_if_matching,
    unlock_location_knowledge,
    get_known_locations_names,
    process_turn,
    ensure_location_population,
    trigger_ares_if_needed
)

# Import degli agenti e schemi
from agents.dm_agent import dm_agent
from agents.lore_agent import generate_story_bible, save_bible_to_memory
from contracts.schemas import (
    Location, WorldState, Character, Enemy, StoryScene, 
    WorldMap, LocationPopulation, StoryBible, Item
)
from knowledge.chroma_store import DungeonMemory
from setup_page import render_setup_page
from persistence import save_game_state, load_game_state
from game_page import render_game_page

load_dotenv()

# --- CONFIGURAZIONE LOGGER E AMBIENTE ---
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

# --- COMPONENTE UI: ZAINO PERSONALE ---
@st.dialog("🎒 Zaino Personale", width="large")
def show_inventory_modal(character: Character):
    st.markdown(f"### Equipaggiamento di {character.name}")
    st.caption(f"Classe: {character.char_class} | Livello: {character.level} | HP: {character.hp}/{character.max_hp}")
    
    if not character.inventory:
        st.info("Lo zaino è pietosamente vuoto. Trova del bottino esplorando il mondo!")
        return

    categories = {"weapon": [], "armor": [], "consumable": [], "key_item": []}
    for item in character.inventory:
        if item.item_type in categories:
            categories[item.item_type].append(item)
        else:
            categories["key_item"].append(item)

    rarity_colors = {
        "Comune": "#b0b0b0", "Non Comune": "#1eff00",
        "Raro": "#0070dd", "Epico": "#a335ee", "Leggendario": "#ff8000"
    }

    def draw_category(title, icon, items):
        if not items: return
        st.markdown(f"#### {icon} {title}")
        for idx, it in enumerate(items):
            color = rarity_colors.get(it.rarity, "#ffffff")
            with st.container(border=True):
                nome_formattato = f"{it.name}"
                if it.durability is not None:
                    nome_formattato += f" [Durabilità: {it.durability}%]"
                elif it.quantity > 1:
                    nome_formattato += f" (x{it.quantity})"
                
                st.markdown(f"<span style='color: {color}; font-weight: bold; font-size: 1.1em;'>{nome_formattato}</span> <span style='font-size: 0.8em; color: gray;'>[{it.rarity}]</span>", unsafe_allow_html=True)
                st.write(f"*{it.description}*")
                
                stats = []
                if it.attack_bonus: stats.append(f"⚔️ ATK +{it.attack_bonus}")
                if it.ac_bonus: stats.append(f"🛡️ CA +{it.ac_bonus}")
                if it.heal_amount: stats.append(f"❤️ Cura {it.heal_amount} HP")
                if it.value > 0: stats.append(f"🪙 Valore: {it.value}")
                
                if stats: st.markdown("**Statistiche:** " + " | ".join(stats))
                st.caption(f"📖 *{it.lore_snippet}*")
                
                if it.item_type == "consumable" and it.heal_amount:
                    if st.button(f"Usa {it.name}", key=f"use_{character.name}_{it.name}_{idx}"):
                        character.hp = min(character.max_hp, character.hp + it.heal_amount)
                        it.quantity -= 1
                        if it.quantity <= 0:
                            character.inventory.remove(it)
                        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        draw_category("Armi", "⚔️", categories["weapon"])
        draw_category("Armature", "🛡️", categories["armor"])
    with col2:
        draw_category("Consumabili", "🧪", categories["consumable"])
        draw_category("Oggetti Speciali", "📜", categories["key_item"])

# --- FUNZIONE HELPER: CREAZIONE PERSONAGGI ---
def generate_starting_character(name: str, char_class: str, char_id: str) -> Character:
    """Genera un personaggio e il suo equipaggiamento iniziale in base alla classe."""
    hero = Character(id=char_id, name=name, char_class=char_class, hp=20, max_hp=20, ac=10) # Valori base
    
    if char_class == "Mago":
        hero.hp, hero.max_hp, hero.ac = 16, 16, 10
        hero.inventory.extend([
            Item(name="Cristallo Risonante", item_type="key_item", rarity="Non Comune", description="Un frammento che pulsa di energia.", lore_snippet="Vibra quando c'è magia vicina.", quantity=1),
            Item(name="Bastone Nodoso", item_type="weapon", rarity="Comune", description="Un bastone di legno vecchio ma robusto.", attack_bonus=1, lore_snippet="Apparteneva a uno stregone novizio.", durability=100)
        ])
    elif char_class == "Ladro":
        hero.hp, hero.max_hp, hero.ac = 22, 22, 12
        hero.inventory.extend([
            Item(name="Set di Grimaldelli", item_type="key_item", rarity="Comune", description="Attrezzi essenziali per aprire serrature.", lore_snippet="Hanno aperto più forzieri di quanti ne ricordi.", quantity=5),
            Item(name="Pugnale Celato", item_type="weapon", rarity="Non Comune", description="Lama corta, facile da nascondere.", attack_bonus=2, lore_snippet="Porta il marchio della gilda dei ladri.", durability=100)
        ])
    else: # Guerriero o fallback
        hero.hp, hero.max_hp, hero.ac = 30, 30, 14
        hero.inventory.extend([
            Item(name="Pozione Rigenerante", item_type="consumable", rarity="Non Comune", description="Densa fiala rossa che rinvigorisce il corpo.", heal_amount=15, lore_snippet="Sa di ferro e cenere.", quantity=3),
            Item(name="Spada d'Acciaio", item_type="weapon", rarity="Comune", description="Una spada a una mano standard.", attack_bonus=3, lore_snippet="Forgiata in massa per le guardie cittadine.", durability=100)
        ])
    return hero


# --- GESTIONE SESSIONE E PERSISTENZA ---
if "session_id" not in st.session_state:
    if "session_id" in st.query_params:
        sid = st.query_params["session_id"]
        st.session_state.session_id = sid
        if load_game_state(sid):
            logger.info(f"Sessione {sid} ripristinata con successo.")
        else:
            logger.warning(f"Impossibile ripristinare la sessione {sid}. Ricomincio da capo.")
            st.session_state.page = "setup"
    else:
        st.session_state.session_id = str(uuid.uuid4())[:8]

if st.query_params.get("session_id") != st.session_state.session_id:
    st.query_params["session_id"] = st.session_state.session_id

if "page" not in st.session_state:
    st.session_state.page = "setup"

# ROTTA SETUP
if st.session_state.page == "setup":
    render_setup_page()
    save_game_state(st.session_state.session_id)
    st.stop()

# ─────────────────────────────────────────────────────────────
# INIZIALIZZAZIONE MONDO (Sessione Zero digitale)
# Ogni step è idempotente: non si rigenera se già presente.
# ─────────────────────────────────────────────────────────────

# Leggiamo il tema/mood dai dati di setup (con fallback sicuri)
_theme = st.session_state.get("setup_theme", "Fantasy")
_mood  = st.session_state.get("setup_mood",  "Eroico")

# Mostriamo la UI di caricamento solo se stiamo ancora inizializzando
_needs_init = (
    "memory" not in st.session_state
    or "story_bible" not in st.session_state
    or "world_map" not in st.session_state
    or "world_state" not in st.session_state
)

if _needs_init:
    st.markdown(f"""
        <div style="
            text-align:center; padding: 60px 20px 40px;
            background: linear-gradient(180deg, #0e0e0f 0%, #0d0d1a 100%);
            border: 1px solid rgba(129,214,190,0.1); border-radius: 20px;
            margin: 20px 0;
        ">
            <div style="font-family:'Manrope',sans-serif; font-size:0.75rem; letter-spacing:0.2em;
                        text-transform:uppercase; color:#81d6be; margin-bottom:12px;">
                Morpheus Genesis
            </div>
            <div style="font-family:'Manrope',sans-serif; font-size:2rem; font-weight:700;
                        color:#e5e2e1; margin-bottom:8px;">
                Sessione Zero in corso...
            </div>
            <div style="font-size:0.95rem; color:#6b7280; max-width:500px; margin:0 auto;">
                Il Dungeon Master sta preparando il mondo di <strong style="color:#bec9c4">{_theme}</strong>
                con tono <strong style="color:#bec9c4">{_mood}</strong>.
            </div>
        </div>
    """, unsafe_allow_html=True)
    _progress = st.progress(0, text="Inizializzazione...")

# ── STEP 0: Memoria ChromaDB ──────────────────────────────────
if "memory" not in st.session_state:
    if _needs_init:
        _progress.progress(10, text="🧠 Attivazione memoria RAG...")
    st.session_state.memory = DungeonMemory(session_id=st.session_state.session_id)
    logger.info("DungeonMemory inizializzata per sessione %s", st.session_state.session_id)

# ── STEP 1: Story Bible (La Musa) ────────────────────────────
if "story_bible" not in st.session_state:
    if _needs_init:
        _progress.progress(25, text="📖 La Musa sta scrivendo la storia del mondo...")
    with st.spinner("📖 La Musa elabora la lore..."):
        campaign_name = st.session_state.get("campaign_name", "").strip()
        bible = generate_story_bible(
            theme_id=_theme,
            theme_description=f"Un mondo a tema {_theme} con tono narrativo {_mood}",
            narrative_style=_mood,
            difficulty=st.session_state.get("difficulty", "Normale"),
            session_name=campaign_name if campaign_name else None,
            session_id=st.session_state.session_id
        )
        save_bible_to_memory(bible, st.session_state.memory)
        st.session_state.story_bible = bible
        activate_first_locked_quest_if_none()
        logger.info("Story Bible generata: '%s'", bible.title)

# ── STEP 2: Mappa di Gioco (Atlas) ───────────────────────────
if "world_map" not in st.session_state:
    if _needs_init:
        _progress.progress(55, text="🗺️ Atlas traccia i confini del mondo...")
    with st.spinner("🗺️ Atlas disegna la mappa..."):
        bible = st.session_state.story_bible
        # spawn_id garantito pari all'herald_location_id della bible
        spawn_id = bible.herald_location_id

        locations = [
            Location(
                id_name=spawn_id,
                name="Punto di Partenza",
                description="Il luogo sicuro da cui inizia l'avventura. Qui l'araldo attende il party.",
                type="hub",
                connected_to=["loc_crossroads"],
                difficulty_level=0,
                x=0, y=0
            ),
            Location(
                id_name="loc_crossroads",
                name="Crocevia dei Destini",
                description="Un nodo di strade che si dirama verso pericoli crescenti.",
                type="corridor",
                connected_to=[spawn_id, "loc_dungeon"],
                difficulty_level=1,
                x=2, y=0
            ),
            Location(
                id_name="loc_dungeon",
                name="Cuore delle Tenebre",
                description="Il fulcro della minaccia. Pochi entrano, meno ancora escono.",
                type="dungeon",
                connected_to=["loc_crossroads"],
                difficulty_level=3,
                x=4, y=0
            ),
        ]

        st.session_state.world_map = WorldMap(
            region_name=bible.title,
            locations=locations,
            spawn_location_id=spawn_id
        )
        st.session_state.current_location_id = spawn_id

        if "visited_locations" not in st.session_state:
            st.session_state.visited_locations = {}

        logger.info("Mappa generata con %d location, spawn: %s", len(locations), spawn_id)

# ── STEP 3: Party + WorldState ───────────────────────────────
if "world_state" not in st.session_state:
    if _needs_init:
        _progress.progress(78, text="⚔️ Il party si prepara all'avventura...")
    with st.spinner("⚔️ I personaggi indossano l'equipaggiamento..."):
        # Legge i dati dal setup; fallback a un guerriero senza nome se mancante
        raw_party = st.session_state.get(
            "setup_party",
            [{"name": "Avventuriero", "class": "Guerriero"}]
        )

        party: list[Character] = []
        for idx, player_data in enumerate(raw_party):
            char_id = f"pg_{idx}"
            hero = generate_starting_character(
                name=player_data["name"],
                char_class=player_data["class"],
                char_id=char_id
            )
            party.append(hero)
            logger.info(
                "Personaggio creato: %s (%s) — HP %d/%d",
                hero.name, hero.char_class, hero.hp, hero.max_hp
            )

        spawn_id = st.session_state.world_map.spawn_location_id
        st.session_state.world_state = WorldState(
            theme=_theme,
            party=party,
            active_enemies=[],
            current_location=spawn_id
        )

        # Sblocca spawn + location adiacenti allo spawn (Fog of War iniziale)
        spawn_loc = next(
            (l for l in st.session_state.world_map.locations if l.id_name == spawn_id),
            None
        )
        if spawn_loc:
            st.session_state.world_state.known_locations = list(
                set([spawn_loc.id_name] + spawn_loc.connected_to)
            )

# ── STEP 4: Completamento progress e pulizia ─────────────────
if _needs_init:
    _progress.progress(100, text="✅ Il mondo è pronto. Buona avventura!")
    import time as _time
    _time.sleep(0.6)
    _progress.empty()


# --- VARIABILI DI STATO AGGIUNTIVE PER IL FLUSSO MULTIPLAYER ---
if "stats_assigned" not in st.session_state:
    st.session_state.stats_assigned = False

if "active_player_id" not in st.session_state:
    # Tiene traccia di chi sta parlando in questo momento (es. "pg_0")
    st.session_state.active_player_id = st.session_state.world_state.party[0].id if st.session_state.world_state.party else None

if "last_narrative" not in st.session_state:
    st.session_state.last_narrative = ""

if "current_scene" not in st.session_state:
    st.session_state.current_scene = None  

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None

if "pending_combat_move" not in st.session_state:
    st.session_state.pending_combat_move = None

if "current_user_input" not in st.session_state:
    st.session_state.current_user_input = ""

if "cinematic_seen" not in st.session_state:
    st.session_state.cinematic_seen = False

# ROTTA GIOCO
if st.session_state.page == "game":
    render_game_page()