import random
import re

# Statistiche predefinite dei nemici noti nel Bestiario
BESTIARY_STATS = {
    "lupo delle nebbie": {"hp": 45, "ac": 13, "atk": 4, "dmg": (5, 10), "loot": "Pelle argentata, zanne affilate, occhi incantati"},
    "ragno di cristallo": {"hp": 55, "ac": 15, "atk": 5, "dmg": (6, 12), "loot": "Filo di cristallo, ghiandola velenifera, frammenti di carapace"},
    "golem di basalto": {"hp": 85, "ac": 16, "atk": 6, "dmg": (8, 16), "loot": "Nucleo elementale, frammenti runici, minerali rari"},
    "sirena abissale": {"hp": 50, "ac": 14, "atk": 5, "dmg": (6, 14), "loot": "Perla incantata, squame luminose, conchiglia melodica"},
    "idra delle paludi": {"hp": 100, "ac": 15, "atk": 7, "dmg": (10, 18), "loot": "Sangue rigenerante, squame di drago minore, denti velenosi"},
    "spettro del giuramento": {"hp": 65, "ac": 15, "atk": 6, "dmg": (7, 14), "loot": "Essenza spettrale, spada benedetta, frammenti di armatura eterea"},
    "divoratore d'ombre": {"hp": 70, "ac": 16, "atk": 6, "dmg": (8, 15), "loot": "Essenza d'ombra, cristallo oscuro, residui magici"},
    "drago delle tempeste": {"hp": 120, "ac": 18, "atk": 8, "dmg": (12, 22), "loot": "Scaglie draconiche, artigli, cuore del fulmine, tesoro accumulato"},
    "mimic del tesoriere": {"hp": 60, "ac": 14, "atk": 5, "dmg": (7, 13), "loot": "Denti affilatissimi, saliva adesiva, monete e oggetti"},
    "basilisco di pietrascura": {"hp": 80, "ac": 16, "atk": 6, "dmg": (8, 16), "loot": "Occhi di basilisco, veleno pietrificante, scaglie resistenti"},
    "falena del sogno": {"hp": 40, "ac": 12, "atk": 4, "dmg": (4, 9), "loot": "Polvere onirica, ali luminose, antenne magiche"},
    "verme delle profondità": {"hp": 95, "ac": 15, "atk": 7, "dmg": (9, 17), "loot": "Denti enormi, pelle resistente, ghiandole digestive"},
    "custode runico": {"hp": 75, "ac": 17, "atk": 6, "dmg": (7, 15), "loot": "Rune magiche, armatura incantata, frammenti di metallo antico"},
    "arpia cinerea": {"hp": 48, "ac": 13, "atk": 5, "dmg": (5, 11), "loot": "Piume magiche, artigli, corde intrecciate"},
    "fungo colossale": {"hp": 90, "ac": 13, "atk": 5, "dmg": (8, 14), "loot": "Spore medicinali, cappello fungino gigante, essenza micotica"},
    "cervo spettrale": {"hp": 60, "ac": 15, "atk": 5, "dmg": (6, 12), "loot": "Corna eteree, essenza spirituale, muschio sacro"},
    "lich del sepolcro eterno": {"hp": 110, "ac": 17, "atk": 8, "dmg": (11, 20), "loot": "Grimorio proibito, bastone necromantico, gemme oscure, filatterio"},
    "fenice cinerea": {"hp": 105, "ac": 16, "atk": 7, "dmg": (10, 18), "loot": "Piume della Fenice, cenere rigenerante, uovo incandescente"}
}

def get_enemy_stats(nome_nemico, difficolta="normal"):
    """
    Restituisce le statistiche del nemico scalate per difficoltà.
    """
    nome_pulito = nome_nemico.lower().strip()
    stats = None
    for k, v in BESTIARY_STATS.items():
        if k in nome_pulito or nome_pulito in k:
            stats = v.copy()
            break
            
    if not stats:
        # Statistiche di fallback per nemici generici
        stats = {"hp": 50, "ac": 13, "atk": 4, "dmg": (5, 11), "loot": "Monete d'oro, provviste, oggetti vari"}
        
    # Scalatura difficoltà
    hp = stats["hp"]
    ac = stats["ac"]
    dmg_min, dmg_max = stats["dmg"]
    
    if difficolta == "easy":
        hp = int(hp * 0.8)
        dmg_min = max(1, int(dmg_min * 0.8))
        dmg_max = max(2, int(dmg_max * 0.8))
    elif difficolta == "hard":
        hp = int(hp * 1.2)
        ac += 1
        dmg_min = int(dmg_min * 1.2)
        dmg_max = int(dmg_max * 1.2)
    elif difficolta == "hardcore":
        hp = int(hp * 1.4)
        ac += 2
        dmg_min = int(dmg_min * 1.4)
        dmg_max = int(dmg_max * 1.4)
        
    return {
        "enemy_name": nome_nemico.title(),
        "enemy_hp": hp,
        "enemy_max_hp": hp,
        "enemy_ac": ac,
        "enemy_atk": stats["atk"],
        "enemy_dmg_min": dmg_min,
        "enemy_dmg_max": dmg_max,
        "loot": stats["loot"]
    }

def extract_player_modifiers(personaggio_str):
    """
    Estrae i modificatori di caratteristica e la Classe Armatura dalla stringa del personaggio.
    """
    stats = {"forza": 10, "destrezza": 10, "intelligenza": 10, "costituzione": 10}
    
    if not personaggio_str:
        return {"forza": 0, "destrezza": 0, "intelligenza": 0, "costituzione": 0, "ac": 13}
        
    for line in personaggio_str.split('\n'):
        l = line.strip().upper()
        if 'FORZA:' in l:
            m = re.search(r'FORZA:\s*(\d+)', l)
            if m: stats["forza"] = int(m.group(1))
        elif 'DESTREZZA:' in l:
            m = re.search(r'DESTREZZA:\s*(\d+)', l)
            if m: stats["destrezza"] = int(m.group(1))
        elif 'INTELLIGENZA:' in l:
            m = re.search(r'INTELLIGENZA:\s*(\d+)', l)
            if m: stats["intelligenza"] = int(m.group(1))
        elif 'COSTITUZIONE:' in l:
            m = re.search(r'COSTITUZIONE:\s*(\d+)', l)
            if m: stats["costituzione"] = int(m.group(1))
            
    mods = {
        "forza": (stats["forza"] - 10) // 2,
        "destrezza": (stats["destrezza"] - 10) // 2,
        "intelligenza": (stats["intelligenza"] - 10) // 2,
        "costituzione": (stats["costituzione"] - 10) // 2,
    }
    
    # Calcolo CA base
    ac = 10 + mods["destrezza"] + 2 # Bonus base armatura/difesa da avventuriero
    lower_p = personaggio_str.lower()
    if "scudo" in lower_p:
        ac += 2
    if "armatura completa" in lower_p or "armatura pesante" in lower_p:
        ac += 4
    elif "armatura di maglia" in lower_p or "corazza" in lower_p:
        ac += 2
        
    mods["ac"] = ac
    return mods

def risolvi_turno_combattimento(player_action, game_state):
    """
    Risolve un turno di combattimento in modo matematico senza chiamare le API LLM.
    Restituisce un dizionario compatibile con la risposta di /api/action.
    """
    combat = game_state.get("combat", {})
    if not combat or not combat.get("active"):
        return None
        
    enemy_name = combat.get("enemy_name", "Nemico")
    enemy_hp = combat.get("enemy_hp", 50)
    enemy_max_hp = combat.get("enemy_max_hp", 50)
    enemy_ac = combat.get("enemy_ac", 13)
    enemy_atk = combat.get("enemy_atk", 4)
    enemy_dmg_min = combat.get("enemy_dmg_min", 5)
    enemy_dmg_max = combat.get("enemy_dmg_max", 10)
    
    player_hp = game_state.get("hp", 100)
    player_mods = extract_player_modifiers(game_state.get("personaggio", ""))
    
    action_lower = player_action.lower().strip()
    
    # 1. TENTATIVO DI FUGA
    if any(w in action_lower for w in ["fuggi", "fuga", "scappa", "ritirata", "indietro"]):
        d20_flee = random.randint(1, 20)
        tot_flee = d20_flee + player_mods["destrezza"]
        if tot_flee >= 11 or d20_flee == 20:
            # Fuga riuscita!
            combat["active"] = False
            dm_reply = (
                f"🏃 **FUGA RIUSCITA!**\n\n"
                f"Tiro Fuga ($d20$ + Destrezza): **{d20_flee}** (Totale: {tot_flee} contro 11).\n"
                f"Con uno scatto repentino e sfruttando l'ambiente, riesci a seminare **{enemy_name}** e a ritirarti in una zona sicura, "
                f"uscendo dal combattimento con il fiato corto ma intatto!\n\n"
                f"*(Sei tornato in modalità Esplorazione Narrative)*"
            )
            return _build_response(dm_reply, d20_flee, player_hp, 0, 0, enemy_max_hp, True, enemy_name)
        else:
            # Fuga fallita -> il nemico attacca
            dm_reply_part1 = (
                f"🏃 **TENTATIVO DI FUGA FALLITO!**\n\n"
                f"Tiro Fuga ($d20$ + Destrezza): **{d20_flee}** (Totale: {tot_flee} contro 11).\n"
                f"Tenti di scappare, ma **{enemy_name}** ti sbarra la strada con ferocia non lasciandoti scampo!"
            )
            return _esegui_contrattacco_nemico(dm_reply_part1, d20_flee, game_state, combat, player_mods)

    # 2. AZIONE DI CURA O POZIONE
    if any(w in action_lower for w in ["cura", "pozione", "ampolla", "kit", "erbe", "medico"]):
        cura_base = random.randint(15, 28) + player_mods["costituzione"]
        vecchi_hp = player_hp
        player_hp = min(100, player_hp + cura_base)
        guarigione = player_hp - vecchi_hp
        game_state["hp"] = player_hp
        
        dm_reply_part1 = (
            f"🧪 **USO DI OGGETTO CURATIVO**\n\n"
            f"Rapidamente assumi il rimedio curativo nel bel mezzo dello scontro, recuperando **+{guarigione} HP** "
            f"(Salute attuale: {player_hp}/100)!"
        )
        return _esegui_contrattacco_nemico(dm_reply_part1, 0, game_state, combat, player_mods)

    # 3. ATTACCO O AZIONE DI COMBATTIMENTO STANDARD
    # Determina la statistica di attacco (Forza vs Destrezza vs Intelligenza)
    if any(w in action_lower for w in ["arco", "balestra", "dardo", "pugnale", "mancina", "schiva"]):
        atk_stat = "destrezza"
    elif any(w in action_lower for w in ["bastone", "magia", "incantesimo", "fuoco", "fulmine", "runa"]):
        atk_stat = "intelligenza"
    else:
        atk_stat = "forza"
        
    mod_atk = player_mods[atk_stat]
    d20_player = random.randint(1, 20)
    tot_player = d20_player + mod_atk
    
    dmg_player = 0
    critico = False
    mancato = False
    
    if d20_player == 20:
        critico = True
        dmg_player = (random.randint(6, 14) + max(1, mod_atk)) * 2
    elif d20_player == 1 or tot_player < enemy_ac:
        mancato = True
        dmg_player = 0
    else:
        dmg_player = random.randint(5, 12) + max(1, mod_atk)
        
    if dmg_player > 0:
        enemy_hp = max(0, enemy_hp - dmg_player)
        combat["enemy_hp"] = enemy_hp
        
    # Costruzione testo attacco giocatore
    if critico:
        txt_attacco = (
            f"💥 **COLPO CRITICO DEVASTANTE!** (Tiro $d20$: **20 naturale**!)\n"
            f"Il tuo colpo perfetto trova una fessura vitale nelle difese di **{enemy_name}**, infliggendo la bellezza di **{dmg_player} danni critici**!"
        )
    elif mancato:
        if d20_player == 1:
            txt_attacco = (
                f"❌ **FALLIMENTO CRITICO!** (Tiro $d20$: **1**)\n"
                f"Il tuo attacco manca completamente il bersaglio in un movimento maldestro, lasciandoti scoperto alle difese di **{enemy_name}**!"
            )
        else:
            txt_attacco = (
                f"🛡️ **ATTACCO DEVIATO!** (Tiro $d20$: **{d20_player}** | Totale: {tot_player} vs CA {enemy_ac})\n"
                f"Porti il tuo colpo verso **{enemy_name}**, ma il nemico riesce a schivare o parare l'attacco con la sua robusta corazza."
            )
    else:
        txt_attacco = (
            f"⚔️ **COLPO A SEGNO!** (Tiro $d20$: **{d20_player}** | Totale: {tot_player} vs CA {enemy_ac})\n"
            f"La tua arma colpisce con precisione ed efficacia **{enemy_name}**, causandogli **{dmg_player} danni**!"
        )
        
    # Controlla se il nemico è morto
    if enemy_hp <= 0:
        combat["active"] = False
        loot = combat.get("loot", "Nessun bottino particolare")
        if "BOSS FINALE" in enemy_name.upper() or combat.get("is_boss", False):
            dm_reply = (
                f"⚔️ **TURNO DI COMBATTIMENTO - SCONTRO EPICO** ⚔️\n\n"
                f"{txt_attacco}\n\n"
                f"👑🏆 **VITTORIA FINALE DEL GIOCO! HAI SCONFITTO IL BOSS FINALE!** 🏆👑\n"
                f"Con un colpo leggendario che risuonerà nei secoli, **{enemy_name}** emette il suo ultimo respiro e crolla al suolo definitivamente sconfitto!\n\n"
                f"La maledizione che gravava su queste terre si spezza e la luce torna a splendere sul mondo di Morpheus Genesis. HAI VINTO LA CAMPAGNA!\n\n"
                f"💎 **Bottino Supremo Ottenuto:** {loot}\n\n"
                f"*(La partita è stata completata con successo! Trionfo Eroico!)*"
            )
        else:
            dm_reply = (
                f"⚔️ **TURNO DI COMBATTIMENTO** ⚔️\n\n"
                f"{txt_attacco}\n\n"
                f"🎉 **VITTORIA SCHIACCIANTE!**\n"
                f"Con quest'ultimo colpo fatale, **{enemy_name}** emette un ultimo ruggito e crolla a terra esanime! Hai vinto la battaglia!\n\n"
                f"💎 **Bottino Ottenuto:** {loot}\n\n"
                f"*(Il combattimento è terminato. Torni in modalità Esplorazione)*"
            )
        return _build_response(dm_reply, d20_player, game_state["hp"], 0, 0, enemy_max_hp, True, enemy_name)
        
    # Se il nemico è ancora vivo -> Contrattacco
    dm_reply_part1 = f"⚔️ **TURNO DI COMBATTIMENTO vs {enemy_name.upper()}** ⚔️\n\n{txt_attacco}"
    return _esegui_contrattacco_nemico(dm_reply_part1, d20_player, game_state, combat, player_mods)


def _esegui_contrattacco_nemico(txt_precedente, tiro_dado_giocatore, game_state, combat, player_mods):
    """
    Gestisce l'attacco del nemico contro il giocatore.
    """
    enemy_name = combat["enemy_name"]
    enemy_hp = combat["enemy_hp"]
    enemy_max_hp = combat["enemy_max_hp"]
    enemy_atk = combat.get("enemy_atk", 4)
    enemy_dmg_min = combat.get("enemy_dmg_min", 5)
    enemy_dmg_max = combat.get("enemy_dmg_max", 10)
    
    player_ac = player_mods["ac"]
    player_hp = game_state.get("hp", 100)
    
    d20_enemy = random.randint(1, 20)
    tot_enemy = d20_enemy + enemy_atk
    
    danni_subiti = 0
    if d20_enemy == 20:
        danni_subiti = int((random.randint(enemy_dmg_min, enemy_dmg_max)) * 1.5)
        txt_nemico = (
            f"🔥 **IL NEMICO TI INFLIGGE UN COLPO CRITICO!** (Tiro $d20$: **20** vs CA {player_ac})\n"
            f"**{enemy_name}** contrattacca con una ferocia inaudita travolgendo le tue difese e infliggendoti **{danni_subiti} danni**!"
        )
    elif d20_enemy != 1 and tot_enemy >= player_ac:
        danni_subiti = random.randint(enemy_dmg_min, enemy_dmg_max)
        txt_nemico = (
            f"🩸 **IL NEMICO COLPISCE!** (Tiro $d20$: **{d20_enemy}** | Totale: {tot_enemy} vs CA {player_ac})\n"
            f"**{enemy_name}** scatta al contrattacco e ti ferisce, causandoti **{danni_subiti} danni**!"
        )
    else:
        danni_subiti = 0
        txt_nemico = (
            f"🛡️ **CONTRATTACCO PARATO!** (Tiro $d20$ nemico: **{d20_enemy}** | Totale: {tot_enemy} vs CA {player_ac})\n"
            f"**{enemy_name}** tenta di colpirti, ma riesci agilmente a schivare o bloccare l'attacco con il tuo equipaggiamento senza subire danni!"
        )
        
    player_hp = max(0, player_hp - danni_subiti)
    game_state["hp"] = player_hp
    
    # Se il giocatore muore
    if player_hp <= 0:
        combat["active"] = False
        txt_nemico += "\n\n💀 **SEI STATO SCONFITTO...** La tua forza ti abbandona e cadi sul campo di battaglia."
        
    dm_reply_full = (
        f"{txt_precedente}\n\n"
        f"--- CONTRATTACCO NEMICO ---\n"
        f"{txt_nemico}\n\n"
        f"📊 **Stato Scontro:** Tuoi HP: **{player_hp}/100** | HP **{enemy_name}**: **{enemy_hp}/{enemy_max_hp}**"
    )
    
    return _build_response(dm_reply_full, tiro_dado_giocatore, player_hp, danni_subiti, enemy_hp, enemy_max_hp, not combat["active"], enemy_name)


def _build_response(dm_reply, tiro_dado, player_hp, danni_subiti, enemy_hp, enemy_max_hp, combat_ended, enemy_name="Nemico"):
    return {
        "success": True,
        "dm_reply": dm_reply,
        "tiro_dado": tiro_dado,
        "hp": player_hp,
        "danni_subiti": danni_subiti,
        "combat": {
            "active": not combat_ended,
            "enemy_name": enemy_name,
            "enemy_hp": enemy_hp,
            "enemy_max_hp": enemy_max_hp
        }
    }
