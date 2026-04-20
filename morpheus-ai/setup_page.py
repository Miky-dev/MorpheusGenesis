import streamlit as st
import time

def init_session_state():
    if 'selected_theme' not in st.session_state:
        st.session_state.selected_theme = "Cyberpunk"
    if 'num_players' not in st.session_state:
        st.session_state.num_players = 2
    if 'campaign_name' not in st.session_state:
        st.session_state.campaign_name = ""
    if 'difficulty' not in st.session_state:
        st.session_state.difficulty = "Normal"
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
            <div class="header-title">Configure<br>Your Expedition</div>
            <div class="header-desc">Select the thematic foundation of your narrative and define the adventurers who will traverse this realm.</div>
        """, unsafe_allow_html=True)
        
        # CAMPAIGN SETTINGS
        st.markdown("""
            <div class="section-title">
                <span class="material-symbols-outlined">settings_applications</span>
                <span>Campaign Settings</span>
            </div>
        """, unsafe_allow_html=True)
        
        setting_cols = st.columns([1, 1])
        with setting_cols[0]:
            st.markdown("<label style='font-size: 0.875rem; color: #bec9c4; font-weight: 600; margin-bottom: 0.5rem; display: block;'>Campaign Name</label>", unsafe_allow_html=True)
            st.text_input("NOME", key="campaign_name", placeholder="e.g. The Obsidian Crown", label_visibility="collapsed", disabled=st.session_state.is_loading_game, autocomplete="off")
        with setting_cols[1]:
            st.markdown("<label style='font-size: 0.875rem; color: #bec9c4; font-weight: 600; margin-bottom: 0.5rem; display: block;'>Difficulty</label>", unsafe_allow_html=True)
            diff_options = ["Easy", "Normal", "Hard", "Epic"]
            st.segmented_control(
                "Difficoltà", 
                options=diff_options, 
                key="difficulty",
                label_visibility="collapsed", 
                disabled=st.session_state.is_loading_game,
                selection_mode="single"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # NARRATIVE THEME & MOOD HEADER
        theme_mood_cols = st.columns([1.5, 1])
        with theme_mood_cols[0]:
            st.markdown("""
                <div class="section-title" style="margin-top: 1rem;">
                    <span class="material-symbols-outlined">auto_stories</span>
                    <span>Narrative Theme</span>
                </div>
            """, unsafe_allow_html=True)
        with theme_mood_cols[1]:
            st.markdown("<label style='font-size: 0.875rem; color: #bec9c4; font-weight: 600; margin-bottom: 0.5rem; display: block;'>Narrative Mood</label>", unsafe_allow_html=True)
            moods = ["Oscuro", "Eroico", "Divertente", "Misterioso", "Cyberpunk", "Tragico"]
            st.session_state.narrative_style = st.selectbox(
                "Narrative Mood", 
                moods, 
                index=moods.index(st.session_state.narrative_style) if st.session_state.narrative_style in moods else 0, 
                label_visibility="collapsed", 
                disabled=st.session_state.is_loading_game
            )
            st.markdown("</div>", unsafe_allow_html=True)
        
        themes = {
            "Fantasy": {"icon": "swords", "bg": "url('https://lh3.googleusercontent.com/aida-public/AB6AXuDbWQubtqL5TSapDqpXUL5JzF9ULGqEVHPjd1oWGR7tDuxLoMPnXQkHuj57cQtTNUjZJsBeklZmxcKmYVVKYSjZKq0G-vGTS6LH4AwP7MlqN4DkogdS3TJQglstxap_hk6i4xlIoREVCxuV2UFw5daN29goJQAaaqULI-jtuVdbkYrcDAFvNEeQ_gP7XFKAWuvPPUHVLXmu3X3h85_dlAL_nG58khD-s81bsT6Rj98hj8kPTaZoCGbMurQX7euT3bNfZq8hcC9XfZc')"},
            "Cyberpunk": {"icon": "memory", "bg": "url('https://lh3.googleusercontent.com/aida-public/AB6AXuB6tjCCHnSp_5193HTFpb-qywgnrvmoqViyaHuslEKZZAMbwO2t54eQwpuYaDw6YsSF4zaKI6B45xXJRTxSu2mL5uxZEhK32XASkchAOttvXsisdcIzazk1-MzjV3Eadp1GJPejDefnHP6euUfvLLG5nTY7UNnl7PZ3jjj_77igylLFbxzd3zAf3-syggkVkqYt47P_NRIC2U6XWJd20bV1yUH8m85Cvs-l1mxV2rIycNV9gM0f853Wcw4n06ucfESAgixJkkIg-1E')"},
            "Sci-Fi": {"icon": "rocket_launch", "bg": "url('https://lh3.googleusercontent.com/aida-public/AB6AXuAdRjdFIvBrYbSilSCXIEdVl6pnU1qOYRvqtdlkTrdYIz02iY0Yb0TdkCBpOUEeb7bRIIfJfBJZBAlp0s3dFFpNWUy9oanxX4X13FnNYAy-3uP7VhEdVdJ4kT3PH09SQ04UcrnDpzpPtpTbe-0-Qz6eEBF47FeFRzSADFgxO0wS0CosZwbRsffa-SFVxREPJzKzHJfi8kUp8tUMlhpMD3t6EGzwyscaxhuVy0SB_87ddDbkO6IH0a0IGiSnsQci0h9lglo5kkzK8qo')"},
            "Horror": {"icon": "psychiatry", "bg": "url('https://lh3.googleusercontent.com/aida-public/AB6AXuCpMT6Q_DSJVOC6HAlW5Ap0IAUaF9imuhvGeo7Z-tvJmdv6ip4Ep0DZlTEeM6b6CrYT2T_gnUqMubOGTz7oFZGXXdozjZ8mkoVU3YwrEva4u4mx9sxeQVNxIVsWV-KOymkyntxRU9u2avWb_satKUDgIW4KtnhpbuqGQDepHOTmRJC2tnq4C03AcZAyJ9wxdK-WycIkjibstYLxAYCPJLvUDF1Ld0eMXJxE_amdGFWqkMJj64zCXfLXbDJXgA71m2dvGoel-Aa9HkA')"},
            "Post-Apoc": {"icon": "local_fire_department", "bg": "url('https://lh3.googleusercontent.com/aida-public/AB6AXuBp76HBktJCPq5144vFyy_0A04caHS6N9ZLrapDudUG61OrJHVL2JoiRRHzud2JEZnoM1EyN4kW_jhXxDk2R4XhHstmr8BPZ4Isp0Yow6HusqbOnqGCx-eYp75D-s8HVr3AuAtB8LPxuc7XQBzZZPadptZBgEaUEjeTyz6tiqSr6DIBuwVNeIWz1FrWLCIkS_qz97kJ22wCLsSRzXztUtEn2-gpuN_90uGRpVZTExqVjX0zs1Y-ijDEd2j4qPb2Jzs79nm-H12z3Wk')"},
            "Steampunk": {"icon": "castle", "bg": "url('https://lh3.googleusercontent.com/aida-public/AB6AXuCZM8RgZZJPO5dg93xTUeCiRxFrpbrNAvS9yhMgLG6UAbRteGUxkPyLTbWiND1CwECT93L-V3lJmyBiG3ow4EuTz-QwfXDJIYXphhDmZL73r5iT5XQH07tfXhYk8ErS4tNd6PTK8B4ZosLVuoDQbvNjanr9e7m-j1CUuPkbvQ-eGaxi6iKW22sRLwwOzj_g9Sn8Kv65zRmh760GcDLTfNV5p5SK8Uk3S0gg5Wd0zFFXC8po3ubVqlVK_A5mS_f4Htf0VO21YeJ7PWY')"},
            "Mystery": {"icon": "mystery", "bg": "url('https://lh3.googleusercontent.com/aida-public/AB6AXuDkRe1YyMwY2WsbNjxmq-YrwPBpzV6JSQcnaRg86Z7RqTvw3qht0OtgW91xQrHb3HZC7gxTEAswEzDReUPU2IiXlBGSpR6h5fLCmoYkRBqjyU2Sy_oI2iEvZzm_vLMOvuImYVdfrYFIB6CooIuclzDwK5VotgcgpP-uWGMCd1dN9dswNX2G6D4wg5GfIDtdbFLGbESFH4t2GZ4uWpDObnhqPnaQ6XKdyFhfJYp0Wn9bjwHD5huNuNi2n89-ryndXpooOoxaKe0KNRQ')"},
            "Wilderness": {"icon": "eco", "bg": "url('https://lh3.googleusercontent.com/aida-public/AB6AXuD_tRVxWEQ8EEhoBVgatHN6AtaSBLQqO0skz2C1bF6htlaiyG14R5nLTm1AYh5blY2mqtgWYcehwP4ksu5HEwPEHvjnwtZCHBvlpqgW8r-wyM2nGBr9tHoODDM-7ZWg0_zA9QdwEItuRDAMlsPutFLddwY7ogTuNm0kHJsYKTAx6nxOZlXkO7TvrP2cEKgPo6snBtievKToM96V2H1Fobl8rpcehfuICBG6KkTq1vFlR-e1ed5RfbjhNibkEhbxq6reu1Jj7nSqdYA')"}
        }
        
        # Inietta la logica CSS dei pulsanti con le immagini come l'HTML originale
        css_bg = "<style>\n"
        for i, (t_name, t_data) in enumerate(themes.items()):
            active = t_name == st.session_state.selected_theme
            bg_overlay = "rgba(42, 42, 42, 0.4)" if not active else "rgba(129, 214, 190, 0.1)"
            border_c = "rgba(136, 147, 142, 0.2)" if not active else "rgba(129, 214, 190, 0.4)"
            hover_border = "rgba(255, 255, 255, 0.2)" if not active else "#81d6be"
            c_text = "#81d6be" if active else "#bec9c4"
            
            # Attenzione, il wrapper stButton deve riempire
            css_bg += f"""
                div.element-container:has(.theme-{i}) + div.element-container div[data-testid='stButton'] button {{
                    background-image: linear-gradient({bg_overlay}, {bg_overlay}), {t_data['bg']} !important;
                    background-size: cover !important; background-position: center !important;
                    height: 140px !important; width: 100% !important; border-radius: 0.75rem !important;
                    border: 1px solid {border_c} !important; border-bottom: 2px solid {hover_border} !important;
                    color: transparent !important; /* Nasconde font di base di ST */
                    position: relative; overflow: hidden;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.4) !important;
                    display: flex !important;
                    flex-direction: column !important;
                    align-items: center !important;
                    justify-content: center !important;
                }}
                /* Nascondi il markdown placeholder di Streamlit interno al bottone */
                div.element-container:has(.theme-{i}) + div.element-container div[data-testid='stButton'] button div {{
                    display: none !important;
                }}
                /* Icona centrata */
                div.element-container:has(.theme-{i}) + div.element-container div[data-testid='stButton'] button::before {{
                    content: "{t_data['icon']}";
                    font-family: 'Material Symbols Outlined';
                    font-size: 2.2rem;
                    color: {c_text};
                    margin-bottom: 8px;
                    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.8));
                }}
                /* Testo centrato */
                div.element-container:has(.theme-{i}) + div.element-container div[data-testid='stButton'] button::after {{
                    content: "{t_name}";
                    font-family: 'Inter', sans-serif;
                    font-weight: 500;
                    font-size: 0.9rem;
                    color: {c_text};
                    text-shadow: 0 2px 4px rgba(0,0,0,0.8);
                }}
                /* Hover effect per i thumbnail */
                div.element-container:has(.theme-{i}) + div.element-container div[data-testid='stButton'] button:hover {{
                    border: 1px solid {hover_border} !important;
                    filter: brightness(1.2);
                }}
            """

        css_bg += "</style>"
        st.markdown(css_bg, unsafe_allow_html=True)
        
        # Griglia 4 colonne
        theme_names = list(themes.keys())
        for row in range(0, len(theme_names), 4):
            cols = st.columns(4)
            for i in range(4):
                if row + i < len(theme_names):
                    t_name = theme_names[row+i]
                    with cols[i]:
                        st.markdown(f'<span class="theme-{row+i}" style="display:none"></span>', unsafe_allow_html=True)
                        if st.button(" ", key=f"tbtn_{t_name}", use_container_width=True, disabled=st.session_state.is_loading_game):
                            st.session_state.selected_theme = t_name
                            st.rerun()

    with col_right:
        st.markdown("""

        """, unsafe_allow_html=True)
        
        # TOP ACTIONS ROW
        top_act_l, top_act_r = st.columns([1, 1])
        
        with top_act_l:
            st.markdown("<label style='font-size: 0.875rem; color: #bec9c4; font-weight: 600;'>Adventurers</label>", unsafe_allow_html=True)
            player_counts = [1, 2, 3, 4]
            st.segmented_control(
                "GIOCATORI", 
                options=player_counts, 
                key="num_players",
                label_visibility="collapsed", 
                disabled=st.session_state.is_loading_game,
                selection_mode="single"
            )
        
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
        
        # Player Config Loop
        players = int(st.session_state.num_players)
        
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
                        <span style="font-size:0.75rem; color:#bec9c4; font-weight:600; letter-spacing:0.05em; text-transform:uppercase;">Player 0{p+1}</span>
                        <span class="material-symbols-outlined" style="font-size: 1rem; color:#bec9c4;">person</span>
                    </div>
                """, unsafe_allow_html=True)
                
                p_val = st.session_state.get(f"setup_p{p+1}_name", "Valerius" if p==0 else "")
                c_val = st.session_state.get(f"setup_p{p+1}_class", "Warrior")
                
                st.markdown("<label style='font-size: 0.875rem; color: #bec9c4; margin-bottom: 0.25rem;'>Character Name</label>", unsafe_allow_html=True)
                st.session_state[f"setup_p{p+1}_name"] = st.text_input(f"NOME P{p+1}", value=p_val, placeholder="Awaiting entry..." if p!=0 else "Enter name", label_visibility="collapsed", disabled=st.session_state.is_loading_game, autocomplete="name")
                
                st.markdown("<label style='font-size: 0.875rem; color: #bec9c4; margin-top: 0.5rem; margin-bottom: 0.25rem;'>Class / Archetype</label>", unsafe_allow_html=True)
                st.session_state[f"setup_p{p+1}_class"] = st.selectbox(f"CLASSE P{p+1}", ["Warrior", "Hacker", "Rogue", "Mage"], index=["Warrior", "Hacker", "Rogue", "Mage"].index(c_val) if c_val in ["Warrior", "Hacker", "Rogue", "Mage"] else 0, label_visibility="collapsed", disabled=st.session_state.is_loading_game)


        

        st.markdown("</div>", unsafe_allow_html=True) # close party box

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
        st.rerun()

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="The Archive Setup")
    render_setup_page()