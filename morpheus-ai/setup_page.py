import streamlit as st
import time
import os
import base64
from persistence import save_game_state

@st.cache_data
def get_cached_base64_image(image_path):
    """Legge l'immagine e la converte in base64 solo la prima volta che viene richiesta."""
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
            return f"url('data:image/png;base64,{encoded}')"
    return image_path

# Classi e icone disponibili
CLASSI = ["Guerriero", "Ladro", "Mago"]
CLASSE_ICONS = {"Guerriero": "shield", "Ladro": "stealth", "Mago": "auto_fix_high"}
CLASS_COLORS = {"Guerriero": "#e07b54", "Ladro": "#81d6be", "Mago": "#a78bfa"}
MAX_PLAYERS = 3

def init_session_state():
    if 'selected_theme' not in st.session_state:
        st.session_state.selected_theme = "Cyberpunk"
    if 'campaign_name' not in st.session_state:
        st.session_state.campaign_name = ""
    if 'difficulty' not in st.session_state:
        st.session_state.difficulty = "Normale"
    if 'narrative_style' not in st.session_state:
        st.session_state.narrative_style = "Oscuro"
    if 'is_loading_game' not in st.session_state:
        st.session_state.is_loading_game = False
    # Lista giocatori: ogni elemento è {"name": str, "class": str}
    if 'party_slots' not in st.session_state:
        st.session_state.party_slots = [{"name": "", "class": "Guerriero"}]

def render_setup_page():
    init_session_state()

    # --- 1. GLOBAL UI TWEAKS (CSS INJECTION) ---
    st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet"/>
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
        
        <style>
        /* Base Reset & Fonts */
        .stApp {
            background-color: #131313;
            color: #e5e2e1;
            font-family: 'Inter', sans-serif;
        }
        
        h1, h2, h3, h4, h5, h6 { font-family: 'Manrope', sans-serif !important; }
        
        .block-container {
            padding-top: 5rem !important;
            max-width: 90% !important;
        }

        /* Abstract Accent */
        .abstract-bg {
            position: absolute;
            top: 0; right: 0;
            width: 50vw; height: 100vh;
            background: linear-gradient(to bottom left, #1c1b1b, transparent);
            opacity: 0.5;
            border-bottom-left-radius: 100%;
            pointer-events: none;
            z-index: 0;
        }

        /* Typography */
        .header-subtitle { color: #81d6be; letter-spacing: 0.1em; font-size: 0.875rem; text-transform: uppercase; font-weight: 500;}
        .header-title { font-family: 'Manrope', sans-serif; font-size: clamp(2.5rem, 4vw, 3.75rem); font-weight: 700; line-height: 1.1; margin-bottom: 1rem;}
        .header-desc { color: #bec9c4; font-size: 1.125rem; max-width: 600px; margin-bottom: 2rem;}
        
        .section-title {
            display: flex; align-items: center; gap: 0.75rem;
            font-size: 1.5rem; font-weight: 600; margin-bottom: 1rem;
            font-family: 'Manrope', sans-serif;
        }
        .section-title span.material-symbols-outlined { color: #81d6be; }

        /* Inputs */
        div[data-baseweb="input"] {
            background-color: #2a2a2a;
            border-radius: 0.75rem;
            border: 1px solid transparent;
        }
        div[data-baseweb="input"]:focus-within { border-color: rgba(129,214,190, 0.4); }
        div[data-baseweb="input"] > input { color: #e5e2e1; padding: 0.75rem 1rem;}
        
        /* Selectbox */
        div[data-baseweb="select"] {
            background-color: #2a2a2a;
            border-radius: 0.75rem;
            border: 1px solid transparent;
        }

        /* Segmented Control */
        div[data-testid="stButtonGroup"] button:focus,
        div[data-testid="stButtonGroup"] button:focus-visible {
            box-shadow: 0 0 0 2px rgba(129, 214, 190, 0.4) !important;
            outline: none !important;
        }
        div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] {
            background: linear-gradient(135deg, #81d6be, #227e69) !important;
            color: #00382c !important;
            border-color: #81d6be !important;
            font-weight: 700 !important;
        }
        div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] * {
            color: #00382c !important;
        }
        div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"]:hover {
            border-color: #81d6be !important;
            color: #81d6be !important;
            background-color: rgba(129, 214, 190, 0.1) !important;
        }
        div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"]:hover * {
            color: #81d6be !important;
        }

        /* Player Cards */
        .player-card-wrapper {
            background-color: #1c1b1b;
            padding: 1.25rem 1.25rem 0.75rem 1.25rem;
            border-radius: 0.75rem;
            margin-bottom: 0.75rem;
            border: 1px solid rgba(136,147,142,0.15);
            transition: border-color 0.3s;
        }
        .player-card-wrapper:hover { border-color: rgba(136,147,142,0.3); }

        .player-badge {
            display: inline-flex; align-items: center; gap: 6px;
            font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em;
            text-transform: uppercase; color: #bec9c4;
            margin-bottom: 0.75rem;
        }
        .player-badge .material-symbols-outlined { font-size: 1rem; }

        /* Add Player button */
        div[data-testid="stVerticalBlock"]:has(> div.element-container div.add-player-marker) button {
            background-color: transparent !important;
            border: 1px dashed rgba(129, 214, 190, 0.35) !important;
            color: #81d6be !important;
            border-radius: 0.75rem !important;
            height: 48px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stVerticalBlock"]:has(> div.element-container div.add-player-marker) button:hover {
            background-color: rgba(129, 214, 190, 0.08) !important;
            border-color: #81d6be !important;
            transform: translateY(-1px) !important;
        }

        /* Start Button */
        div[data-testid="stVerticalBlock"]:has(> div.element-container div.start-button-marker) button {
            background: linear-gradient(135deg, #81d6be, #227e69) !important;
            color: #00382c !important;
            font-family: 'Manrope', sans-serif !important;
            font-size: 1rem !important;
            font-weight: 700 !important;
            height: 52px !important;
            width: 100% !important;
            border-radius: 0.75rem !important;
            box-shadow: 0 12px 24px rgba(34, 126, 105, 0.25) !important;
            border: none !important;
            transition: all 0.3s ease !important;
            letter-spacing: 0.05em !important;
        }
        div[data-testid="stVerticalBlock"]:has(> div.element-container div.start-button-marker) button:hover {
            transform: translateY(-3px) scale(1.01) !important;
            box-shadow: 0 0 20px rgba(129, 214, 190, 0.5), 0 16px 32px rgba(34, 126, 105, 0.4) !important;
            filter: brightness(1.1) !important;
        }

        /* Remove player button — small red icon button */
        button[data-testid="stBaseButton-secondary"][kind="secondary"] {
            padding: 2px 8px !important;
        }
        
        <div class="abstract-bg"></div>
    
    """, unsafe_allow_html=True)

    # --- 2. LAYOUT SPLIT ---
    col_left, col_border, col_right = st.columns([6, 0.5, 4.5])

    with col_left:
        # HEADER
        st.markdown("""
            <div class="header-subtitle">Morpheus Genesis</div>
            <div class="header-title">Sessione Zero &mdash;<br>Raduna il Party</div>
            <div class="header-desc">Definisci il mondo, il tono della storia e gli avventurieri che affronteranno insieme questa campagna.</div>
        """, unsafe_allow_html=True)
        
        # CAMPAIGN SETTINGS
        st.markdown("""
            <div class="section-title">
                <span class="material-symbols-outlined">settings_applications</span>
                <span>Impostazioni Campagna</span>
            </div>
        """, unsafe_allow_html=True)
        
        @st.fragment
        def render_campaign_settings():
            setting_cols = st.columns([1, 1])
            with setting_cols[0]:
                st.markdown("<label style='font-size: 0.875rem; color: #bec9c4; font-weight: 600; margin-bottom: 0.5rem; display: block;'>Nome della Campagna</label>", unsafe_allow_html=True)
                st.text_input("NOME", key="campaign_name", placeholder="es. La Corona di Ossidiana", label_visibility="collapsed", disabled=st.session_state.is_loading_game, autocomplete="off")
            with setting_cols[1]:
                st.markdown("<label style='font-size: 0.875rem; color: #bec9c4; font-weight: 600; margin-bottom: 0.5rem; display: block;'>Difficoltà</label>", unsafe_allow_html=True)
                diff_options = ["Facile", "Normale", "Difficile", "Epica"]
                st.segmented_control(
                    "Difficoltà", 
                    options=diff_options, 
                    key="difficulty",
                    label_visibility="collapsed", 
                    disabled=st.session_state.is_loading_game,
                    selection_mode="single"
                )
        
        render_campaign_settings()

        st.markdown("<br>", unsafe_allow_html=True)

        # NARRATIVE THEME & MOOD
        st.markdown("""
            <div class="section-title" style="margin-top: 1rem;">
                <span class="material-symbols-outlined">auto_stories</span>
                <span>Tema Narrativo</span>
            </div>
        """, unsafe_allow_html=True)
        
        @st.fragment
        def render_mood_selector():
            mood_cols = st.columns([1, 1])
            with mood_cols[0]:
                st.markdown("<label style='font-size: 0.875rem; color: #bec9c4; font-weight: 600; margin-bottom: 0.5rem; display: block;'>Mood Narrativo</label>", unsafe_allow_html=True)
                moods = ["Oscuro", "Eroico", "Divertente", "Misterioso", "Tragico"]
                st.selectbox(
                    "Mood Narrativo", 
                    moods, 
                    index=moods.index(st.session_state.narrative_style) if st.session_state.narrative_style in moods else 0, 
                    key="narrative_style",
                    label_visibility="collapsed", 
                    disabled=st.session_state.is_loading_game
                )
        
        render_mood_selector()
        
        themes = {
            "Fantasy": {"icon": "swords", "bg": "assets/fantasy.png"},
            "Cyberpunk": {"icon": "memory", "bg": "assets/cyberpunk.png"},
            "Fantascienza": {"icon": "rocket_launch", "bg": "assets/scifi.png"},
            "Horror": {"icon": "skull", "bg": "assets/horror.png"},
            "Post-Apocalittico": {"icon": "dangerous", "bg": "assets/postapoc.png"},
            "Pirati": {"icon": "sailing", "bg": "assets/pirates.png"},
            "Western": {"icon": "grade", "bg": "assets/western.png"},
            "Antico Egitto": {"icon": "landscape", "bg": "assets/egypt.png"}
        }

        # CSS immagini base64 — iniettato una sola volta fuori dal fragment
        css_bg = "<style>\n"
        for i, (t_name, t_data) in enumerate(themes.items()):
            bg_css = t_data['bg']
            if not bg_css.startswith("url("):
                bg_css = get_cached_base64_image(bg_css)

            css_bg += f"""
                div.element-container:has(.theme-{i}) + div.element-container div[data-testid='stButton'] button {{
                    background-image: linear-gradient(rgba(42, 42, 42, 0.4), rgba(42, 42, 42, 0.4)), {bg_css} !important;
                    background-size: cover !important; background-position: center !important;
                    height: 140px !important; width: 100% !important; border-radius: 0.75rem !important;
                    border: 1px solid rgba(136, 147, 142, 0.2) !important;
                    border-bottom: 2px solid rgba(255, 255, 255, 0.2) !important;
                    color: transparent !important;
                    position: relative; overflow: hidden;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.4) !important;
                    display: flex !important; flex-direction: column !important;
                    align-items: center !important; justify-content: center !important;
                    transition: border-color 0.15s ease, filter 0.15s ease;
                }}
                div.element-container:has(.theme-{i}) + div.element-container div[data-testid='stButton'] button div {{
                    display: none !important;
                }}
                div.element-container:has(.theme-{i}) + div.element-container div[data-testid='stButton'] button::before {{
                    content: "{t_data['icon']}";
                    font-family: 'Material Symbols Outlined';
                    font-size: 2.2rem; color: #bec9c4;
                    margin-bottom: 8px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.8));
                    transition: color 0.15s ease;
                }}
                div.element-container:has(.theme-{i}) + div.element-container div[data-testid='stButton'] button::after {{
                    content: "{t_name}";
                    font-family: 'Inter', sans-serif; font-weight: 500; font-size: 0.9rem;
                    color: #bec9c4; text-shadow: 0 2px 4px rgba(0,0,0,0.8);
                    transition: color 0.15s ease;
                }}
                div.element-container:has(.theme-{i}) + div.element-container div[data-testid='stButton'] button:hover {{
                    border: 1px solid rgba(255, 255, 255, 0.2) !important;
                    filter: brightness(1.2);
                }}
                div.element-container:has(.theme-{i}.active-theme) + div.element-container div[data-testid='stButton'] button {{
                    background-image: linear-gradient(rgba(129, 214, 190, 0.1), rgba(129, 214, 190, 0.1)), {bg_css} !important;
                    border: 1px solid rgba(129, 214, 190, 0.4) !important;
                    border-bottom: 2px solid #81d6be !important;
                }}
                div.element-container:has(.theme-{i}.active-theme) + div.element-container div[data-testid='stButton'] button::before,
                div.element-container:has(.theme-{i}.active-theme) + div.element-container div[data-testid='stButton'] button::after {{
                    color: #81d6be !important;
                }}
                div.element-container:has(.theme-{i}.active-theme) + div.element-container div[data-testid='stButton'] button:hover {{
                    border: 1px solid #81d6be !important;
                }}
            """
        css_bg += "</style>"
        st.markdown(css_bg, unsafe_allow_html=True)

        @st.fragment
        def render_theme_selector():
            def update_theme(t_name):
                st.session_state.selected_theme = t_name

            theme_names = list(themes.keys())
            for row in range(0, len(theme_names), 4):
                cols = st.columns(4)
                for i in range(4):
                    if row + i < len(theme_names):
                        t_name = theme_names[row + i]
                        with cols[i]:
                            active_class = " active-theme" if t_name == st.session_state.selected_theme else ""
                            st.markdown(
                                f'<span class="theme-{row+i}{active_class}" style="display:none"></span>',
                                unsafe_allow_html=True
                            )
                            st.button(
                                " ",
                                key=f"tbtn_{t_name}",
                                use_container_width=True,
                                disabled=st.session_state.is_loading_game,
                                on_click=update_theme,
                                args=(t_name,)
                            )

        render_theme_selector()

    # ---------------------------------------------------------------
    # PANNELLO DESTRO: Party Builder Multi-Giocatore
    # ---------------------------------------------------------------
    with col_right:

        # --- Header pannello ---
        st.markdown("""
            <div class="section-title" style="margin-bottom: 1.25rem;">
                <span class="material-symbols-outlined">group</span>
                <span>Il Party</span>
            </div>
        """, unsafe_allow_html=True)

        # --- Player card CSS ---
        st.markdown("""
        <style>
        div[data-testid="stVerticalBlock"]:has(> div.element-container div.player-card-marker) {
            background-color: #1c1b1b;
            padding: 1rem 1.25rem 0.5rem 1.25rem;
            border-radius: 0.75rem;
            margin-bottom: 0.75rem;
            border: 1px solid rgba(136,147,142,0.15);
            transition: border-color 0.3s;
        }
        div[data-testid="stVerticalBlock"]:has(> div.element-container div.player-card-marker):hover { 
            border-color: rgba(136,147,142,0.3); 
        }
        </style>
        """, unsafe_allow_html=True)

        # --- Render card per ogni slot giocatore ---
        for idx in range(len(st.session_state.party_slots)):
            slot = st.session_state.party_slots[idx]
            classe_corrente = slot.get("class", "Guerriero")
            colore = CLASS_COLORS.get(classe_corrente, "#bec9c4")
            icona = CLASSE_ICONS.get(classe_corrente, "person")

            with st.container():
                st.markdown(f'<div class="player-card-marker" style="display:none"></div>', unsafe_allow_html=True)

                # Badge con numero e classe attuale
                header_col, remove_col = st.columns([5, 1])
                with header_col:
                    st.markdown(
                        f"""<div class="player-badge">
                            <span class="material-symbols-outlined" style="color:{colore}">{icona}</span>
                            <span style="color:{colore}">Avventuriero {idx + 1}</span>
                        </div>""",
                        unsafe_allow_html=True
                    )
                with remove_col:
                    # Mostra il pulsante rimuovi solo se ci sono più di 1 giocatori
                    if len(st.session_state.party_slots) > 1 and not st.session_state.is_loading_game:
                        if st.button("✕", key=f"remove_player_{idx}", help="Rimuovi questo avventuriero"):
                            st.session_state.party_slots.pop(idx)
                            st.rerun()

                # Nome personaggio
                st.markdown("<label style='font-size: 0.8rem; color: #9ca3af; margin-bottom: 0.25rem; display:block;'>Nome del Personaggio</label>", unsafe_allow_html=True)
                new_name = st.text_input(
                    f"nome_p{idx}",
                    value=slot.get("name", ""),
                    placeholder=f"es. {'Valerius' if idx == 0 else 'Lyra' if idx == 1 else 'Dorn'}",
                    label_visibility="collapsed",
                    key=f"name_input_{idx}",
                    disabled=st.session_state.is_loading_game,
                    autocomplete="name"
                )
                st.session_state.party_slots[idx]["name"] = new_name

                # Classe
                st.markdown("<label style='font-size: 0.8rem; color: #9ca3af; margin-top: 0.4rem; margin-bottom: 0.25rem; display:block;'>Classe / Archetipo</label>", unsafe_allow_html=True)
                new_class = st.selectbox(
                    f"classe_p{idx}",
                    CLASSI,
                    index=CLASSI.index(classe_corrente) if classe_corrente in CLASSI else 0,
                    label_visibility="collapsed",
                    key=f"class_select_{idx}",
                    disabled=st.session_state.is_loading_game,
                    format_func=lambda c: f"{'⚔️' if c=='Guerriero' else '🗡️' if c=='Ladro' else '🔮'}  {c}"
                )
                st.session_state.party_slots[idx]["class"] = new_class

        # --- Bottone "Aggiungi Avventuriero" ---
        if len(st.session_state.party_slots) < MAX_PLAYERS and not st.session_state.is_loading_game:
            with st.container():
                st.markdown('<div class="add-player-marker" style="display:none"></div>', unsafe_allow_html=True)
                if st.button(
                    f"＋  Aggiungi Avventuriero  ({len(st.session_state.party_slots)}/{MAX_PLAYERS})",
                    use_container_width=True,
                    key="add_player_btn"
                ):
                    st.session_state.party_slots.append({"name": "", "class": "Guerriero"})
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Riepilogo Party (solo se ci sono nomi) ---
        named_players = [s for s in st.session_state.party_slots if s.get("name", "").strip()]
        if named_players:
            party_summary = " · ".join(
                [f"{s['name']} ({s['class']})" for s in named_players]
            )
            st.markdown(
                f"<div style='font-size:0.75rem; color:#6b7280; text-align:center; margin-bottom:1rem; font-style:italic;'>🎲 {party_summary}</div>",
                unsafe_allow_html=True
            )

        # --- Bottone RADUNA IL PARTY ---
        with st.container():
            st.markdown('<div class="start-button-marker" style="display:none"></div>', unsafe_allow_html=True)
            
            # Validazione: almeno 1 giocatore con nome
            can_start = any(s.get("name", "").strip() for s in st.session_state.party_slots)
            
            if st.button(
                "⚔️  RADUNA IL PARTY",
                use_container_width=True,
                disabled=st.session_state.is_loading_game or not can_start,
                key="start_game_btn",
                help="Almeno un avventuriero deve avere un nome." if not can_start else ""
            ):
                # Filtra i giocatori senza nome e normalizza i dati
                valid_party = [
                    {"name": s["name"].strip(), "class": s["class"]}
                    for s in st.session_state.party_slots
                    if s.get("name", "").strip()
                ]
                
                # Salva nel session_state per app.py
                st.session_state.setup_party = valid_party
                st.session_state.setup_theme = st.session_state.selected_theme
                st.session_state.setup_mood = st.session_state.narrative_style
                # Legacy compatibility (primo giocatore come p1)
                st.session_state.setup_p1_name = valid_party[0]["name"]
                st.session_state.setup_p1_class = valid_party[0]["class"]
                
                st.session_state.is_loading_game = True
                st.rerun()

        if not can_start:
            st.caption("⚠️ Inserisci almeno un nome per iniziare l'avventura.")

    # --- LOADING SCREEN ---
    if st.session_state.is_loading_game:
        st.markdown("<br><br>", unsafe_allow_html=True)
        _, spin_col, _ = st.columns([1, 2, 1])
        with spin_col:
            n_players = len(st.session_state.get("setup_party", [{}]))
            theme_sel = st.session_state.selected_theme
            with st.spinner("Convocazione del destino in corso..."):
                status_text = st.empty()
                status_text.markdown(
                    f"<h3 style='text-align: center; color: #81d6be;'>"
                    f"Inizializzando '{theme_sel}'...<br>"
                    f"<span style='font-size:0.9rem; color:#6b7280;'>"
                    f"{n_players} avventurier{'i' if n_players > 1 else 'e'} si preparano al viaggio</span>"
                    f"</h3>",
                    unsafe_allow_html=True
                )
                time.sleep(2)
        st.session_state.is_loading_game = False
        st.session_state.page = "game"
        if "session_id" in st.session_state:
            save_game_state(st.session_state.session_id)
        st.rerun()

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Morpheus Genesis - Setup")
    render_setup_page()