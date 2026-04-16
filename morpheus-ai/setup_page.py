import streamlit as st


def init_session_state():
    if 'selected_theme' not in st.session_state:
        st.session_state.selected_theme = "🦾 Cyberpunk"
    if 'num_players' not in st.session_state:
        st.session_state.num_players = 2
    if 'campaign_name' not in st.session_state:
        st.session_state.campaign_name = ""
    if 'difficulty' not in st.session_state:
        st.session_state.difficulty = "Normale"
    if 'is_loading_game' not in st.session_state:
        st.session_state.is_loading_game = False

def render_setup_page():
    init_session_state()

    # --- 1. CSS CUSTOM ---
    st.markdown("""
        <style>
        /* Sfondo Base */
        .stApp {
            background-color: #0a0a0a;
            background-image: 
                linear-gradient(to right, #141414 1px, transparent 1px),
                linear-gradient(to bottom, #141414 1px, transparent 1px);
            background-size: 30px 30px;
            color: #f0f0f0;
        }

        .block-container {
            padding-top: 2rem !important;
            max-width: 95% !important; /* Sfrutta più larghezza possibile */
        }

        .main-title {
            font-size: clamp(2rem, 4vw, 3.5rem);
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 0.2rem;
            line-height: 1.1;
        }
        .purple-text {
            color: #9d66ff;
            text-shadow: 0 0 15px rgba(157, 102, 255, 0.4);
        }

        .status-box {
            background: rgba(20, 20, 25, 0.9);
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #00ff88;
            height: 100%;
        }

        /* ---------------------------------------------------
           CARD DEI TEMI: Altezze fisse e wrap naturale
           --------------------------------------------------- */
        
        div[data-testid="stButton"] button {
            height: 240px !important; /* Altezza FISSA e uguale per tutti, ingrandita */
            width: 400px !important;
            border-radius: 12px !important;
            border: 1px solid #333 !important;
            background: #121212 !important;
            /* La transizione è fondamentale per l'hover */
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
            padding: 15px !important;
            
            /* Flexbox per distribuire il contenuto */
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-end !important; /* Testo parte dal basso per far vedere l'immagine */
            align-items: center !important;
            
            /* Preparazione sfondi */
            background-size: cover !important;
            background-position: center !important;
            background-blend-mode: overlay !important;
            background-color: rgba(18, 18, 18, 0.75) !important; /* Scuriamo l'immagine di default */
        }

        /* Hover: Glow Viola per i temi, e schiarisce l'immagine */
        div[data-testid="stButton"] button:hover {
            border-color: #9d66ff !important;
            box-shadow: 0 0 20px rgba(157, 102, 255, 0.5) !important;
            background-color: rgba(24, 20, 37, 0.4) !important;
            transform: translateY(-2px) !important;
        }

        div[data-testid="stButton"] button p {
            white-space: normal !important; /* Permette l'a capo naturale senza tagliare */
            word-break: break-word !important; 
            text-align: center !important;
            line-height: 1.4 !important;
            margin: 0 !important;
            font-size: 1.05rem !important; /* Leggermente più grande */
            text-shadow: 0 2px 4px rgba(0,0,0,0.9) !important; /* Ombra per leggibilità su immagini */
        }

        /* Stato Selezionato */
        div[data-testid="stButton"] button[kind="primary"] {
            border: 2px solid #9d66ff !important;
            background-color: rgba(157, 102, 255, 0.25) !important;
            box-shadow: 0 0 15px rgba(157, 102, 255, 0.5) !important;
        }

        /* Pulsante Start: stile spostato per isolamento */
        </style>
    """, unsafe_allow_html=True)

    # --- 2. HEADER ---
    st.markdown("""
        <div style="text-align: center; margin-bottom: 3rem; margin-top: 1rem;">
            <h1 style="font-size: clamp(3rem, 6vw, 5.5rem); letter-spacing: 6px; text-transform: uppercase; margin-bottom: -15px;">
                Morpheus <span class="purple-text">Genesis</span>
            </h1>
            <p style="color: #00ff88; font-size: 1.4rem; font-weight: bold; letter-spacing: 4px; text-transform: uppercase; text-shadow: 0 0 10px rgba(0, 255, 136, 0.3);">
                Configura il tuo Destino
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    # --- 3. PARAMETRI GLOBALI ---
    st.subheader("🌐 Parametri di Rete")
    col_sys1, col_sys2, col_sys3 = st.columns([2, 1.5, 1], gap="large")
    
    with col_sys1:
        st.session_state.campaign_name = st.text_input("NOME CAMPAGNA", value=st.session_state.campaign_name, placeholder="Es. Protocollo Omega...", disabled=st.session_state.is_loading_game)
    with col_sys2:
        st.session_state.difficulty = st.select_slider("LIVELLO DI SFIDA", options=["Storia", "Normale", "Difficile", "Incubo"], value=st.session_state.difficulty, disabled=st.session_state.is_loading_game)
    with col_sys3:
        st.session_state.num_players = st.number_input("NUMERO GIOCATORI", min_value=1, max_value=4, value=st.session_state.num_players, disabled=st.session_state.is_loading_game)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 4. TEMI NARRATIVI ---
    st.subheader("📖 Modulo Ambientale")
    st.caption("Clicca su una cella di memoria per selezionare l'ambientazione.")
    
    # Rimosso il \n per permettere al CSS (white-space: normal) di impaginare da solo
    themes = {
        "🏰 Fantasy": "Magia, draghi e regni in rovina.",
        "🦾 Cyberpunk": "Neon, corporazioni e impianti neurali.",
        "🚀 Sci-Fi": "Esplorazione stellare e IA ribelli.",
        "💀 Horror": "Oscurità, tensione e mostri indicibili.",
        "🔍 Mystery": "Enigmi, crimini e atmosfere noir.",
        "⚙️ Steampunk": "Vapore, ingranaggi e dirigibili.",
        "⛰️ Post-Apoc": "Sopravvivenza tra scorie radioattive.",
        "🌪️ Mythological": "Dei capricciosi e gesta eroiche."
    }
    theme_names = list(themes.keys())
    
    theme_images = {
        "🏰 Fantasy": "url('https://images.unsplash.com/photo-1518709268805-4e9042af9f23?q=80&w=600')",
        "🦾 Cyberpunk": "url('https://png.pngtree.com/thumb_back/fh260/background/20230705/pngtree-conceptual-3d-art-futuristic-cyberpunk-city-at-night-with-scifi-touches-image_3759066.jpg')",
        "🚀 Sci-Fi": "url('https://png.pngtree.com/thumb_back/fh260/background/20230611/pngtree-space-wallpapers-download-free-image_2929035.jpg')",
        "💀 Horror": "url('https://images.unsplash.com/photo-1505635552518-3448ff116af3?q=80&w=600')",
        "🔍 Mystery": "url('https://img.freepik.com/foto-gratuito/disposizione-astratta-del-concetto-di-verita_23-2149051376.jpg?semt=ais_hybrid&w=740&q=80')",
        "⚙️ Steampunk": "url('https://img.freepik.com/photos-premium/paysage-urbain-steampunk-dirigeables-volant-au-dessus-grands-batiments_14117-1014014.jpg?semt=ais_hybrid&w=740&q=80')",
        "⛰️ Post-Apoc": "url('https://img.freepik.com/free-photo/skyline-dystopian-future_23-2151957425.jpg?semt=ais_hybrid&w=740&q=80')",
        "🌪️ Mythological": "url('https://img.freepik.com/free-photo/fantasy-scene-depicting-sun-god-s_23-2151339297.jpg?semt=ais_hybrid&w=740&q=80')",
    }

    # Inject dynamic CSS to map each column to its specific background image via :has() trick
    css_bg = "<style>\n"
    for idx, (name, bg) in enumerate(theme_images.items()):
        css_bg += f"div[data-testid='stColumn']:has(.theme-marker-{idx}) div[data-testid='stButton'] button {{ background-image: {bg} !important; }}\n"
    css_bg += "</style>"
    st.markdown(css_bg, unsafe_allow_html=True)

    # 3 colonne per rendere le card più larghe. L'ultima riga avrà 2 card centrate.
    for row in range(0, 8, 3):
        if row + 3 <= 8:
            cols = st.columns(3, gap="large")
            items_to_render = 3
        else:
            # Ultima riga: creiamo layout con spaziatura laterale per centrare le 2 card rimanenti
            pad_cols = st.columns([0.5, 1, 1, 0.5], gap="large")
            cols = [pad_cols[1], pad_cols[2]]
            items_to_render = 2

        for i in range(items_to_render):
            idx = row + i
            if idx >= len(theme_names): 
                break
                
            theme_name = theme_names[idx]
            theme_desc = themes[theme_name]
            
            with cols[i]:
                # Invisible marker to act as anchor for CSS
                st.markdown(f'<span class="theme-marker-{idx}" style="display:none"></span>', unsafe_allow_html=True)
                
                # Usiamo \n\n per distanziare il titolo dalla descrizione.
                button_label = f"**{theme_name}**\n\n{theme_desc}"
                if theme_name == st.session_state.selected_theme:
                    st.button(button_label, key=f"btn_{theme_name}", use_container_width=True, type="primary", disabled=st.session_state.is_loading_game)
                else:
                    if st.button(button_label, key=f"btn_{theme_name}", use_container_width=True, disabled=st.session_state.is_loading_game):
                        st.session_state.selected_theme = theme_name
                        st.rerun()

    st.divider()

    # --- 5. GIOCATORI E DIAGNOSTICA ---
    col_agents, col_status = st.columns([2.5, 1.5], gap="large")

    with col_agents:
        st.subheader("🛠️ Inizializzazione Giocatori")
        players = int(st.session_state.num_players)
        
        for i in range(0, players, 2):
            agent_cols = st.columns(2, gap="medium")
            with agent_cols[0]:
                with st.container(border=True):
                    st.markdown(f"**GIOCATORE 0{i+1}**")
                    st.text_input("Identificativo", placeholder="Inserisci nome...", key=f"p{i+1}_name", label_visibility="collapsed", disabled=st.session_state.is_loading_game)
                    st.selectbox("Classe", ["Warrior", "Mage", "Rogue", "Cleric"], key=f"p{i+1}_class", label_visibility="collapsed", disabled=st.session_state.is_loading_game)
            if i + 1 < players:
                with agent_cols[1]:
                    with st.container(border=True):
                        st.markdown(f"**GIOCATORE 0{i+2}**")
                        st.text_input("Identificativo", placeholder="Inserisci nome...", key=f"p{i+2}_name", label_visibility="collapsed", disabled=st.session_state.is_loading_game)
                        st.selectbox("Classe", ["Warrior", "Mage", "Rogue", "Cleric"], key=f"p{i+2}_class", label_visibility="collapsed", disabled=st.session_state.is_loading_game)

    with col_status:
        st.subheader("⚙️ Diagnostica")
        display_name = st.session_state.campaign_name if st.session_state.campaign_name else "Non assegnato"
        
        st.markdown(f"""
            <div class="status-box">
                <p style="color: #00ff88; margin-bottom: 8px; font-weight: bold;">● Neural Engine Pronto</p>
                <p style="color: #aaa; font-size: 0.9rem; margin-bottom: 4px;">▸ Campagna: <b>{display_name}</b></p>
                <p style="color: #aaa; font-size: 0.9rem; margin-bottom: 4px;">▸ Difficoltà: <b>{st.session_state.difficulty}</b></p>
                <p style="color: #9d66ff; font-size: 0.9rem; margin-bottom: 0;">▸ Dataset: <b>{st.session_state.selected_theme}</b></p>
            </div>
        """, unsafe_allow_html=True)

    # --- 6. PULSANTE START CENTRATO E PIÙ PICCOLO ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Colonne per stringere il bottone e lasciarlo comodo al centro
    _, col_center, _ = st.columns([3, 2, 3])
    
    with col_center:
        # Iniettiamo lo stile localmente puntando ESATTAMENTE al contenitore adiacente (il bottone successivo)
        st.markdown("""
            <div class="start-btn-marker" style="display:none"></div>
            <style>
                div.element-container:has(.start-btn-marker) + div.element-container button {
                    height: 65px !important; 
                    background: linear-gradient(90deg, #9d66ff, #6b4cff) !important; 
                    color: #ffffff !important;
                    border: none !important;
                    padding: 0 !important;
                    border-radius: 8px !important; 
                    width: 100% !important;
                    transition: all 0.3s ease !important;
                    
                    /* Flexbox per centrare in modo assoluto e perfetto */
                    display: flex !important;
                    justify-content: center !important;
                    align-items: center !important;
                }
                
                /* Streamlit aggiunge dei div interni al bottone, dobbiamo centrare anche loro */
                div.element-container:has(.start-btn-marker) + div.element-container button div {
                    display: flex !important;
                    justify-content: center !important;
                    align-items: center !important;
                }
                
                div.element-container:has(.start-btn-marker) + div.element-container button:hover {
                    transform: translateY(-3px) !important;
                    box-shadow: 0 8px 20px rgba(157, 102, 255, 0.5) !important;
                    background: linear-gradient(90deg, #aa78ff, #7a5dff) !important;
                }
                
                div.element-container:has(.start-btn-marker) + div.element-container button p {
                    font-size: 1.15rem !important;
                    font-weight: bold !important;
                    color: #ffffff !important; 
                    text-transform: uppercase !important;
                    letter-spacing: 2px !important;
                    
                    /* Reset margini per allineamento millimetrico */
                    text-align: center !important;
                    line-height: 1 !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        

        if st.button("INIZIA AVVENTURA ➔", use_container_width=True, disabled=st.session_state.is_loading_game):
            # --- AGGIUNGI QUESTI SALVATAGGI ---
            st.session_state.setup_p1_name = st.session_state.get("p1_name", "Valerius")
            st.session_state.setup_p1_class = st.session_state.get("p1_class", "Warrior")
            st.session_state.setup_theme = st.session_state.selected_theme
            # ----------------------------------
            
            st.session_state.is_loading_game = True
            st.rerun()

    # --- ANIMAZIONE DI CARICAMENTO ---
    # Questa sezione fissa l'attenzione sotto il pulsante e blocca l'UI soprastante
    if st.session_state.is_loading_game:
        import time
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        _, spin_col, _ = st.columns([1, 2, 1])
        with spin_col:
            with st.spinner("Avvio del Neural Engine in corso..."):
                status_text = st.empty()
                
                status_text.markdown("<h3 style='text-align: center; color: #9d66ff; margin-bottom: 20px;'>Morpheus Genesis sta chiamando i suoi agenti...</h3>", unsafe_allow_html=True)
                
                theme = st.session_state.selected_theme
                
                status_text.markdown("<h3 style='text-align: center; color: #bbb; margin-bottom: 20px;'>Agente Arbitro sta forgiando le regole dello scontro...</h3>", unsafe_allow_html=True)
                import time
                time.sleep(1)
                
                status_text.markdown("<h3 style='text-align: center; color: #00ff88; margin-bottom: 20px;'>Neural Engine Pronto. Benvenuti in Morpheus Genesis.</h3>", unsafe_allow_html=True)
                time.sleep(1.5)
                
        st.session_state.is_loading_game = False
        st.session_state.page = "game"
        st.rerun()

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Setup Destino")
    render_setup_page()