import streamlit as st

def render_setup_page():
    # --- 1. CSS CUSTOM PER IL LOOK & FEEL ---
    st.markdown("""
        <style>
        /* Sfondo con Grid e Colori Dark */
        .stApp {
            background-color: #0d0d0d;
            background-image: 
                linear-gradient(to right, #1a1a1a 1px, transparent 1px),
                linear-gradient(to bottom, #1a1a1a 1px, transparent 1px);
            background-size: 40px 40px;
            color: #ffffff;
        }

        /* Titolo e Font */
        .main-title {
            font-size: 3.5rem;
            font-weight: 800;
            text-transform: uppercase;
            margin-bottom: 0;
            line-height: 1;
        }
        .purple-text {
            color: #9d66ff;
        }

        /* Card dei Temi */
        .theme-card {
            background: #151515;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
            transition: 0.3s;
            cursor: pointer;
            height: 100%;
        }
        .theme-card:hover {
            border-color: #9d66ff;
            box-shadow: 0 0 15px rgba(157, 102, 255, 0.3);
        }
        .theme-card.selected {
            border: 2px solid #9d66ff;
            background: #1a1525;
        }

        /* Status Box */
        .status-box {
            background: #111;
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #00ff88;
        }

        /* Input Fields */
        .stTextInput input {
            background-color: #000 !important;
            border: 1px solid #333 !important;
            color: white !important;
        }

        /* Pulsante Inizia Avventura */
        .stButton>button {
            background: linear-gradient(90deg, #9d66ff, #6b4cff);
            color: white;
            border: none;
            padding: 20px;
            font-size: 1.2rem;
            font-weight: bold;
            border-radius: 8px;
            width: 100%;
            text-transform: uppercase;
            letter-spacing: 2px;
            transition: 0.3s;
        }
        .stButton>button:hover {
            transform: scale(1.02);
            box-shadow: 0 0 30px rgba(157, 102, 255, 0.5);
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. HEADER ---
    st.markdown('<p class="main-title">CONFIGURA IL TUO <span class="purple-text">DESTINO</span></p>', unsafe_allow_html=True)
    st.write("Definisci l'ambientazione e i tuoi compagni di viaggio per iniziare la procedura.")
    st.markdown("<br>", unsafe_allow_html=True)

    # --- 3. TEMI NARRATIVI (GRID) ---
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("### 📖 TEMI NARRATIVI")
        
        # Simuliamo la grid dello screenshot
        t1, t2, t3, t4 = st.columns(4)
        themes = [
            ("🏰 Fantasy", "Antiche profezie e regni."),
            ("🦾 Cyberpunk", "Neon e impianti neurali."),
            ("🚀 Sci-Fi", "Esplorazione interstellare."),
            ("💀 Horror", "Incubi e oscurità.")
        ]
        
        for i, col in enumerate([t1, t2, t3, t4]):
            with col:
                selected = (i == 1) # Cyberpunk preselezionato come nell'immagine
                class_name = "theme-card selected" if selected else "theme-card"
                st.markdown(f"""
                    <div class="{class_name}">
                        <h4>{themes[i][0]}</h4>
                        <p style="font-size: 0.8rem; color: #888;">{themes[i][1]}</p>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        t5, t6, t7, t8 = st.columns(4)
        themes_2 = [
            ("🔍 Mystery", "Noir ed enigmi."),
            ("⚙️ Steampunk", "Ingranaggi e vapore."),
            ("⛰️ Post-Apoc", "Sopravvivenza tra macerie."),
            ("🌪️ Mythological", "Dei, titani e leggende.")
        ]
        for i, col in enumerate([t5, t6, t7, t8]):
            with col:
                st.markdown(f"""
                    <div class="theme-card">
                        <h4>{themes_2[i][0]}</h4>
                        <p style="font-size: 0.8rem; color: #888;">{themes_2[i][1]}</p>
                    </div>
                """, unsafe_allow_html=True)

    with col_right:
        st.markdown("### 👥 GIOCATORI")
        st.select_slider("", options=[1, 2, 3, 4], value=2, key="setup_players")
        st.caption("La complessità narrativa si adatterà al numero di agenti.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### STATO SISTEMA")
        st.markdown("""
            <div class="status-box">
                <p style="color: #00ff88; margin:0;">● Neural Engine Pronto</p>
                <p style="color: #9d66ff; margin:0;">● Dataset Cyberpunk Caricato</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- 4. CONFIGURAZIONE AGENTI ---
    st.markdown("### 🛠️ CONFIGURAZIONE AGENTI")
    
    a1, a2 = st.columns(2)
    
    with a1:
        with st.container(border=True):
            st.write("GIOCATORE 01")
            st.text_input("NOME", placeholder="Es. Valerius", key="setup_p1_name")
            st.radio("CLASSE", ["Warrior", "Mage", "Rogue", "Cleric"], horizontal=True, key="setup_p1_class")

    with a2:
        with st.container(border=True):
            st.write("GIOCATORE 02")
            st.text_input("NOME ", placeholder="Es. Elara", key="setup_p2_name")
            st.radio("CLASSE ", ["Warrior", "Mage", "Rogue", "Cleric"], horizontal=True, key="setup_p2_class")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 5. START BUTTON ---
    if st.button("INIZIA AVVENTURA ➔"):
        st.balloons()
        st.session_state.page = "game"
        st.rerun()