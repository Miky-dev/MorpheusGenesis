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
    trigger_ares_if_needed
)
from agents.dm_agent import dm_agent
from agents.spawner_agent import spawner_agent
from agents.map_agent import map_generator_agent
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
    </style>
    """

def draw_hp_bar(current_hp, max_hp, name, is_hero=True):
    pct = max(0, current_hp / max_hp)
    fill_class = "hp-bar-fill-green" if pct > 0.6 else "hp-bar-fill-yellow" if pct > 0.3 else "hp-bar-fill-red"
    card_class = "hud-card" if is_hero else "hud-card-inactive"
    name_class = "hud-name" if is_hero else "hud-name-inactive"
    st.markdown(f"""
        <div class="{card_class}">
            <div class="{name_class}">{name.upper()}</div>
            <div class="hp-bar-track"><div class="{fill_class}" style="width:{pct*100:.0f}%"></div></div>
            <p class="hp-label">Salute: {current_hp} / {max_hp} HP</p>
        </div>
    """, unsafe_allow_html=True)

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
                # Formattazione Nome: Durabilità (armi/armature) vs Quantità (altro)
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
                
                # Bottone per usare i consumabili
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
            if st.button("⚔️ INIZIA L'AVVENTURA", use_container_width=True, type="primary"):
                st.session_state.cinematic_seen = True
                save_game_state(st.session_state.session_id)
                st.rerun()
        st.stop()

    title_text = bible.title if bible else "Project Morpheus"
    st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:0.5rem;">
            <div style="font-family:'Space Grotesk',sans-serif; font-size:9px; font-weight:700; letter-spacing:0.25em; text-transform:uppercase; color:#6dddff;">Morpheus Genesis</div>
            <div style="width:4px; height:4px; border-radius:50%; background:#484849;"></div>
            <div style="font-family:'Inter',sans-serif; font-size:9px; letter-spacing:0.15em; text-transform:uppercase; color:#767576;">Turn {st.session_state.world_state.turn_number}</div>
        </div>
        <h1 style="font-family:'Space Grotesk',sans-serif; font-size:1.4rem; font-weight:700; letter-spacing:-0.02em; color:#6dddff; text-transform:uppercase; margin:0 0 1rem 0; padding-bottom:0.5rem; border-bottom:1px solid rgba(72,72,73,0.15);">{title_text}</h1>
    """, unsafe_allow_html=True)

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
        draw_hp_bar(st.session_state.world_state.party[0].hp, st.session_state.world_state.party[0].max_hp, st.session_state.world_state.party[0].name, is_hero=True)
        if st.button("🎒 Inventario", key="hud_inv_btn", use_container_width=True):
            show_inventory_modal(st.session_state.world_state.party[0])
    with col_hp2:
        if st.session_state.world_state.active_enemies:
            draw_hp_bar(st.session_state.world_state.active_enemies[0].hp, st.session_state.world_state.active_enemies[0].max_hp, st.session_state.world_state.active_enemies[0].name, is_hero=False)
    st.divider()

    if not st.session_state.last_narrative and st.session_state.current_scene is None:
        ensure_location_population()
        world_map = st.session_state.world_map
        luogo_attuale = next(l for l in world_map.locations if l.id_name == st.session_state.current_location_id)
        pop = st.session_state.visited_locations[luogo_attuale.id_name]
        
        if luogo_attuale.difficulty_level == 0:
            st.success(f"📍 Sei a {luogo_attuale.name}. È un luogo sicuro.")
            with st.spinner("Apollo sta preparando l'accoglienza..."):
                quest_hint = f"\nHINT NARRATIVO: Un misterioso {bible.herald_npc_name} potrebbe avere informazioni." if bible else ""
                dm_prompt = f"GIOCATORE: {st.session_state.world_state.party[0].name}.\nLOCATION: {luogo_attuale.name}.\nNPC: {[n.name for n in pop.npcs]}.\n{quest_hint}\nZONA SICURA. Narra arrivo."
                scene = safe_agent_run(dm_agent, dm_prompt, schema=StoryScene, context_name=f"DM scene safe mode ({luogo_attuale.name})")
                if scene: st.session_state.current_scene = scene; st.session_state.last_narrative = scene.narration
        else:
            st.error(f"⚠️ Attenzione: {luogo_attuale.name} (Livello di Pericolo {luogo_attuale.difficulty_level})")
            if not st.session_state.world_state.active_enemies:
                with st.spinner("Ares sta forgiando una minaccia..."):
                    enemy_payload = safe_agent_run(spawner_agent, f"Genera nemico liv {luogo_attuale.difficulty_level}", schema=None, context_name="Ares spawn")
                    if isinstance(enemy_payload, str): enemy_payload = parse_json_response(enemy_payload, "Ares")
                    if enemy_payload:
                        st.session_state.world_state.active_enemies = [Enemy(name=enemy_payload.get("name", "Nemico"), hp=enemy_payload["stats"]["hp"], max_hp=enemy_payload["stats"]["hp"], ac=enemy_payload["stats"]["ca"])]
            nemico = st.session_state.world_state.active_enemies[0] if st.session_state.world_state.active_enemies else None
            with st.spinner("Apollo descrive il pericolo..."):
                dm_prompt = f"GIOCATORE: {st.session_state.world_state.party[0].name}.\nNEMICO: {nemico.name if nemico else 'Sconosciuto'}. Narra apparizione."
                scene = safe_agent_run(dm_agent, dm_prompt, schema=StoryScene, context_name="DM combat scene")
                if scene: st.session_state.current_scene = scene; st.session_state.last_narrative = scene.narration
        save_game_state(st.session_state.session_id)
        st.rerun()

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

    if st.session_state.world_state.party[0].hp <= 0:
        st.markdown("<div style='text-align:center; padding:32px; background:rgba(255,113,108,0.05); border:1px solid rgba(255,113,108,0.2); border-radius:16px; margin:16px 0;'><div style='font-family:\"Space Grotesk\",sans-serif; font-size:24px; font-weight:700; color:#ff716c; letter-spacing:-0.02em; margin-bottom:8px;'>☠️ GAME OVER</div><div style='font-family:\"Newsreader\",serif; font-size:14px; color:#767576; font-style:italic;'>La storia si chiude senza di te. Rinasci per tentare una nuova sorte.</div></div>", unsafe_allow_html=True)
        col_r = st.columns([1, 2, 1])[1]
        with col_r:
            if st.button("🔄 Nuova Partita", use_container_width=True, type="primary"):
                st.session_state.clear()
                st.rerun()
        st.stop()

    if st.session_state.world_state.active_enemies:
        st.markdown("<div class='section-label'>⚔️ Modalità Combattimento</div>", unsafe_allow_html=True)
        hero = st.session_state.world_state.party[0]
        enemy = st.session_state.world_state.active_enemies[0]
        with st.container(border=True):
            for log in st.session_state.world_state.combat_log[-3:]: st.markdown(f"<p style='font-family:Inter,sans-serif; font-size:11px; color:#adaaab; margin:2px 0;'>{log}</p>", unsafe_allow_html=True)
        if st.session_state.pending_combat_move is None:
            st.markdown(f"<div style='font-family:\"Inter\",sans-serif; font-size:9px; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:#adaaab; margin:12px 0 8px 0;'>Scegli la tua mossa contro {enemy.name}</div>", unsafe_allow_html=True)
            moves = CLASS_MOVES.get(hero.char_class, [{"name": "Attacco Base", "damage": "1d8"}])
            cols = st.columns(len(moves))
            for i, m in enumerate(moves):
                if cols[i].button(f"🗡️ {m['name']}", use_container_width=True):
                    st.session_state.pending_combat_move = m
                    save_game_state(st.session_state.session_id)
                    st.rerun()
        else:
            mossa = st.session_state.pending_combat_move
            st.info(f"Hai scelto: **{mossa['name']}**. Preparati a colpire!")
            combat_status_placeholder = st.empty()
            if combat_status_placeholder.button("🎲 TIRA IL DADO PER COLPIRE!", use_container_width=True, type="primary"):
                outcome = resolve_combat_round(mossa['name'], random.randint(1, 20))
                last_logs = "\n".join(st.session_state.world_state.combat_log[-2:])
                st.session_state.pending_combat_move = None
                if outcome == "vittoria":
                    combat_status_placeholder.markdown("""
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid rgba(72,72,73,0.15);">
                            <span style="font-family:'Inter',sans-serif; font-size:14px; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:var(--on-surface-variant);">Game Master</span>
                            <div class="dm-dot"></div>
                            <div class="dm-dot"></div>
                            <div class="dm-dot"></div>
                            <div class="dm-dot"></div>
                        </div>
                    """, unsafe_allow_html=True)
                    scene = safe_agent_run(dm_agent, f"Narra vittoria. Log: {last_logs}", schema=StoryScene, context_name="DM Combat End")
                    if scene: st.session_state.last_narrative = scene.narration
                    st.session_state.world_state.active_enemies = []
                elif outcome == "sconfitta" or st.session_state.world_state.party[0].hp <= 0:
                    combat_status_placeholder.markdown("""
                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid rgba(72,72,73,0.15);">
                            <span style="font-family:'Inter',sans-serif; font-size:14px; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:var(--on-surface-variant);">Game Master</span>
                            <div class="dm-dot"></div>
                            <div class="dm-dot"></div>
                            <div class="dm-dot"></div>
                            <div class="dm-dot"></div>
                        </div>
                    """, unsafe_allow_html=True)
                    scene = safe_agent_run(dm_agent, f"Narra sconfitta. Log: {last_logs}", schema=StoryScene, context_name="DM Combat Death")
                    if scene: st.session_state.last_narrative = scene.narration
                    st.session_state.world_state.active_enemies = []
                else: st.session_state.last_narrative = f"### Resoconto scontro:\n{last_logs}"
                save_game_state(st.session_state.session_id)
                st.rerun()
            if st.button("❌ Cambia mossa", type="secondary"):
                st.session_state.pending_combat_move = None
                save_game_state(st.session_state.session_id)
                st.rerun()
    else:
        section_label_placeholder = st.empty()
        section_label_placeholder.markdown("<div class='section-label'>🧭 Cosa fai?</div>", unsafe_allow_html=True)
        azione_scelta = None 
        scene = st.session_state.current_scene
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
                    st.session_state.free_action_input = "" # Svuota l'input

            with st.container():
                st.markdown('<div class="pill-input-marker" style="display:none"></div>', unsafe_allow_html=True)
                col_txt, col_send = st.columns([20, 1], gap="small", vertical_alignment="center")
                with col_txt:
                    st.text_input("Azione Libera", placeholder="Oppure fai di testa tua...", label_visibility="collapsed", key="free_action_input", on_change=on_input_change, autocomplete="off")
                with col_send:
                    if st.button("Invia", icon=":material/arrow_upward:", key="send_btn"):
                        if st.session_state.free_action_input:
                            st.session_state.azione_scelta_per_turn = st.session_state.free_action_input
                            st.session_state.free_action_input = ""
            
            if st.session_state.azione_scelta_per_turn:
                azione_scelta = st.session_state.azione_scelta_per_turn
                st.session_state.azione_scelta_per_turn = None # Reset
        else: st.warning("⏳ Devi scegliere una delle opzioni qui sopra.")
        
        st.markdown('<div class="content-spacer"></div>', unsafe_allow_html=True)
        
        user_input = azione_scelta
        if user_input:
            section_label_placeholder.markdown("""
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid rgba(72,72,73,0.15);">
                    <span style="font-family:'Inter',sans-serif; font-size:14px; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:var(--on-surface-variant);">Game Master</span>
                    <div class="dm-dot"></div>
                    <div class="dm-dot"></div>
                    <div class="dm-dot"></div>
                    <div class="dm-dot"></div>
                </div>
            """, unsafe_allow_html=True)
            if user_input.lower().startswith("congedarsi"): st.session_state.world_state.active_npc_name = None
            elif user_input.lower().startswith("parlare con "): st.session_state.world_state.active_npc_name = user_input[len("parlare con "):].strip()
            scene = process_turn(user_input)
            if scene: st.session_state.current_scene = scene; st.session_state.last_narrative = scene.narration; trigger_ares_if_needed(st.session_state.current_scene)
            turn_num = st.session_state.world_state.turn_number
            st.session_state.memory.add_event(text=f"Turno {turn_num}: {user_input}. Narrazione: {st.session_state.last_narrative}", turn=turn_num, event_type="exploration")
            st.session_state.world_state.turn_number += 1
            save_game_state(st.session_state.session_id)
            st.rerun()

    if 'session_id' in st.session_state and st.session_state.get('page') == 'game':
        save_game_state(st.session_state.session_id)
