import random
import re

# bestiario - stats dei nemici conosciuti
BESTIARY_STATS = {
    "lupo delle nebbie": {"hp": 43, "ac": 13, "atk": 4, "dmg": (5, 10), "loot": "Pelle argentata, zanne affilate"},
    "ragno di cristallo": {"hp": 55, "ac": 14, "atk": 5, "dmg": (6, 12), "loot": "Filo di cristallo, ghiandola velenifera, frammenti di carapace"},
    "golem di basalto": {"hp": 88, "ac": 16, "atk": 6, "dmg": (8, 16), "loot": "Nucleo elementale, frammenti runici, minerali rari"},
    "sirena abissale": {"hp": 50, "ac": 14, "atk": 5, "dmg": (6, 14), "loot": "Perla incantata, squame luminose, conchiglia melodica"},
    "idra delle paludi": {"hp": 98, "ac": 15, "atk": 7, "dmg": (10, 18), "loot": "Sangue rigenerante, squame di drago minore, denti velenosi, sacca biliare"},
    "spettro del giuramento": {"hp": 65, "ac": 15, "atk": 6, "dmg": (7, 14), "loot": "Essenza spettrale, frammenti di armatura eterea"},
    "divoratore d'ombre": {"hp": 72, "ac": 16, "atk": 6, "dmg": (8, 15), "loot": "Essenza d'ombra, cristallo oscuro, residui magici"},
    "drago delle tempeste": {"hp": 122, "ac": 18, "atk": 8, "dmg": (12, 22), "loot": "Scaglie draconiche, artigli, cuore del fulmine, tesoro accumulato, squama regale"},
    "mimic del tesoriere": {"hp": 58, "ac": 14, "atk": 5, "dmg": (7, 13), "loot": "Denti affilatissimi, saliva adesiva, monete e oggetti"},
    "basilisco di pietrascura": {"hp": 78, "ac": 16, "atk": 6, "dmg": (8, 16), "loot": "Occhi di basilisco, veleno pietrificante, scaglie resistenti"},
    "falena del sogno": {"hp": 38, "ac": 12, "atk": 4, "dmg": (4, 9), "loot": "Polvere onirica, ali luminose"},
    "verme delle profondità": {"hp": 95, "ac": 15, "atk": 7, "dmg": (9, 17), "loot": "Denti enormi, pelle resistente, ghiandole digestive"},
    "custode runico": {"hp": 76, "ac": 17, "atk": 6, "dmg": (7, 15), "loot": "Rune magiche, armatura incantata, frammenti di metallo antico"},
    "arpia cinerea": {"hp": 47, "ac": 13, "atk": 5, "dmg": (5, 11), "loot": "Piume magiche, artigli"},
    "fungo colossale": {"hp": 90, "ac": 13, "atk": 5, "dmg": (8, 14), "loot": "Spore medicinali, cappello fungino gigante, essenza micotica"},
    "cervo spettrale": {"hp": 62, "ac": 15, "atk": 5, "dmg": (6, 12), "loot": "Corna eteree, essenza spirituale, muschio sacro"},
    "lich del sepolcro eterno": {"hp": 112, "ac": 17, "atk": 8, "dmg": (11, 20), "loot": "Grimorio proibito, bastone necromantico, gemme oscure, filatterio"},
    "fenice cinerea": {"hp": 103, "ac": 16, "atk": 7, "dmg": (10, 18), "loot": "Piume della Fenice, cenere rigenerante, uovo incandescente"},  # nerfato da 110hp
    # "scarabeo di cenere": {"hp": 32, "ac": 11, "atk": 3, "dmg": (3, 7), "loot": "Guscio bruciato"},  # troppo debole, tolto
}

# oggetti e le loro stats per il combattimento
ITEMS_DB = {
    # armi - probabilità % di colpire
    "arco lungo": {"tipo": "attacco", "efficacia": 75},
    "spada corta": {"tipo": "attacco", "efficacia": 80},
    "coltello da caccia": {"tipo": "attacco", "efficacia": 85},
    "mazza ferrata": {"tipo": "attacco", "efficacia": 70},
    "due pugnali": {"tipo": "attacco", "efficacia": 85},
    "ascia bipenne": {"tipo": "attacco", "efficacia": 65},
    "martello da guerra": {"tipo": "attacco", "efficacia": 75},
    "bastone runico": {"tipo": "attacco", "efficacia": 90},
    "bastone di quercia": {"tipo": "attacco", "efficacia": 70},
    "falcetto rituale": {"tipo": "attacco", "efficacia": 80},

    # difese - % passiva di parare
    "scudo sacro": {"tipo": "difesa", "efficacia": 60},
    "armatura di maglia": {"tipo": "difesa", "efficacia": 50},
    "mantello scuro": {"tipo": "difesa", "efficacia": 40},
    "mantello incantato": {"tipo": "difesa", "efficacia": 50},
    "mantello mimetico": {"tipo": "difesa", "efficacia": 45},
    "scudo pesante": {"tipo": "difesa", "efficacia": 70},
    "armatura completa": {"tipo": "difesa", "efficacia": 75},
    "bracciali rinforzati": {"tipo": "difesa", "efficacia": 35},
    "amleto d'ombra del cacciatore": {"tipo": "difesa", "efficacia": 55},

    # cure - HP ripristinati (riutilizzabili)
    "kit medico": {"tipo": "cura", "efficacia": 40},
    "pozione di rigenerazione elfica": {"tipo": "cura", "efficacia": 50},
    "pozione di mana": {"tipo": "cura", "efficacia": 20},
    "ampolla d'acqua santa": {"tipo": "cura", "efficacia": 30},
    "razioni da viaggio": {"tipo": "cura", "efficacia": 15},
    "erbe medicinali": {"tipo": "cura", "efficacia": 35},
    "fiasca di forte liquore": {"tipo": "cura", "efficacia": 25},
}


def get_enemy_stats(nome_nemico, difficolta="normal"):
    # cerca il nemico nel bestiario, se non lo trova usa stats generiche
    nome_pulito = nome_nemico.lower().strip()
    stats = None
    for k, v in BESTIARY_STATS.items():
        if k in nome_pulito or nome_pulito in k:
            stats = v.copy()
            break

    if not stats:
        stats = {"hp": 50, "ac": 13, "atk": 4, "dmg": (5, 11), "loot": "Monete d'oro, provviste, oggetti vari"}

    hp = stats["hp"]
    ac = stats["ac"]
    dmg_min, dmg_max = stats["dmg"]

    if difficolta == "easy":
        hp = int(hp * 0.8)
        dmg_min = max(1, int(dmg_min * 0.8))
        dmg_max = max(2, int(dmg_max * 0.8))
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
    # parsing delle stats dalla scheda personaggio (forza, destrezza ecc)
    # e calcolo della classe armatura
    if not personaggio_str:
        return {"forza": 0, "destrezza": 0, "intelligenza": 0, "costituzione": 0, "ac": 13}

    stats = {}
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

    # fallback se manca qualche stat nella scheda
    stats.setdefault("forza", 10)
    stats.setdefault("destrezza", 10)
    stats.setdefault("intelligenza", 10)
    stats.setdefault("costituzione", 10)

    mods = {
        "forza": (stats["forza"] - 10) // 2,
        "destrezza": (stats["destrezza"] - 10) // 2,
        "intelligenza": (stats["intelligenza"] - 10) // 2,
        "costituzione": (stats["costituzione"] - 10) // 2,
    }

    ac = 10 + mods["destrezza"] + 2  # bonus base da avventuriero
    lower_p = personaggio_str.lower()
    if "scudo" in lower_p:
        ac += 2
    if "armatura completa" in lower_p or "armatura pesante" in lower_p:
        ac += 4
    elif "armatura di maglia" in lower_p or "corazza" in lower_p:
        ac += 2

    mods["ac"] = ac

    # trova la difesa migliore nell'inventario
    dif_nome = None
    dif_pct = 0
    for item_name, item_data in ITEMS_DB.items():
        if item_data["tipo"] == "difesa" and item_name in lower_p:
            if item_data["efficacia"] > dif_pct:
                dif_pct = item_data["efficacia"]
                dif_nome = item_name

    mods["best_defense_name"] = dif_nome
    mods["best_defense_pct"] = dif_pct

    return mods


def risolvi_turno_combattimento(player_action, game_state):
    """
    Risolve un turno di combattimento senza chiamare l'LLM.
    Torna un dict compatibile con /api/action oppure None se non siamo in combat.
    """
    combat = game_state.get("combat", {})
    if not combat or not combat.get("active"):
        return None

    enemy_name = combat["enemy_name"]
    enemy_hp = combat["enemy_hp"]
    enemy_max_hp = combat["enemy_max_hp"]
    enemy_ac = combat.get("enemy_ac", 13)   # a volte manca nei vecchi save
    enemy_atk = combat["enemy_atk"]
    enemy_dmg_min, enemy_dmg_max = combat["enemy_dmg_min"], combat["enemy_dmg_max"]

    hp = game_state.get("hp", 100)
    player_mods = extract_player_modifiers(game_state.get("personaggio", ""))

    action_lower = player_action.lower().strip()
    difficolta = game_state.get("difficolta", "normal")

    # fuga
    if any(w in action_lower for w in ["fuggi", "fuga", "scappa", "ritirata", "indietro"]):
        soglia = 11
        if difficolta == "easy": soglia = 7
        elif difficolta == "hardcore": soglia = 15

        dado = random.randint(1, 20)
        tot = dado + player_mods["destrezza"]
        if tot >= soglia or dado == 20:
            combat["active"] = False
            testo = (
                f"🏃 **FUGA RIUSCITA!**\n\n"
                f"Tiro Fuga ($d20$ + Destrezza): **{dado}** (Totale: {tot} contro {soglia}).\n"
                f"Con uno scatto repentino e sfruttando l'ambiente, riesci a seminare **{enemy_name}** e a ritirarti in una zona sicura, "
                f"uscendo dal combattimento con il fiato corto ma intatto!\n\n"
                f"*(Sei tornato in modalità Esplorazione Narrative)*"
            )
            return _crea_risposta(testo, dado, hp, 0, 0, enemy_max_hp, True, enemy_name, "d20")
        else:
            parte1 = (
                f"🏃 **TENTATIVO DI FUGA FALLITO!**\n\n"
                f"Tiro Fuga ($d20$ + Destrezza): **{dado}** (Totale: {tot} contro {soglia}).\n"
                f"Tenti di scappare, ma **{enemy_name}** ti sbarra la strada con ferocia non lasciandoti scampo!"
            )
            return _contrattacco_nemico(parte1, dado, game_state, combat, player_mods, "d20")

    # se usa una pozione o oggetto curativo
    personaggio_lower = game_state.get("personaggio", "").lower()
    obj_usato = None
    obj_data = None
    for item_name, item_data in ITEMS_DB.items():
        if item_name in action_lower and item_name in personaggio_lower:
            obj_usato = item_name
            obj_data = item_data
            break

    if obj_data and obj_data["tipo"] == "cura":
        cura = obj_data["efficacia"]
        if difficolta == "easy": cura = int(cura * 1.5)
        elif difficolta == "hardcore": cura = int(cura * 0.5)

        prima = hp
        hp = min(100, hp + cura)
        guariti = hp - prima
        game_state["hp"] = hp

        parte1 = (
            f"🧪 **USO DI {obj_usato.upper()}**\n\n"
            f"Rapidamente usi il tuo oggetto curativo nel bel mezzo dello scontro, recuperando **+{guariti} HP** "
            f"(Salute attuale: {hp}/100)!"
        )
        return _contrattacco_nemico(parte1, 0, game_state, combat, player_mods, "none")
    elif any(w in action_lower for w in ["cura", "pozione", "ampolla", "kit", "erbe", "medico"]):
        cura = random.randint(15, 28) + player_mods["costituzione"]
        if difficolta == "easy": cura = int(cura * 1.5)
        elif difficolta == "hardcore": cura = int(cura * 0.5)

        prima = hp
        hp = min(100, hp + cura)
        guariti = hp - prima
        game_state["hp"] = hp

        parte1 = (
            f"🧪 **USO DI OGGETTO CURATIVO**\n\n"
            f"Rapidamente assumi il rimedio curativo nel bel mezzo dello scontro, recuperando **+{guariti} HP** "
            f"(Salute attuale: {hp}/100)!"
        )
        return _contrattacco_nemico(parte1, 0, game_state, combat, player_mods, "none")

    # altrimenti è un attacco
    if any(w in action_lower for w in ["arco", "balestra", "dardo", "pugnale", "mancina", "schiva"]):
        stat_usata = "destrezza"
    elif any(w in action_lower for w in ["bastone", "magia", "incantesimo", "fuoco", "fulmine", "runa"]):
        stat_usata = "intelligenza"
    else:
        stat_usata = "forza"

    mod = player_mods[stat_usata]

    dmg = 0
    crit = False
    miss = False
    roll = 0

    arma_txt = obj_usato.title() if (obj_data and obj_data["tipo"] == "attacco") else "Il tuo attacco"

    d20 = random.randint(1, 20)
    tot = d20 + mod
    roll = d20

    if d20 == 20:
        crit = True
        dmg = (random.randint(6, 14) + max(1, mod)) * 2
    elif d20 == 1 or tot < enemy_ac:
        miss = True
    else:
        dmg = random.randint(5, 12) + max(1, mod)

    if dmg > 0:
        enemy_hp = max(0, enemy_hp - dmg)
        combat["enemy_hp"] = enemy_hp

    # costruzione testo attacco
    if crit:
        txt_atk = (
            f"💥 **COLPO CRITICO DEVASTANTE!** (d20: **20 naturale**!)\n"
            f"Il tuo colpo perfetto con {arma_txt} trova una fessura vitale nelle difese di **{enemy_name}**, infliggendo la bellezza di **{dmg} danni critici**!"
        )
    elif miss:
        if d20 == 1:
            txt_atk = (
                f"❌ **FALLIMENTO CRITICO!** (d20: **1**)\n"
                f"Il tuo attacco con {arma_txt} manca completamente il bersaglio in un movimento maldestro, lasciandoti scoperto alle difese di **{enemy_name}**!"
            )
        else:
            txt_atk = (
                f"🛡️ **ATTACCO DEVIATO!** (d20: **{d20}**, tot {tot} vs CA {enemy_ac})\n"
                f"Porti il tuo colpo con {arma_txt} verso **{enemy_name}**, ma il nemico riesce a schivare o parare l'attacco."
            )
    else:
        txt_atk = (
            f"⚔️ **COLPO A SEGNO!** (d20: {d20}+{mod} = {tot} vs CA {enemy_ac})\n"
            f"{arma_txt} colpisce con precisione ed efficacia **{enemy_name}**, causandogli **{dmg} danni**!"
        )

    if enemy_hp <= 0:
        combat["active"] = False
        if "BOSS FINALE" in enemy_name.upper() or combat.get("is_boss", False):
            testo = (
                f"⚔️ **TURNO DI COMBATTIMENTO - SCONTRO EPICO** ⚔️\n\n"
                f"{txt_atk}\n\n"
                f"👑🏆 **VITTORIA FINALE DEL GIOCO! HAI SCONFITTO IL BOSS FINALE!** 🏆👑\n"
                f"Con un colpo leggendario che risuonerà nei secoli, **{enemy_name}** emette il suo ultimo respiro e crolla al suolo definitivamente sconfitto!\n\n"
                f"La maledizione che gravava su queste terre si spezza e la luce torna a splendere sul mondo di Morpheus Genesis. HAI VINTO LA CAMPAGNA!\n\n"
                f"*(La partita è stata completata con successo! Trionfo Eroico!)*"
            )
        else:
            testo = (
                f"⚔️ **TURNO DI COMBATTIMENTO** ⚔️\n\n"
                f"{txt_atk}\n\n"
                f"🎉 **VITTORIA SCHIACCIANTE!**\n"
                f"Con quest'ultimo colpo fatale, **{enemy_name}** emette un ultimo ruggito e crolla a terra esanime! Hai vinto la battaglia!\n\n"
                f"*(Il combattimento è terminato. Torni in modalità Esplorazione)*"
            )
        return _crea_risposta(testo, roll, game_state["hp"], 0, 0, enemy_max_hp, True, enemy_name, "d20")

    # nemico ancora vivo, contrattacca
    parte1 = f"⚔️ **TURNO DI COMBATTIMENTO vs {enemy_name.upper()}** ⚔️\n\n{txt_atk}"
    return _contrattacco_nemico(parte1, roll, game_state, combat, player_mods, "d20")


def _contrattacco_nemico(txt_prima, roll_giocatore, game_state, combat, player_mods, tipo_dado="d20"):
    # gestisce la fase di attacco del nemico dopo l'azione del player
    enemy_name = combat["enemy_name"]
    enemy_hp = combat["enemy_hp"]
    enemy_max_hp = combat["enemy_max_hp"]
    enemy_atk = combat.get("enemy_atk", 4)
    enemy_dmg_min = combat.get("enemy_dmg_min", 5)
    enemy_dmg_max = combat.get("enemy_dmg_max", 10)

    ca_player = player_mods["ac"]
    hp = game_state.get("hp", 100)

    d20 = random.randint(1, 20)
    tot = d20 + enemy_atk

    danni = 0
    parato = False

    dif_nome = player_mods.get("best_defense_name")
    dif_pct = player_mods.get("best_defense_pct", 0)

    # check difesa passiva
    if dif_nome and dif_pct > 0:
        d100 = random.randint(1, 100)
        if d100 <= dif_pct:
            parato = True
            danni = 0
            txt_nem = (
                f"🛡️ **DIFESA AUTOMATICA RIUSCITA!** (d100: {d100}% vs {dif_pct}% di {dif_nome.title()})\n"
                f"**{enemy_name}** tenta di colpirti, ma il tuo **{dif_nome}** assorbe o devia completamente l'attacco, lasciandoti illeso!"
            )

    if not parato:
        if d20 == 20:
            danni = int((random.randint(enemy_dmg_min, enemy_dmg_max)) * 1.5)
            txt_nem = (
                f"🔥 **IL NEMICO TI INFLIGGE UN COLPO CRITICO!** (d20: **20** vs CA {ca_player})\n"
                f"**{enemy_name}** contrattacca con una ferocia inaudita travolgendo le tue difese e infliggendoti **{danni} danni**!"
            )
        elif d20 != 1 and tot >= ca_player:
            danni = random.randint(enemy_dmg_min, enemy_dmg_max)
            txt_nem = (
                f"🩸 **IL NEMICO COLPISCE!** (d20: {d20}, tot {tot} vs CA {ca_player})\n"
                f"**{enemy_name}** scatta al contrattacco e ti ferisce, causandoti **{danni} danni**!"
            )
        else:
            danni = 0
            # TODO: aggiungere varianti testuali casuali per non ripetere sempre la stessa frase
            txt_nem = (
                f"Il contrattacco di **{enemy_name}** va a vuoto! "
                f"(d20 nemico: {d20}, tot {tot} — la tua CA {ca_player} regge)"
            )

    hp = max(0, hp - danni)
    game_state["hp"] = hp

    if hp <= 0:
        combat["active"] = False
        txt_nem += "\n\n💀 **SEI STATO SCONFITTO...** La tua forza ti abbandona e cadi sul campo di battaglia."

    testo_completo = (
        f"{txt_prima}\n\n"
        f"--- CONTRATTACCO NEMICO ---\n"
        f"{txt_nem}\n\n"
        f"📊 **Stato Scontro:** Tuoi HP: **{hp}/100** | HP **{enemy_name}**: **{enemy_hp}/{enemy_max_hp}**"
    )

    return _crea_risposta(testo_completo, roll_giocatore, hp, danni, enemy_hp, enemy_max_hp, not combat["active"], enemy_name, tipo_dado)


def _crea_risposta(testo, roll, hp, danni, enemy_hp, enemy_max_hp, finito, enemy_name="Nemico", tipo_dado="d20"):
    # FIXME: forse dovrei pulire eventuali tag [DANNI:] residui qui dentro
    return {
        "success": True,
        "dm_reply": testo,
        "tiro_dado": roll,
        "tipo_dado": tipo_dado,
        "hp": hp,
        "danni_subiti": danni,
        "combat": {
            "active": not finito,
            "enemy_name": enemy_name,
            "enemy_hp": enemy_hp,
            "enemy_max_hp": enemy_max_hp
        }
    }
