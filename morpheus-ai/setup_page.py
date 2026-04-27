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

def init_session_state():
    if 'selected_theme' not in st.session_state:
        st.session_state.selected_theme = "Cyberpunk"
    if 'num_players' not in st.session_state:
        st.session_state.num_players = 2
    if 'campaign_name' not in st.session_state:
        st.session_state.campaign_name = ""
    if 'difficulty' not in st.session_state:
        st.session_state.difficulty = "Normale"
    if 'narrative_style' not in st.session_state:
        st.session_state.narrative_style = "Oscuro"
    if 'is_loading_game' not in st.session_state:
        st.session_state.is_loading_game = False

def render_setup_page():
    init_session_state()

    # --- 1. GLOBAL UI TWEAKS (CSS INJECTION)  ---
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
        
        /* Top Navigation Mockup */
        .top-nav {
            background-color: #0a0a0a;
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 64px;
            display: flex;
            align-items: center;
            padding: 0 2rem;
            box-shadow: 0 4px 24px rgba(0,0,0,0.2);
            z-index: 100;
        }
        

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

        /* Typography Override */
        .header-subtitle { color: #81d6be; letter-spacing: 0.1em; font-size: 0.875rem; text-transform: uppercase; font-weight: 500;}
        .header-title { font-family: 'Manrope', sans-serif; font-size: clamp(2.5rem, 4vw, 3.75rem); font-weight: 700; line-height: 1.1; margin-bottom: 1rem;}
        .header-desc { color: #bec9c4; font-size: 1.125rem; max-width: 600px; margin-bottom: 2rem;}
        
        .section-title {
            display: flex; align-items: center; gap: 0.75rem;
            font-size: 1.5rem; font-weight: 600; margin-bottom: 1rem;
            font-family: 'Manrope', sans-serif;
        }
        .section-title span.material-symbols-outlined { color: #81d6be; }

        /* Inputs override */
        div[data-baseweb="input"] {
            background-color: #2a2a2a;
            border-radius: 0.75rem;
            border: 1px solid transparent;
        }
        div[data-baseweb="input"]:focus-within { border-color: rgba(129,214,190, 0.4); }
        div[data-baseweb="input"] > input { color: #e5e2e1; padding: 0.75rem 1rem;}
        
        /* Selectbox override */
        div[data-baseweb="select"] {
            background-color: #2a2a2a;
            border-radius: 0.75rem;
            border: 1px solid transparent;
        }

        /* --- SEGMENTED CONTROL NATIVI (STREAMLIT 1.56+) --- */
        /* Rimuove il focus ring rosso da tutti i pulsanti nel gruppo */
        div[data-testid="stButtonGroup"] button:focus,
        div[data-testid="stButtonGroup"] button:focus-visible {
            box-shadow: 0 0 0 2px rgba(129, 214, 190, 0.4) !important;
            outline: none !important;
        }

        /* STATO ATTIVO: Sovrascrive il rosso di base con il gradiente verde acqua */
        div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] {
            background: linear-gradient(135deg, #81d6be, #227e69) !important;
            color: #00382c !important;
            border-color: #81d6be !important;
            font-weight: 700 !important;
        }

        /* Colore del testo interno per lo stato attivo */
        div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] * {
            color: #00382c !important;
        }

        /* STATO HOVER: Colora i bordi e il testo dei pulsanti non selezionati al passaggio del mouse */
        div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"]:hover {
            border-color: #81d6be !important;
            color: #81d6be !important;
            background-color: rgba(129, 214, 190, 0.1) !important;
        }

        /* Colore del testo in hover */
        div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_control"]:hover * {
            color: #81d6be !important;
        }

        .player-card {
            background-color: #1c1b1b;
            padding: 1.25rem;
            border-radius: 0.75rem;
            margin-bottom: 1.5rem;
            border: 1px solid transparent;
            transition: border-color 0.3s;
        }
        .player-card:hover { border-color: rgba(136,147,142,0.2); }
        
        /* --- THEME BUTTONS TRICK (Injected Via Markdown) --- */
        /* Will be handled individually to map to Streamlit buttons */
        
        /* Start Button - Container Targeted Strategy */
        div[data-testid="stVerticalBlock"]:has(> div.element-container div.start-button-marker) button {
            background: linear-gradient(135deg, #81d6be, #227e69) !important;
            color: #00382c !important;
            font-family: 'Manrope', sans-serif !important;
            font-size: 1rem !important;
            font-weight: 700 !important;
            height: 48px !important;
            width: 200px !important;
            border-radius: 0.75rem !important;
            box-shadow: 0 12px 24px rgba(34, 126, 105, 0.2) !important;
            margin-top: 10px !important;
            margin-left: auto !important;
            border: none !important;
            transition: all 0.3s ease !important;
        }

        div[data-testid="stVerticalBlock"]:has(> div.element-container div.start-button-marker) button:hover {
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 0 20px rgba(129, 214, 190, 0.6), 
                        0 0 40px rgba(129, 214, 190, 0.3),
                        0 16px 32px rgba(34, 126, 105, 0.4) !important;
            filter: brightness(1.1) !important;
        }
        
        <div class="abstract-bg"></div>
    
    """, unsafe_allow_html=True)

    # --- 2. LAYOUT SPLIT (equivalent to grid-cols-12: 7 and 5) ---
    col_left, col_border, col_right = st.columns([6, 0.5, 4.5])

    with col_left:
        # HEADER
        st.markdown("""
            <div class="header-subtitle">Morpheus Genesis</div>
            <div class="header-title">Configura la tua<br>Spedizione</div>
            <div class="header-desc">Seleziona la base tematica della tua narrazione e definisci gli avventurieri che attraverseranno questo regno.</div>
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

        # NARRATIVE THEME & MOOD HEADER
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

        # ---------------------------------------------------------------
        # CSS PESANTE (immagini base64): iniettato UNA SOLA VOLTA
        # fuori dal fragment — non viene mai più reinviato al browser.
        # ---------------------------------------------------------------
        css_bg = "<style>\n"
        for i, (t_name, t_data) in enumerate(themes.items()):
            bg_css = t_data['bg']
            if not bg_css.startswith("url("):
                bg_css = get_cached_base64_image(bg_css)

            css_bg += f"""
                /* --- STATO INATTIVO (BASE) per tema {i} --- */
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
                /* --- STATO ATTIVO per tema {i} --- */
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

        # ---------------------------------------------------------------
        # FRAGMENT: ri-renderizza SOLO i pulsanti (dati leggeri, niente immagini)
        # ---------------------------------------------------------------
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

    with col_right:
        @st.fragment
        def render_right_panel():
            st.markdown("""

            """, unsafe_allow_html=True)
            
            # TOP ACTIONS ROW
            top_act_l, top_act_r = st.columns([1, 1])
            
            with top_act_l:
                # Multiplayer rimosso per semplificare l'interfaccia
                pass
            
            
            with top_act_r:
                with st.container():
                    st.markdown('<div class="start-button-marker" style="display:none"></div>', unsafe_allow_html=True)
                    if st.button("INIZIA AVVENTURA", use_container_width=True, disabled=st.session_state.is_loading_game):
                        # Salva logic per engine 
                        st.session_state.setup_theme = st.session_state.selected_theme
                        st.session_state.setup_mood = st.session_state.narrative_style
                        st.session_state.is_loading_game = True
                        st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Player Config Loop (Single Player Only)
            players = 1
            
            # Inject styling specific for player container
            st.markdown("""
            <style>
            div[data-testid="stVerticalBlock"]:has(> div.element-container div.player-card-marker) {
                background-color: #1c1b1b;
                padding: 1.25rem;
                border-radius: 0.75rem;
                margin-bottom: 1.5rem;
                border: 1px solid transparent;
                transition: border-color 0.3s;
            }
            div[data-testid="stVerticalBlock"]:has(> div.element-container div.player-card-marker):hover { 
                border-color: rgba(136,147,142,0.2); 
            }
            </style>
            """, unsafe_allow_html=True)

            for p in range(players):
                with st.container():
                    st.markdown(f"""
                        <div class="player-card-marker" style="display:none"></div>
                        <div style="display:flex; justify-content:space-between; margin-bottom: 1rem;">
                            <span style="font-size:0.75rem; color:#bec9c4; font-weight:600; letter-spacing:0.05em; text-transform:uppercase;">Eroe Principale</span>
                            <span class="material-symbols-outlined" style="font-size: 1rem; color:#bec9c4;">person</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    p_val = st.session_state.get(f"setup_p{p+1}_name", "Valerius" if p==0 else "")
                    c_val = st.session_state.get(f"setup_p{p+1}_class", "Guerriero")
                    
                    st.markdown("<label style='font-size: 0.875rem; color: #bec9c4; margin-bottom: 0.25rem;'>Nome del Personaggio</label>", unsafe_allow_html=True)
                    st.session_state[f"setup_p{p+1}_name"] = st.text_input(f"NOME P{p+1}", value=p_val, placeholder="In attesa di inserimento..." if p!=0 else "Inserisci nome", label_visibility="collapsed", disabled=st.session_state.is_loading_game, autocomplete="name")
                    
                    st.markdown("<label style='font-size: 0.875rem; color: #bec9c4; margin-top: 0.5rem; margin-bottom: 0.25rem;'>Classe / Archetipo</label>", unsafe_allow_html=True)
                    classi = ["Guerriero", "Ladro", "Mago"]
                    st.session_state[f"setup_p{p+1}_class"] = st.selectbox(f"CLASSE P{p+1}", classi, index=classi.index(c_val) if c_val in classi else 0, label_visibility="collapsed", disabled=st.session_state.is_loading_game)

            st.markdown("</div>", unsafe_allow_html=True) # close party box

        render_right_panel()

    # --- LOADING SCREEN ---
    if st.session_state.is_loading_game:
        st.markdown("<br><br>", unsafe_allow_html=True)
        _, spin_col, _ = st.columns([1, 2, 1])
        with spin_col:
            with st.spinner("Connessione al Neural Engine in corso..."):
                status_text = st.empty()
                status_text.markdown(f"<h3 style='text-align: center; color: #81d6be;'>Bypass dei protocolli di sicurezza... Inizializzando '{st.session_state.selected_theme}'...</h3>", unsafe_allow_html=True)
                time.sleep(2)
        st.session_state.is_loading_game = False
        st.session_state.page = "game"
        if "session_id" in st.session_state:
            save_game_state(st.session_state.session_id)
        st.rerun()

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Morpheus Genesis - Setup")
    render_setup_page()