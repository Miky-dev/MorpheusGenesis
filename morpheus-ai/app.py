import streamlit as st
import logging
import os
import random
from dotenv import load_dotenv

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

# Import degli agenti residui non delegati interamente a engine
from agents.dm_agent import dm_agent
from agents.spawner_agent import spawner_agent
from agents.lore_agent import generate_story_bible, save_bible_to_memory
from agents.map_agent import map_generator_agent

from knowledge.chroma_store import DungeonMemory
from contracts.schemas import WorldState, Character, Enemy, StoryScene, WorldMap, LocationPopulation, StoryBible, Item
from setup_page import render_setup_page
from dataclasses import asdict
import uuid
from persistence import save_game_state, load_game_state

load_dotenv()

@st.dialog("🎒 Zaino Personale", width="large")
def show_inventory_modal(character: Character):
    st.markdown(f"### Equipaggiamento di {character.name}")
    st.caption(f"Classe: {character.char_class} | Livello: {character.level}")
    
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
        "Comune": "#b0b0b0",
        "Non Comune": "#1eff00",
        "Raro": "#0070dd",
        "Epico": "#a335ee",
        "Leggendario": "#ff8000"
    }

    def draw_category(title, icon, items):
        if not items:
            return
        st.markdown(f"#### {icon} {title}")
        for idx, it in enumerate(items):
            color = rarity_colors.get(it.rarity, "#ffffff")
            with st.container(border=True):
                # Formattazione Nome: Durabilità (armi/armature) vs Quantità (altro)
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
                
                if stats:
                    st.markdown("**Statistiche:** " + " | ".join(stats))
                st.caption(f"📖 *{it.lore_snippet}*")
                
                # Bottone per usare i consumabili
                if it.item_type == "consumable" and it.heal_amount:
                    if st.button(f"Usa {it.name}", key=f"use_{it.name}_{idx}"):
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

# --- GESTIONE SESSIONE E PERSISTENZA ---
if "session_id" not in st.session_state:
    # Se presente nell'URL, recuperiamo la sessione esistente
    if "session_id" in st.query_params:
        sid = st.query_params["session_id"]
        st.session_state.session_id = sid
        # Proviamo a caricare lo stato salvato
        if load_game_state(sid):
            logger.info(f"Sessione {sid} ripristinata con successo.")
        else:
            logger.warning(f"Impossibile ripristinare la sessione {sid}. Ricomincio da capo.")
            st.session_state.page = "setup"
    else:
        # Nuova sessione locale
        st.session_state.session_id = str(uuid.uuid4())[:8]

# Sincronizziamo l'URL con l'ID sessione corrente
if st.query_params.get("session_id") != st.session_state.session_id:
    st.query_params["session_id"] = st.session_state.session_id

if "page" not in st.session_state:
    st.session_state.page = "setup"

if st.session_state.page == "setup":
    render_setup_page()
    # Salviamo lo stato dopo il setup (se siamo passati a game lo faremo dopo)
    save_game_state(st.session_state.session_id)
    st.stop()

# Inizializziamo la memoria PRIMA della generazione del mondo
if "memory" not in st.session_state:
    st.session_state.memory = DungeonMemory(session_id=st.session_state.session_id)

# 1. Inizializzazione Session State (Membro B)
if "world_state" not in st.session_state:
    # Recuperiamo i dati dalla Setup Page
    p1_name = st.session_state.get("setup_p1_name", "Valerius")
    p1_class = st.session_state.get("setup_p1_class", "Guerriero")
    theme = st.session_state.get("setup_theme", "Cyberpunk")
    mood = st.session_state.get("setup_mood", "Oscuro")
    
    # --- Generazione Story Bible (La Musa) PRIMA di tutto ---
    if "story_bible" not in st.session_state:
        with st.spinner("📖 La Musa sta scrivendo la storia del mondo..."):
            # Se il giocatore non ha inserito un nome campagna, passiamo None per forzare la Musa a inventarne uno originale
            campaign_name = st.session_state.get("campaign_name", "").strip()
            session_name_to_pass = campaign_name if campaign_name else None

            bible = generate_story_bible(
                theme_id=theme,
                theme_description=f"Un mondo a tema {theme} con un tono {mood}",
                narrative_style=mood,
                difficulty=st.session_state.get("difficulty", "Normale"),
                session_name=session_name_to_pass,
                session_id=st.session_state.session_id
            )
            # Salviamo la Bible nella memoria ChromaDB per gli altri agenti
            save_bible_to_memory(bible, st.session_state.memory)
            st.session_state.story_bible = bible
            activate_first_locked_quest_if_none()

    # --- Generazione Mappa (Atlas) ---
    if "world_map" not in st.session_state:
        with st.spinner("Atlas sta disegnando i confini del mondo..."):
            bible = st.session_state.story_bible
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

    # Creiamo uno stato iniziale basato sull'input e differenziato per classe
    if p1_class == "Mago":
        hero = Character(name=p1_name, char_class=p1_class, hp=16, max_hp=16, ac=10)
        start_item = Item(name="Cristallo Risonante", item_type="key_item", rarity="Non Comune", description="Un frammento che pulsa di energia.", lore_snippet="Vibra quando c'è magia vicina.", quantity=1)
        weapon_item = Item(name="Bastone Nodoso", item_type="weapon", rarity="Comune", description="Un bastone di legno vecchio ma robusto.", attack_bonus=1, lore_snippet="Apparteneva a uno stregone novizio.", durability=100)
        hero.inventory.extend([start_item, weapon_item])
    elif p1_class == "Ladro":
        hero = Character(name=p1_name, char_class=p1_class, hp=22, max_hp=22, ac=12)
        start_item = Item(name="Set di Grimaldelli", item_type="key_item", rarity="Comune", description="Attrezzi essenziali per aprire serrature.", lore_snippet="Hanno aperto più forzieri di quanti ne ricordi.", quantity=5)
        weapon_item = Item(name="Pugnale Celato", item_type="weapon", rarity="Non Comune", description="Lama corta, facile da nascondere.", attack_bonus=2, lore_snippet="Porta il marchio della gilda dei ladri.", durability=100)
        hero.inventory.extend([start_item, weapon_item])
    else: # Guerriero o fallback
        hero = Character(name=p1_name, char_class=p1_class, hp=30, max_hp=30, ac=14)
        start_item = Item(name="Pozione Rigenerante", item_type="consumable", rarity="Non Comune", description="Densa fiala rossa che rinvigorisce il corpo.", heal_amount=15, lore_snippet="Sa di ferro e cenere.", quantity=3)
        weapon_item = Item(name="Spada d'Acciaio", item_type="weapon", rarity="Comune", description="Una spada a una mano standard.", attack_bonus=3, lore_snippet="Forgiata in massa per le guardie cittadine.", durability=100)
        hero.inventory.extend([start_item, weapon_item])
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
    st.session_state.current_scene = None  

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None

if "pending_combat_move" not in st.session_state:
    st.session_state.pending_combat_move = None

if "current_user_input" not in st.session_state:
    st.session_state.current_user_input = ""

if "cinematic_seen" not in st.session_state:
    st.session_state.cinematic_seen = False


from game_page import render_game_page

if st.session_state.page == "game":
    render_game_page()
