import streamlit as st
import random
import os
from dataclasses import asdict
import uuid
import logging

from utils import safe_agent_run, parse_json_response
from combat import CLASS_MOVES, resolve_combat_round
from engine import (
    activate_first_locked_quest_if_none,
    complete_talk_quest_if_matching,
    unlock_location_knowledge,
    get_known_locations_names,
    process_turn,
    ensure_location_population,
    trigger_ares_if_needed,
    advance_turn  # <-- IMPORTANTE: Aggiunto l'import per passare il turno
)
from agents.dm_agent import dm_agent
from contracts.schemas import Character, Enemy, StoryScene
from persistence import save_game_state

logger = logging.getLogger("morpheus_ai")

def get_morpheus_css():
    return """
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,200..800;1,6..72,200..800&family=Inter:wght@100;200;300;400;500;600;700;800;900&display=swap" rel="stylesheet"/>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
    <style>
    :root {
        --primary:   #6dddff;
        --secondary: #00fd87;
        --tertiary:  #d575ff;
        --error:     #ff716c;
        --surface-dim:           #141416;
        --surface-container-low: #1a1a1c;
        --surface-container:     #222224;
        --surface-container-high:#2a2a2c;
        --surface-container-highest: #323234;
        --surface-variant:       #262627;
        --outline:               #767576;
        --outline-variant:       #5e5e60;
        --on-surface:            #f0f0f0;
        --on-surface-variant:    #b8b5b6;
    }
    .stApp { background-color: var(--surface-dim) !important; font-family: 'Newsreader', Georgia, serif !important; }
    h1, h2, h3, h4, h5, h6 { font-family: 'Space Grotesk', sans-serif !important; color: var(--on-surface) !important; }
    #MainMenu, footer { display: none; } header[data-testid="stHeader"] { background: transparent !important; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1.5rem !important; max-width: 650px !important; margin: 0 auto !important; }
    hr { border-color: rgba(72,72,73,0.3) !important; margin: 1rem 0 !important; }
    h1[data-testid="stTitle"], h1 { font-family: 'Space Grotesk', sans-serif !important; font-size: 1.5rem !important; font-weight: 700 !important; letter-spacing: -0.02em !important; color: var(--primary) !important; text-transform: uppercase !important; border-bottom: 1px solid rgba(72,72,73,0.15) !important; padding-bottom: 0.5rem !important; margin-bottom: 1rem !important; }
    .hud-card { background: var(--surface-container); border-radius: 12px; padding: 12px 14px; border-left: 2px solid var(--primary); box-shadow: 0 0 20px rgba(109,221,255,0.1); margin-bottom: 6px; }
    .hud-card-inactive { background: var(--surface-container); border-radius: 12px; padding: 12px 14px; border-left: 2px solid rgba(72,72,73,0.3); margin-bottom: 6px; }
    .hud-name { font-family: 'Inter', sans-serif; font-size: 10px; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--primary); margin-bottom: 4px; }
    .hud-name-inactive { font-family: 'Inter', sans-serif; font-size: 10px; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--on-surface); margin-bottom: 4px; }
    .hp-bar-track { background: var(--surface-container-highest); border-radius: 9999px; height: 6px; width: 100%; overflow: hidden; margin-bottom: 4px; }
    .hp-bar-fill-green { height: 100%; background: var(--secondary); border-radius: 9999px; box-shadow: 0 0 8px rgba(0,253,135,0.4); }
    .hp-bar-fill-yellow { height: 100%; background: #fbbf24; border-radius: 9999px; box-shadow: 0 0 8px rgba(251,191,36,0.4); }
    .hp-bar-fill-red { height: 100%; background: var(--error); border-radius: 9999px; box-shadow: 0 0 8px rgba(255,113,108,0.4); }
    .hp-label { font-family: 'Inter', sans-serif; font-size: 10px; color: var(--on-surface-variant); margin: 0; }
    .narrative-box { position: relative; padding: 24px 28px; border-left: 2px solid var(--primary); background: transparent; margin: 16px 0; }
    .narrative-gm-label { font-family: 'Inter', sans-serif; font-size: 10px; font-weight: 900; letter-spacing: 0.2em; text-transform: uppercase; color: var(--primary); margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
    .narrative-gm-label::after { content: ''; width: 4px; height: 4px; border-radius: 50%; background: var(--outline-variant); display: inline-block; }
    .narrative-text { font-family: 'Newsreader', Georgia, serif; font-size: 1.2rem; line-height: 1.8; color: var(--on-surface); font-style: italic; }
    .agent-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
    .agent-pill { display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 9999px; font-family: 'Inter', sans-serif; font-size: 9px; font-weight: 700; letter-spacing: 0.15em; text-transform: uppercase; border: 1px solid; cursor: default; }
    .pill-dm { background: rgba(109,221,255,0.05); border-color: rgba(109,221,255,0.25); color: var(--primary); }
    .pill-lore { background: rgba(213,117,255,0.05); border-color: rgba(213,117,255,0.25); color: var(--tertiary); }
    .pill-rules { background: rgba(0,253,135,0.05); border-color: rgba(0,253,135,0.25); color: var(--secondary); }
    .pill-combat { background: rgba(255,113,108,0.05); border-color: rgba(255,113,108,0.25); color: var(--error); }
    .pill-atlas { background: rgba(109,221,255,0.05); border-color: rgba(109,221,255,0.15); color: var(--primary); }
    .stButton > button { background: var(--surface-container-highest) !important; color: var(--on-surface) !important; border: 1px solid rgba(72,72,73,0.35) !important; border-radius: 8px !important; padding: 6px 12px !important; font-family: 'Space Grotesk', sans-serif !important; font-size: 0.75rem !important; font-weight: 600 !important; transition: all 0.2s ease !important; width: 100% !important; text-transform: none !important; min-height: 36px !important; }
    .stButton > button:hover { border-color: rgba(109,221,255,0.5) !important; color: var(--primary) !important; background: rgba(109,221,255,0.05) !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, rgba(109,221,255,0.15), rgba(0,195,235,0.1)) !important; border-color: rgba(109,221,255,0.4) !important; color: var(--primary) !important; }
    .stButton > button[kind="primary"]:hover { background: linear-gradient(135deg, rgba(109,221,255,0.25), rgba(0,195,235,0.15)) !important; box-shadow: 0 0 20px rgba(109,221,255,0.15) !important; }
    div[data-testid="stHorizontalBlock"] .stButton > button:has-text("🗡️") { border-color: rgba(255,113,108,0.3) !important; }
    section[data-testid="stSidebar"] { background-color: #1f1f22 !important; border-right: 1px solid rgba(109,221,255,0.2) !important; }
    section[data-testid="stSidebar"] h3 { font-family: 'Inter', sans-serif !important; font-size: 9px !important; letter-spacing: 0.2em !important; text-transform: uppercase !important; color: var(--on-surface-variant) !important; font-weight: 700 !important; }
    div[data-testid="stInfo"] { background: rgba(109,221,255,0.05) !important; border: 1px solid rgba(109,221,255,0.2) !important; border-radius: 10px !important; color: var(--on-surface) !important; }
    div[data-testid="stInfo"] svg { display: none; }
    div[data-testid="stSuccess"] { background: rgba(0,253,135,0.05) !important; border: 1px solid rgba(0,253,135,0.2) !important; border-radius: 10px !important; color: var(--secondary) !important; }
    div[data-testid="stError"] { background: rgba(255,113,108,0.05) !important; border: 1px solid rgba(255,113,108,0.2) !important; border-radius: 10px !important; color: var(--error) !important; }
    .section-label { font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--on-surface-variant); margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(72,72,73,0.15); }
    div[data-testid="stContainer"] { border-color: rgba(72,72,73,0.2) !important; border-radius: 12px !important; background: var(--surface-container-low) !important; }
    div[data-testid="stChatInput"] { display: none !important; }
    .fixed-inventory { display: none; }
    div[class*="stBottom"], div[data-testid="stBottomBlockContainer"], div[data-testid="stBottom"], .stChatFloatingInputContainer { background: transparent !important; background-color: transparent !important; border: none !important; box-shadow: none !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) { position: fixed !important; bottom: 1.2rem !important; left: 50% !important; transform: translateX(-50%) !important; width: 90% !important; max-width: 650px !important; height: auto !important; min-height: 54px !important; z-index: 9999 !important; background-color: transparent !important; background: transparent !important; backdrop-filter: blur(12px) !important; -webkit-backdrop-filter: blur(12px) !important; border: 1px solid rgba(109,221,255,0.4) !important; border-radius: 9999px !important; padding: 0 8px 0 24px !important; box-shadow: 0 0 25px rgba(109,221,255,0.2) !important; transition: border-color 0.2s, box-shadow 0.2s !important; display: flex !important; flex-direction: column !important; justify-content: center !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker):focus-within { border-color: rgba(109,221,255,0.8) !important; box-shadow: 0 0 35px rgba(109,221,255,0.35) !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) > div { margin-top: 0 !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) [data-testid="stHorizontalBlock"] { gap: 0 !important; align-items: center !important; height: 100% !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) [data-testid="stTextInputRootElement"], 
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) [data-testid="stTextInputRootElement"] > div, 
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) [data-testid="stTextInputRootElement"] > div > div { background-color: transparent !important; background: transparent !important; border: none !important; box-shadow: none !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) [data-testid="stTextInput"] input { background: transparent !important; border: none !important; box-shadow: none !important; outline: none !important; color: #6dddff !important; font-family: 'Inter', sans-serif !important; font-size: 0.95rem !important; caret-color: #6dddff; padding: 8px 0 !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) [data-testid="stTextInput"] input::placeholder { color: rgba(109,221,255,0.3) !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) [data-testid="stTextInput"] { margin-bottom: 0 !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) [data-testid="stTextInput"] label, 
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) [data-testid="InputInstructions"], 
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) [class*="InputInstructions"] { display: none !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) button { background: transparent !important; border: none !important; box-shadow: none !important; color: #6dddff !important; width: 42px !important; height: 42px !important; min-height: 42px !important; padding: 0 !important; border-radius: 50% !important; transition: color 0.2s, background 0.2s !important; display: flex !important; align-items: center !important; justify-content: center !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) button:hover { color: #fff !important; background: rgba(109,221,255,0.1) !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) button p { display: none !important; }
    div[data-testid="stVerticalBlock"]:has(> div.element-container div.pill-input-marker) button span[data-testid="stIconMaterial"] { font-size: 24px !important; margin: 0 !important; }
    
    /* HUD Inventory Button styling */
    div.element-container:has(button[key="hud_inv_btn"]) button {
        background: rgba(109,221,255,0.05) !important;
        border: 1px solid rgba(109,221,255,0.2) !important;
        color: var(--primary) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 10px !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        height: 32px !important;
        margin-top: -4px !important;
    }
    div.element-container:has(button[key="hud_inv_btn"]) button:hover {
        background: rgba(109,221,255,0.1) !important;
        border-color: var(--primary) !important;
    }
    section[data-testid="stSidebar"] .stButton > button { background: rgba(109,221,255,0.05) !important; border: 1px solid rgba(109,221,255,0.2) !important; color: var(--primary) !important; text-transform: uppercase !important; font-size: 10px !important; letter-spacing: 0.1em !important; }
    section[data-testid="stSidebar"] .stButton > button:hover { background: rgba(109,221,255,0.1) !important; border-color: var(--primary) !important; }
    details[data-testid="stExpander"] { background: var(--surface-container) !important; border: 1px solid rgba(72,72,73,0.2) !important; border-radius: 10px !important; }
    details[data-testid="stExpander"] summary { font-family: 'Inter', sans-serif !important; font-size: 11px !important; font-weight: 600 !important; letter-spacing: 0.05em !important; color: var(--on-surface-variant) !important; text-transform: uppercase !important; }
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--outline-variant); border-radius: 10px; }

    /* Hide spinner text, keep only the spinning icon */
    div[data-testid="stSpinner"] p { display: none !important; }
    div[data-testid="stSpinner"] { display: flex !important; align-items: center !important; justify-content: center !important; }

    /* DM Thinking animation */
    @keyframes dmPulse {
        0%, 100% { opacity: 0.2; transform: scale(0.8); }
        50% { opacity: 1; transform: scale(1.2); }
    }
    .dm-thinking {
        display: flex; align-items: center; gap: 6px;
        padding: 24px 28px;
        border-left: 2px solid rgba(109,221,255,0.4);
    }
    .dm-thinking-label {
        font-family: 'Inter', sans-serif; font-size: 10px; font-weight: 700;
        letter-spacing: 0.2em; text-transform: uppercase; color: var(--primary);
        margin-right: 12px;
    }
    .dm-dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: #6dddff;
        animation: dmPulse 1.2s ease-in-out infinite;
    }
    .dm-dot:nth-child(2) { animation-delay: 0.2s; }
    .dm-dot:nth-child(3) { animation-delay: 0.4s; }
    .dm-dot:nth-child(4) { animation-delay: 0.6s; }
    .content-spacer { height: 80px; width: 100%; }

    /* --- HUD STATS TOOLTIP --- */
    .hud-card { position: relative; cursor: pointer; }
    .hud-tooltip { 
        visibility: hidden; opacity: 0; position: absolute; bottom: 105%; left: 0; 
        width: 100%; min-width: 190px; background-color: var(--surface-container-highest); 
        border: 1px solid rgba(109,221,255,0.4); border-radius: 8px; padding: 12px; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.8); transition: all 0.2s ease-in-out; 
        z-index: 1000; transform: translateY(10px); backdrop-filter: blur(10px);
    }
    .hud-card:hover .hud-tooltip, .hud-card:active .hud-tooltip { 
        visibility: visible; opacity: 1; transform: translateY(0); 
    }
    .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
    .stat-item { 
        font-family: 'Inter', sans-serif; font-size: 10px; display: flex; 
        justify-content: space-between; background: rgba(255,255,255,0.03); 
        padding: 4px 8px; border-radius: 4px; 
    }
    .stat-label { color: var(--on-surface-variant); font-weight: 700; }
    .stat-val { color: var(--primary); font-weight: 900; }

    </style>
    """

def draw_hp_bar(entity, is_hero=True, label_prefix=""):
    # Accorpiamo il prefisso (es. "TURNO DI:") al nome se esiste
    nome_mostrato = f"{label_prefix} {entity.name}" if label_prefix else entity.name
    current_hp = entity.hp
    max_hp = entity.max_hp
    pct = max(0, current_hp / max_hp)
    fill_class = "hp-bar-fill-green" if pct > 0.6 else "hp-bar-fill-yellow" if pct > 0.3 else "hp-bar-fill-red"
    card_class = "hud-card" if is_hero else "hud-card-inactive"
    name_class = "hud-name" if is_hero else "hud-name-inactive"

    # Creiamo il tooltip solo se l'entità ha le statistiche (gli eroi)
    tooltip_html = ""
    if is_hero and hasattr(entity, 'strength'):
        tooltip_html = (
            f"<div class='hud-tooltip'>"
            f"<div style=\"font-family:'Space Grotesk', sans-serif; font-size:12px; font-weight:bold; color:var(--primary); margin-bottom:8px; border-bottom:1px solid rgba(109,221,255,0.3); padding-bottom:4px;\">SCHEDA STATISTICHE</div>"
            f"<div class='stat-grid'>"
            f"<div class='stat-item'><span class='stat-label'>FOR</span> <span class='stat-val'>{entity.strength}</span></div>"
            f"<div class='stat-item'><span class='stat-label'>DES</span> <span class='stat-val'>{entity.dexterity}</span></div>"
            f"<div class='stat-item'><span class='stat-label'>COS</span> <span class='stat-val'>{entity.constitution}</span></div>"
            f"<div class='stat-item'><span class='stat-label'>INT</span> <span class='stat-val'>{entity.intelligence}</span></div>"
            f"<div class='stat-item'><span class='stat-label'>SAG</span> <span class='stat-val'>{entity.wisdom}</span></div>"
            f"<div class='stat-item'><span class='stat-label'>CAR</span> <span class='stat-val'>{entity.charisma}</span></div>"
            f"</div>"
            f"<div class='stat-item' style='margin-top:6px; justify-content:center; gap:8px; background: rgba(109,221,255,0.1); border: 1px solid rgba(109,221,255,0.2);'>"
            f"<span class='stat-label'>CLASSE ARMATURA (CA)</span> <span class='stat-val'>{entity.ac}</span>"
            f"</div>"
            f"</div>"
        )

    st.markdown(
        f"<div class='{card_class}'>"
        f"{tooltip_html}"
        f"<div class='{name_class}'>{nome_mostrato.upper()}</div>"
        f"<div class='hp-bar-track'><div class='{fill_class}' style='width:{pct*100:.0f}%'></div></div>"
        f"<p class='hp-label' style='margin-top:4px;'>Salute: {current_hp} / {max_hp} HP</p>"
        f"</div>",
        unsafe_allow_html=True
    )

@st.dialog("🎒 Zaino Personale", width="large")
def show_inventory_modal(character: Character):
    st.markdown(f"### Equipaggiamento di {character.name}")
    st.caption(f"Classe: {character.char_class} | Livello: {character.level}")
    if not character.inventory:
        st.info("Lo zaino è vuoto.")
        return
    categories = {"weapon": [], "armor": [], "consumable": [], "key_item": []}
    for item in character.inventory:
        if item.item_type in categories: categories[item.item_type].append(item)
        else: categories["key_item"].append(item)

    def draw_category(title, icon, items):
        if not items: return
        st.markdown(f"#### {icon} {title}")
        for idx, it in enumerate(items):
            with st.container(border=True):
                nome_formattato = f"{it.name}"
                if it.durability is not None:
                    nome_formattato += f" [Durabilità: {it.durability}%]"
                elif it.quantity > 1:
                    nome_formattato += f" (x{it.quantity})"
                    
                st.markdown(f"<span style='font-weight: bold;'>{nome_formattato}</span> <span style='font-size: 0.8em; color: gray;'>[{it.rarity}]</span>", unsafe_allow_html=True)
                st.write(f"*{it.description}*")
                stats = []
                if it.attack_bonus: stats.append(f"⚔️ ATK +{it.attack_bonus}")
                if it.ac_bonus: stats.append(f"🛡️ CA +{it.ac_bonus}")
                if it.heal_amount: stats.append(f"❤️ Cura {it.heal_amount} HP")
                if it.value > 0: stats.append(f"🪙 Valore: {it.value}")
                if stats: st.markdown("**Statistiche:** " + " | ".join(stats))
                st.caption(f"📖 *{it.lore_snippet}*")
                
                if it.item_type == "consumable" and it.heal_amount:
                    if st.button(f"Usa {it.name}", key=f"use_game_{it.name}_{idx}"):
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

def render_game_page():
    # Hidden div prevents markdown from parsing indented styles as text blocks!
    st.markdown(f"<div style='display:none'>{get_morpheus_css()}</div>", unsafe_allow_html=True)
    bible = st.session_state.get("story_bible", None)

    # Identifica il giocatore attivo per questo turno
    active_player = next((p for p in st.session_state.world_state.party if p.id == st.session_state.active_player_id), None)
    
    if not active_player:
        st.error("Errore di caricamento: Nessun giocatore attivo trovato.")
        return

    if bible and not st.session_state.cinematic_seen:
        st.markdown(f"""
            <div style="background: linear-gradient(180deg, #0e0e0f 0%, #0e0e1f 100%); border: 1px solid rgba(109,221,255,0.15); border-radius: 16px; padding: 48px; margin: 20px 0; box-shadow: 0 0 60px rgba(109,221,255,0.06);">
                <div style="font-family: 'Inter', sans-serif; font-size: 10px; font-weight: 700; letter-spacing: 0.3em; text-transform: uppercase; color: #6dddff; text-align: center; margin-bottom: 16px;">Morpheus Genesis · Opening Cinematic</div>
                <h1 style="text-align: center; color: #ffffff; font-family: 'Space Grotesk', sans-serif; font-size: 2.4rem; font-weight: 700; margin-bottom: 32px; letter-spacing: -0.02em;">{bible.title}</h1>
                <div style="color: #adaaab; font-size: 1.15rem; line-height: 1.9; font-family: 'Newsreader', Georgia, serif; font-style: italic; text-align: justify; border-left: 2px solid #6dddff; padding-left: 28px;">{bible.opening_cinematic}</div>
            </div>
        """, unsafe_allow_html=True)
        col_center = st.columns([1, 2, 1])[1]
        with col_center:
            if st.button("👁️ APRI GLI OCCHI", use_container_width=True, type="primary"):
                st.session_state.cinematic_seen = True
                save_game_state(st.session_state.session_id)
                st.rerun()
        st.stop()

    # 2. NUOVA FASE: ASSEGNAZIONE STATISTICHE
    if st.session_state.cinematic_seen and not st.session_state.get("stats_assigned", False):
        st.markdown("## 🎲 Il Destino prende forma")
        st.markdown("*Mentre la visione svanisce, prendete coscienza dei vostri corpi...*")
        
        # Iteriamo su tutti i membri del party per mostrare i loro tiri
        for char in st.session_state.world_state.party:
            with st.container(border=True):
                st.markdown(f"### {char.name} ({char.char_class})")
                
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                # Funzione per simulare il tiro 4d6 scarta il più basso (classico D&D)
                def roll_stat():
                    rolls = sorted([random.randint(1, 6) for _ in range(4)])
                    return sum(rolls[1:])

                # Se le statistiche sono ancora a 10 (valore di default), mostriamo il bottone per tirare
                if char.strength == 10 and st.button(f"Tira per {char.name}", key=f"roll_{char.id}"):
                    char.strength = roll_stat()
                    char.dexterity = roll_stat()
                    char.constitution = roll_stat()
                    char.intelligence = roll_stat()
                    char.wisdom = roll_stat()
                    char.charisma = roll_stat()
                    save_game_state(st.session_state.session_id)
                    st.rerun()
                
                # Se ha tirato, mostriamo i risultati
                if char.strength != 10:
                    col1.metric("FORZA", char.strength)
                    col2.metric("DESTREZZA", char.dexterity)
                    col3.metric("COSTITUZIONE", char.constitution)
                    col4.metric("INTELLIGENZA", char.intelligence)
                    col5.metric("SAGGEZZA", char.wisdom)
                    col6.metric("CARISMA", char.charisma)

        st.divider()
        
        # Controlliamo se TUTTI hanno tirato le statistiche
        tutti_pronti = all(c.strength != 10 for c in st.session_state.world_state.party)
        
        if tutti_pronti:
            col_start = st.columns([1, 2, 1])[1]
            with col_start:
                if st.button("⚔️ INIZIA L'AVVENTURA", use_container_width=True, type="primary"):
                    st.session_state.stats_assigned = True
                    save_game_state(st.session_state.session_id)
                    st.rerun()
        else:
            st.info("Tutti i giocatori devono tirare i dadi prima di poter iniziare.")
            
        st.stop() # Blocca l'esecuzione finché le statistiche non sono confermate

    title_text = bible.title if bible else "Project Morpheus"
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:0.5rem;">
            <div style="font-family:'Space Grotesk',sans-serif; font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#6dddff;">Morpheus Genesis</div>
            <div style="width:4px; height:4px; border-radius:50%; background:#484849;"></div>
            <div style="font-family:'Inter',sans-serif; font-size:9px; letter-spacing:0.15em; text-transform:uppercase; color:#767576;">Turn {st.session_state.world_state.turn_number}</div>
        </div>
        <h1 style="font-family:'Space Grotesk',sans-serif; font-size:1.4rem; font-weight:700; letter-spacing:-0.02em; color:#6dddff; text-transform:uppercase; margin:0 0 1rem 0; padding-bottom:0.5rem; border-bottom:1px solid rgba(72,72,73,0.15);">{title_text}</h1>
    """, unsafe_allow_html=True)

    # 3. GENERAZIONE DELLA SCENA INIZIALE (Il Gancio)
    if st.session_state.stats_assigned and not st.session_state.last_narrative:
        with st.spinner("📜 Il Game Master sta tessendo l'inizio della vostra storia..."):
            bible = st.session_state.get("story_bible")
            active_player = next((p for p in st.session_state.world_state.party if p.id == st.session_state.get("active_player_id")), st.session_state.world_state.party[0])
            
            from engine import genera_scena_di_apertura
            scena_iniziale = genera_scena_di_apertura(active_player)
            
            if scena_iniziale:
                st.session_state.current_scene = scena_iniziale
                st.session_state.last_narrative = scena_iniziale.narration
                save_game_state(st.session_state.session_id)
                st.rerun()
        st.stop()

    # 4. INTERFACCIA DI GIOCO STANDARD (HUD, Mappa, Chat...)
    # (Da qui in poi, sappiamo che last_narrative esiste)
    
    activate_first_locked_quest_if_none()

    with st.sidebar:
        if bible:
            st.markdown("<div style='font-family:\"Inter\",sans-serif; font-size:9px; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:#adaaab; margin-bottom:8px;'>Main Objective</div>", unsafe_allow_html=True)
            st.info(f"**{bible.main_objective}**")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown("<div style='font-family:\"Inter\",sans-serif; font-size:9px; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:#adaaab; margin-bottom:8px; padding-top:8px; border-top:1px solid rgba(72,72,73,0.15);'>Active Quests</div>", unsafe_allow_html=True)
            
            quest_chain = st.session_state.story_bible.quest_chain
            active_quests = [sq for sq in quest_chain if sq.status == "active"]
            if active_quests:
                for sq in active_quests:
                    st.markdown(f"<div style='background:rgba(109,221,255,0.04); border:1px solid rgba(109,221,255,0.12); border-radius:8px; padding:10px 12px; margin-bottom:6px;'><div style='font-family:\"Space Grotesk\",sans-serif; font-size:12px; font-weight:600; color:#ffffff; margin-bottom:4px;'>{sq.title}</div><div style='font-family:\"Newsreader\",serif; font-size:11px; color:#adaaab; font-style:italic;'>{sq.description}</div></div>", unsafe_allow_html=True)
            else:
                st.markdown("<p style='font-family:Inter,sans-serif; font-size:11px; color:#767576; font-style:italic;'>Nessuna missione attiva.</p>", unsafe_allow_html=True)
            
            with st.expander("System Debug"):
                st.json(asdict(st.session_state.world_state))
                if "story_bible" in st.session_state: st.json(st.session_state.story_bible.model_dump())

    col_hp1, col_hp2 = st.columns([1, 1])
    with col_hp1: 
        draw_hp_bar(active_player, is_hero=True, label_prefix="TURNO DI:")
        
        if st.button("🎒 Inventario", key="hud_inv_btn", use_container_width=True):
            show_inventory_modal(active_player)
    with col_hp2:
        if st.session_state.world_state.active_enemies:
            draw_hp_bar(st.session_state.world_state.active_enemies[0], is_hero=False)

    if st.session_state.current_location_id in st.session_state.visited_locations:
        pop = st.session_state.visited_locations[st.session_state.current_location_id]
        with st.expander("📖 Lore del Luogo", expanded=False):
            st.markdown(f"*{pop.location_lore}*")
            if pop.rumors:
                st.markdown("**Dicerie sentite in giro:**")
                for r in pop.rumors: st.markdown(f"- *{r}*")

    if st.session_state.world_state.active_npc_name:
        st.markdown(f"<div style='display:flex; align-items:center; gap:8px; background:rgba(109,221,255,0.04); border:1px solid rgba(109,221,255,0.15); border-radius:8px; padding:10px 14px; margin:8px 0;'><span style='font-size:16px;'>💬</span><span style='font-family:\"Inter\",sans-serif; font-size:11px; color:#adaaab; text-transform:uppercase; letter-spacing:0.1em;'>Conversazione con</span><span style='font-family:\"Space Grotesk\",sans-serif; font-size:13px; font-weight:600; color:#6dddff;'>{st.session_state.world_state.active_npc_name}</span></div>", unsafe_allow_html=True)

    if st.session_state.last_narrative:
        st.markdown(f"<div class='narrative-box'><div class='narrative-gm-label'>Game Master</div><p class='narrative-text'>{st.session_state.last_narrative}</p></div>", unsafe_allow_html=True)

    # Controllo stato di salute globale o del singolo giocatore
    alive_players = [p for p in st.session_state.world_state.party if p.hp > 0]
    if not alive_players:
        st.markdown("<div style='text-align:center; padding:32px; background:rgba(255,113,108,0.05); border:1px solid rgba(255,113,108,0.2); border-radius:16px; margin:16px 0;'><div style='font-family:\"Space Grotesk\",sans-serif; font-size:24px; font-weight:700; color:#ff716c; letter-spacing:-0.02em; margin-bottom:8px;'>☠️ GAME OVER</div><div style='font-family:\"Newsreader\",serif; font-size:14px; color:#767576; font-style:italic;'>Il party è stato sconfitto. La storia si chiude senza di voi.</div></div>", unsafe_allow_html=True)
        col_r = st.columns([1, 2, 1])[1]
        with col_r:
            if st.button("🔄 Nuova Partita", use_container_width=True, type="primary"):
                st.session_state.clear()
                st.rerun()
        st.stop()
    elif active_player.hp <= 0:
        st.warning(f"☠️ {active_player.name} è a terra privo di sensi e non può agire in questo turno.")
        if st.button("Passa il turno", use_container_width=True):
            advance_turn()
            st.rerun()
        st.stop()

    if st.session_state.world_state.active_enemies:
        st.markdown("<div class='section-label'>⚔️ Modalità Combattimento</div>", unsafe_allow_html=True)
        enemy = st.session_state.world_state.active_enemies[0]
        with st.container(border=True):
            for log in st.session_state.world_state.combat_log[-3:]: st.markdown(f"<p style='font-family:Inter,sans-serif; font-size:11px; color:#adaaab; margin:2px 0;'>{log}</p>", unsafe_allow_html=True)
        if st.session_state.pending_combat_move is None:
            st.markdown(f"<div style='font-family:\"Inter\",sans-serif; font-size:9px; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:#adaaab; margin:12px 0 8px 0;'>Cosa fa {active_player.name} contro {enemy.name}?</div>", unsafe_allow_html=True)
            # Modificato: Prende le mosse in base alla classe del giocatore attivo
            moves = CLASS_MOVES.get(active_player.char_class, [{"name": "Attacco Base", "damage": "1d8"}])
            cols = st.columns(len(moves))
            for i, m in enumerate(moves):
                if cols[i].button(f"🗡️ {m['name']}", use_container_width=True):
                    st.session_state.pending_combat_move = m
                    save_game_state(st.session_state.session_id)
                    st.rerun()
        else:
            mossa = st.session_state.pending_combat_move
            st.info(f"{active_player.name} prepara: **{mossa['name']}**. Preparati a colpire!")
            combat_status_placeholder = st.empty()
            if combat_status_placeholder.button("🎲 TIRA IL DADO PER COLPIRE!", use_container_width=True, type="primary"):
                # Passa l'azione con l'indicazione di chi la fa, se il tuo engine lo supporta (altrimenti il calcolo dovrà sapere chi agisce)
                outcome = resolve_combat_round(mossa['name'], random.randint(1, 20)) 
                last_logs = "\n".join(st.session_state.world_state.combat_log[-2:])
                st.session_state.pending_combat_move = None
                
                if outcome == "vittoria":
                    combat_status_placeholder.markdown("""
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid rgba(72,72,73,0.15);">
                            <span style="font-family:'Inter',sans-serif; font-size:14px; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:var(--on-surface-variant);">Game Master</span>
                        </div>
                    """, unsafe_allow_html=True)
                    dm_prompt = f"""
                    Narra vittoria del party. Colpo finale di {active_player.name}. 
                    Log: {last_logs}
                    
                    REGOLE JSON TASSATIVE:
                    - Rispondi SOLO in JSON seguendo questo schema:
                    {{
                      "narration": "Testo epico della vittoria...",
                      "choices": ["Continua l'esplorazione", "Cerca tesori"],
                      "is_combat": false,
                      "allow_free_action": true,
                      "enemy_spawn": null
                    }}
                    """
                    scene = safe_agent_run(dm_agent, dm_prompt, schema=StoryScene, context_name="DM Combat End")
                    if scene: st.session_state.last_narrative = scene.narration
                    st.session_state.world_state.active_enemies = []
                elif outcome == "sconfitta" or not [p for p in st.session_state.world_state.party if p.hp > 0]:
                    # Caso gestito sopra (GAME OVER globale)
                    dm_prompt = f"""
                    Narra sconfitta letale per il party. 
                    Log: {last_logs}
                    
                    REGOLE JSON TASSATIVE:
                    - Rispondi SOLO in JSON seguendo questo schema:
                    {{
                      "narration": "Testo tragico della sconfitta...",
                      "choices": [],
                      "is_combat": false,
                      "allow_free_action": false,
                      "enemy_spawn": null
                    }}
                    """
                    scene = safe_agent_run(dm_agent, dm_prompt, schema=StoryScene, context_name="DM Combat Death")
                    if scene: st.session_state.last_narrative = scene.narration
                    st.session_state.world_state.active_enemies = []
                else: 
                    st.session_state.last_narrative = f"### Resoconto scontro:\n{last_logs}"
                
                # Modificato: A fine turno di combattimento, passa la palla al prossimo
                advance_turn()
                save_game_state(st.session_state.session_id)
                st.rerun()
            if st.button("❌ Cambia mossa", type="secondary"):
                st.session_state.pending_combat_move = None
                save_game_state(st.session_state.session_id)
                st.rerun()
    else:
        # ==========================================
        # GESTIONE DELLA RICHIESTA DI TIRO (SKILL CHECK)
        # ==========================================
        if st.session_state.get("pending_skill_check"):
            check = st.session_state.pending_skill_check
            
            st.markdown(f"""
            <div style='background:rgba(251, 191, 36, 0.1); border:1px solid #fbbf24; border-radius:12px; padding:16px; margin-bottom:16px;'>
                <h3 style='color:#fbbf24; margin-top:0;'>🎲 Il Game Master richiede una Prova!</h3>
                <p style='color:var(--on-surface);'><strong>Azione:</strong> {check['motivo']}</p>
                <p style='color:var(--on-surface);'><strong>Richiesta:</strong> Prova di <strong>{check['caratteristica']}</strong> (CD {check['cd']})</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 1. Troviamo il modificatore corretto in base alla caratteristica richiesta dall'IA
            stat_name_en = {
                "Forza": "strength", "Destrezza": "dexterity", "Costituzione": "constitution",
                "Intelligenza": "intelligence", "Saggezza": "wisdom", "Carisma": "charisma"
            }.get(check['caratteristica'], "strength") # fallback a forza se l'IA sbaglia nome
            
            valore_stat = getattr(active_player, stat_name_en, 10)
            modificatore = (valore_stat - 10) // 2
            
            segno = "+" if modificatore >= 0 else ""
            
            if st.button(f"Tira 1d20 {segno}{modificatore} ({check['caratteristica']})", use_container_width=True, type="primary"):
                dado = random.randint(1, 20)
                totale = dado + modificatore
                esito = "SUCCESSO" if totale >= check['cd'] else "FALLIMENTO"
                
                # Prepariamo l'input formattato da passare al DM
                risultato_testo = f"{check['azione_originale']} -> [RISULTATO DADO: {totale} contro CD {check['cd']} - {esito}]"
                
                # Puliamo lo stato della prova
                st.session_state.pending_skill_check = None
                
                # Rilanciamo process_turn AGGIRANDO il controllo regole, passando direttamente alla narrazione
                with st.spinner(f"Dado tirato: {dado}{segno}{modificatore} = {totale}. Il DM sta descrivendo l'esito..."):
                    scene = process_turn(risultato_testo, bypass_rules=True)
                    if scene:
                        st.session_state.current_scene = scene
                        st.session_state.last_narrative = scene.narration
                        trigger_ares_if_needed(scene)
                        
                    st.session_state.memory.add_event(text=f"Turno {st.session_state.world_state.turn_number} ({active_player.name}): Prova di {check['caratteristica']} -> {esito}. Narrazione: {st.session_state.last_narrative}", turn=st.session_state.world_state.turn_number, event_type="skill_check")
                    st.session_state.world_state.turn_number += 1
                    advance_turn()
                    save_game_state(st.session_state.session_id)
                    st.rerun()
                    
            if st.button("❌ Rinuncia e cambia azione", use_container_width=True):
                st.session_state.pending_skill_check = None
                st.rerun()
                
            st.stop() # Blocca il resto dell'interfaccia finché non tira il dado
        # ==========================================

        else:
            section_label_placeholder = st.empty()
            section_label_placeholder.markdown(f"<div class='section-label'>🧭 Cosa fa {active_player.name}?</div>", unsafe_allow_html=True)
            azione_scelta = None 
            scene = st.session_state.current_scene
            
            # --- Aggiunto il pulsante per passare il turno ---
            if st.button("⏩ Salta il turno", key="skip_turn_btn"):
                 advance_turn()
                 st.rerun()
    
            if scene and scene.choices:
                for option in scene.choices:
                    if st.button(f" {option}", use_container_width=True, key=f"btn_{option}"): azione_scelta = option
            if st.session_state.get("world_map"):
                cur_loc = next((l for l in st.session_state.world_map.locations if l.id_name == st.session_state.world_state.current_location), None)
                if cur_loc:
                    available_destinations = [l for l in st.session_state.world_map.locations if l.id_name in cur_loc.connected_to and l.id_name in st.session_state.world_state.known_locations]
                    if available_destinations:
                        st.markdown("### 🗺️ Spostamento Rapido")
                        cols = st.columns(len(available_destinations))
                        for i, dest in enumerate(available_destinations):
                            if cols[i].button(f"🧭 {dest.name}", use_container_width=True): azione_scelta = f"__MOVE_{dest.id_name}"
            if scene is None or scene.allow_free_action:
                if "azione_scelta_per_turn" not in st.session_state:
                    st.session_state.azione_scelta_per_turn = None
    
                def on_input_change():
                    if st.session_state.free_action_input:
                        st.session_state.azione_scelta_per_turn = st.session_state.free_action_input
                        st.session_state.free_action_input = "" 
    
                with st.container():
                    st.markdown('<div class="pill-input-marker" style="display:none"></div>', unsafe_allow_html=True)
                    col_txt, col_send = st.columns([20, 1], gap="small", vertical_alignment="center")
                    with col_txt:
                        # Modificato: Personalizza il placeholder con il nome
                        placeholder_testo = f"Scrivi cosa fa {active_player.name}..."
                        # Nel turno 1 incoraggiamo i giocatori a descrivere i propri personaggi
                        if st.session_state.world_state.turn_number == 1:
                            placeholder_testo = f"Descrivi l'aspetto di {active_player.name} e come reagisce alla scena..."
                            
                        st.text_input("Azione Libera", placeholder=placeholder_testo, label_visibility="collapsed", key="free_action_input", on_change=on_input_change, autocomplete="off")
                    with col_send:
                        if st.button("Invia", icon=":material/arrow_upward:", key="send_btn"):
                            if st.session_state.free_action_input:
                                st.session_state.azione_scelta_per_turn = st.session_state.free_action_input
                                st.session_state.free_action_input = ""
                
                if st.session_state.azione_scelta_per_turn:
                    azione_scelta = st.session_state.azione_scelta_per_turn
                    st.session_state.azione_scelta_per_turn = None 
            else: st.warning("⏳ Devi scegliere una delle opzioni qui sopra.")
            
            st.markdown('<div class="content-spacer"></div>', unsafe_allow_html=True)
            
            user_input = azione_scelta
            if user_input:
                section_label_placeholder.markdown("""
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid rgba(72,72,73,0.15);">
                        <span style="font-family:'Inter',sans-serif; font-size:14px; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:var(--on-surface-variant);">Game Master</span>
                    </div>
                """, unsafe_allow_html=True)
                if user_input.lower().startswith("congedarsi"): st.session_state.world_state.active_npc_name = None
                elif user_input.lower().startswith("parlare con "): st.session_state.world_state.active_npc_name = user_input[len("parlare con "):].strip()
                
                # Formatta l'azione includendo il nome del personaggio così l'AI capisce CHI la sta facendo
                action_text_with_name = f"[{active_player.name}]: {user_input}"
                
                scene = process_turn(action_text_with_name)
                
                if scene: st.session_state.current_scene = scene; st.session_state.last_narrative = scene.narration; trigger_ares_if_needed(st.session_state.current_scene)
                turn_num = st.session_state.world_state.turn_number
                st.session_state.memory.add_event(text=f"Turno {turn_num} ({active_player.name}): {user_input}. Narrazione: {st.session_state.last_narrative}", turn=turn_num, event_type="exploration")
                
                st.session_state.world_state.turn_number += 1
                
                # --- Modificato: Passiamo il turno al giocatore successivo prima di ricaricare ---
                advance_turn()
                save_game_state(st.session_state.session_id)
                st.rerun()

    if 'session_id' in st.session_state and st.session_state.get('page') == 'game':
        save_game_state(st.session_state.session_id)