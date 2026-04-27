import random
import streamlit as st
import logging

logger = logging.getLogger("morpheus_ai")

CLASS_MOVES = {
    "Guerriero": [
        {"name": "Attacco Pesante", "damage": "1d10+4", "desc": "Un fendente brutale."},
        {"name": "Scudo d'Acciaio", "damage": "1d4+4", "desc": "Colpisci col bordo dello scudo."}
    ],
    "Mago": [
        {"name": "Dardo Incantato", "damage": "2d4+5", "desc": "Dardi di pura energia magica."},
        {"name": "Esplosione Arcana", "damage": "1d12+2", "desc": "Un'onda d'urto distruttiva."}
    ],
    "Ladro": [
        {"name": "Attacco Furtivo", "damage": "1d6+6", "desc": "Colpisci i punti vitali."},
        {"name": "Lama Veloce", "damage": "2d4+3", "desc": "Due fendenti rapidissimi."}
    ]
}

def resolve_combat_round(move_name, d20_roll=None):
    hero = st.session_state.world_state.party[0]
    enemy = st.session_state.world_state.active_enemies[0]
    
    # 1. TURNO GIOCATORE: d20 + bonus (fisso a +4 per ora) vs CA Nemico
    roll = d20_roll if d20_roll is not None else random.randint(1, 20)
    total_atk = roll + 4
    hit = total_atk >= enemy.ac
    
    if hit:
        dmg = random.randint(4, 12) # Danno variabile
        enemy.hp -= dmg
        st.session_state.world_state.combat_log.append(f"💥 **{hero.name}** usa {move_name}: COLPITO! ({total_atk} vs CA {enemy.ac}) per {dmg} danni.")
    else:
        st.session_state.world_state.combat_log.append(f"🛡️ **{hero.name}** usa {move_name}: MANCATO! ({total_atk} vs CA {enemy.ac}).")

    # 1b. USURA ARMA: Ogni attacco consuma un po' di durabilità
    for item in hero.inventory:
        if item.item_type == "weapon" and item.durability is not None:
            wear = random.randint(2, 5)
            item.durability -= wear
            if item.durability <= 0:
                item.durability = 0
                st.session_state.world_state.combat_log.append(f"⚠️ **ATTENZIONE**: La tua arma ({item.name}) si è rotta durante lo scontro!")
                hero.inventory.remove(item)
            break # Applichiamo l'usura solo alla prima arma trovata (quella usata)

    if enemy.hp <= 0:
        enemy.hp = 0
        st.session_state.world_state.combat_log.append(f"💀 **{enemy.name}** è stato sconfitto!")
        return "vittoria"

    # 2. TURNO NEMICO: Il nemico attacca sempre dopo il giocatore
    e_roll = random.randint(1, 20)
    e_total = e_roll + 3
    if e_total >= hero.ac:
        e_dmg = random.randint(3, 8)
        hero.hp -= e_dmg
        st.session_state.world_state.combat_log.append(f"⚠️ **{enemy.name}** colpisce: {e_dmg} danni subiti!")
    else:
        st.session_state.world_state.combat_log.append(f"💨 **{enemy.name}** manca il colpo.")
    
    if hero.hp <= 0:
        hero.hp = 0
        st.session_state.world_state.combat_log.append(f"☠️ **{hero.name}** è stato sconfitto!")
        return "sconfitta"
        
    return "continua"
