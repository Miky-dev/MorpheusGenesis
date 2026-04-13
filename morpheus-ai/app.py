import streamlit as st
from dotenv import load_dotenv
import os

# Import dei vostri moduli
from agents.rules_agent import rules_agent
from knowledge.chroma_store import DungeonMemory
from contracts.schemas import WorldState, Character, Enemy

# Caricamento variabili d'ambiente
load_dotenv()

# 1. Inizializzazione Session State (Membro B)
if "world_state" not in st.session_state:
    # Creiamo uno stato iniziale di test
    hero = Character(name="Valerius", char_class="Guerriero", hp=24, max_hp=24)
    skeleton = Enemy(name="Scheletro", hp=20, ac=13)
    
    st.session_state.world_state = WorldState(
        party=[hero],
        active_enemies=[skeleton]
    )

if "memory" not in st.session_state:
    st.session_state.memory = DungeonMemory(session_id="test_session_001")

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None

if "current_user_input" not in st.session_state:
    st.session_state.current_user_input = ""

# UI TITOLO
st.title("⚔️ Project Morpheus — Test Sprint 1")
st.subheader("Integrazione Rules Agent + World State + ChromaDB")

# Sidebar con lo Stato del Mondo (Visualizzazione per debug)
with st.sidebar:
    st.header("🌍 World State")
    st.json(st.session_state.world_state.model_dump())

# 2. Interfaccia di Gioco (Membro B)
st.write(f"**Personaggio:** {st.session_state.world_state.party[0].name}")
st.write(f"**Nemico:** {st.session_state.world_state.active_enemies[0].name} (HP: {st.session_state.world_state.active_enemies[0].hp})")

user_input = st.text_input("Cosa vuoi fare?", placeholder="Esempio: Attacco lo scheletro con la spada")

# --- LOGICA DI GESTIONE TURNO (Membro A + B) ---

# Fase 1: Elaborazione Azione (Athena decide cosa serve)
if st.button("Valuta Azione"):
    if user_input:
        with st.spinner("Athena sta decidendo il destino..."):
            response = rules_agent.run(user_input)
            
            # --- PARSING ROBUSTO (Manteniamo la logica di gestione stringhe/errori) ---
            content = response.content
            if isinstance(content, str):
                import json
                try:
                    clean_str = content.replace('```json', '').replace('```', '').strip()
                    data = json.loads(clean_str)
                    
                    if "error" in data:
                        error_msg = data["error"].get("message", "Errore sconosciuto")
                        if data["error"].get("code") == 429:
                            st.error("⏳ **Limite superato!** Google ti ha messo in pausa. Aspetta circa 60 secondi.")
                        else:
                            st.error(f"❌ Errore API: {error_msg}")
                        st.stop()
                    
                    from contracts.schemas import RulesResult
                    result = RulesResult(**data)
                except Exception as e:
                    st.error(f"⚠️ Risposta non standard. Riprova tra poco.")
                    with st.expander("Debug"):
                        st.code(content)
                    st.stop()
            else:
                result = content
            # --- FINE PARSING ---
            
            # Salviamo il verdetto di Athena nello stato della sessione
            st.session_state.pending_action = result
            st.session_state.current_user_input = user_input
    else:
        st.warning("Scrivi qualcosa!")

# Fase 2: Il Lancio del Dado (Manuale del giocatore)
if st.session_state.pending_action:
    res = st.session_state.pending_action
    
    if res.needs_clarification:
        st.warning(f"🤔 {res.narrative_hint}")
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
                
            # Salvataggio in Memoria
            turn_num = st.session_state.world_state.turn_number
            event_text = f"Turno {turn_num}: {st.session_state.current_user_input}. "
            event_text += f"Tiro: {total} (Dado {d20_roll} + {modifier}). "
            event_text += f"Esito: {'Colpito' if hit else 'Mancato'}. {res.narrative_hint}"
            
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
            
            # Visualizzazione rapida prima del rerun
            st.write(f"**Suggerimento narrativo:** *{res.narrative_hint}*")
            st.rerun()