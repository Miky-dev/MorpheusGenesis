import random
import re
import textwrap
import os
import json
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# ==========================================
# CONFIGURAZIONE
# ==========================================
MAP_CONFIG = {
    "small": {
        "tot_ambientazioni": 4,
        "tot_npc": 4,
        "tot_cattivi": 2,
        "nome_tag": "Mappa Compatta (Avventura Breve)"
    },
    "medium": {
        "tot_ambientazioni": 6,
        "tot_npc": 6,
        "tot_cattivi": 3,
        "nome_tag": "Mappa Standard (Campagna Bilanciata)"
    },
    "large": {
        "tot_ambientazioni": 10,
        "tot_npc": 10,
        "tot_cattivi": 5,
        "nome_tag": "Mappa Estesa (Odissea Epica)"
    }
}

DIREZIONI_MAPPA = [
    "CENTRO", "NORD", "EST", "OVEST", "SUD",
    "NORD-EST", "NORD-OVEST", "SUD-EST", "SUD-OVEST", "PROFONDITÀ"
]

_model_name = os.environ.get("MODEL_NAME", "gpt-4o-mini")

# ==========================================
# MODELLI PYDANTIC PER OUTPUT STRUTTURATI
# ==========================================

class CartografoOutput(BaseModel):
    ambientazioni_selezionate: list[str] = Field(description="Lista esatta dei testi delle ambientazioni selezionate dal dataset fornito.")
    mappa_testuale: str = Field(description="Testo con la mappa formattata riga per riga.")
    tot_ambientazioni: int = Field(description="Numero totale di ambientazioni selezionate.")
    nodi: list[str] = Field(description="Lista delle singole righe formattate come '[DIREZIONE]: Descrizione'. Il primo nodo deve avere ' <-- (Tu sei qui: Punto di Partenza)'.")

class NodoNemico(BaseModel):
    indice_citta: int = Field(description="L'indice del nodo (da 0 a N-1).")
    nemico: str = Field(description="Testo originale del nemico o boss.")
    is_boss: bool = Field(description="True se questo è il boss finale (deve esserlo all'ultimo indice), False altrimenti.")

class CastingOutput(BaseModel):
    npc_selezionati: list[str] = Field(description="Lista dei testi completi degli NPC selezionati.")
    creature_selezionate: list[str] = Field(description="Lista dei testi completi dei nemici selezionati.")
    mappa_arricchita: str = Field(description="Testo completo della mappa con nodi e personaggi assegnati.")
    tot_npc: int = Field(description="Numero totale di NPC.")
    tot_cattivi: int = Field(description="Numero totale di creature/nemici.")
    boss_finale_str: str = Field(description="Testo descrittivo del boss finale formattato. Deve iniziare con [NomeBoss].")
    nome_boss: str = Field(description="Il nome esatto del boss finale estratto (senza parentesi quadre).")
    oggetti_scelti: list[str] = Field(description="Lista dei testi degli oggetti scelti.")
    citta_con_nemici_list: list[NodoNemico] = Field(description="Lista di dizionari che mappano le città ai nemici/boss.")

# ==========================================
# AGENTI AGNO
# ==========================================

class CartografoAgent:
    """Agente Cartografo basato su Agno - crea la mappa e seleziona le ambientazioni dal RAG."""
    def __init__(self, ambientazioni_rag):
        self.ambientazioni_rag = ambientazioni_rag
        self.agent = Agent(
            name="Cartografo Agent",
            model=OpenAIChat(id=_model_name),
            instructions=[
                "Sei il Cartografo. Il tuo compito è definire la topologia della mappa.",
                "Seleziona le ambientazioni dal dataset fornito e organizza le località.",
                "Devi restituire un oggetto JSON strettamente aderente allo schema richiesto.",
                f"Usa le seguenti direzioni nell'ordine per i nodi: {', '.join(DIREZIONI_MAPPA)}."
            ],
            output_schema=CartografoOutput
        )

    def esegui(self, map_size: str, tema_desc: str) -> dict:
        print("🗺️ [Agente 1: Cartografo] Analisi topologia e generazione mappa in corso con Agno...")
        config = MAP_CONFIG.get(map_size, MAP_CONFIG["medium"])
        tot_amb = min(config["tot_ambientazioni"], len(self.ambientazioni_rag))
        
        prompt = (
            f"Crea una mappa di dimensione '{map_size}' con ESATTAMENTE {tot_amb} località.\n"
            f"Scegli {tot_amb} ambientazioni dal seguente dataset (copia il testo in modo esatto):\n"
            f"{chr(10).join(self.ambientazioni_rag)}\n\n"
            f"Assicurati che 'tot_ambientazioni' sia esattamente {tot_amb} e genera la lista di 'nodi'."
        )
        
        try:
            response = self.agent.run(prompt)
            return response.content.model_dump()
        except Exception as e:
            print(f"⚠️ Errore Agno Cartografo: {e}. Fallback su metodo deterministico.")
            ambient_scelte = random.sample(self.ambientazioni_rag, tot_amb) if tot_amb > 0 else ["Lande Sconosciute"]
            nodi_mappa = []
            for i in range(len(ambient_scelte)):
                dir_label = DIREZIONI_MAPPA[i] if i < len(DIREZIONI_MAPPA) else f"ZONA-{i+1}"
                riga = f"[{dir_label}]: {ambient_scelte[i].strip()}"
                if i == 0:
                    riga += " <-- (Tu sei qui: Punto di Partenza)"
                nodi_mappa.append(riga)
            return {
                "ambientazioni_selezionate": ambient_scelte,
                "mappa_testuale": "\n".join(nodi_mappa),
                "tot_ambientazioni": len(ambient_scelte),
                "nodi": nodi_mappa
            }


class CastingDirectorAgent:
    """Direttore del Casting basato su Agno - assegna NPC, nemici, boss finale e oggetti."""
    def __init__(self, personaggi_rag, creature_rag, oggetti_rag=None):
        self.personaggi_rag = personaggi_rag
        self.creature_rag = creature_rag
        self.oggetti_rag = oggetti_rag or []
        self.agent = Agent(
            name="Casting Director Agent",
            model=OpenAIChat(id=_model_name),
            instructions=[
                "Sei il Casting Director. Assegna NPC e nemici alle località create dal Cartografo.",
                "Eleggi il boss finale nella zona più remota (l'ultima della mappa).",
                "Devi restituire un oggetto JSON aderente allo schema.",
                "Per ogni nodo della mappa, aggiungi: ' <-- (🧑 NPC residente: [Nome] | ⚔️ Pericolo: [Nome])' oppure '... | 🌿 Zona Sicura)'.",
                "Il boss finale va SEMPRE all'ultimo nodo (il più alto indice) e l'etichetta diventa '👑 BOSS FINALE: [Nome]'.",
                "Garantisci MINIMO 1 NPC per città, e Nemici in ALMENO LA METÀ del numero totale di città."
            ],
            output_schema=CastingOutput
        )

    def esegui(self, map_size: str, cartografo_output: dict, tema_desc: str) -> dict:
        print("🎭 [Agente 2: Direttore del Casting] Assegnazione tramite Agno...")
        config = MAP_CONFIG.get(map_size, MAP_CONFIG["medium"])
        tot_citta = cartografo_output["tot_ambientazioni"]
        
        tot_npc = min(max(config["tot_npc"], tot_citta), len(self.personaggi_rag))
        tot_cattivi_target = max(config["tot_cattivi"], (tot_citta + 1) // 2)
        tot_cattivi = min(tot_cattivi_target, len(self.creature_rag))
        tot_oggetti = min(3, len(self.oggetti_rag)) if self.oggetti_rag else 2
        
        prompt = (
            f"Popola questa mappa (che ha {tot_citta} località):\n"
            f"{cartografo_output['mappa_testuale']}\n\n"
            f"Scegli ESATTAMENTE {tot_npc} NPC dal dataset:\n"
            f"{chr(10).join(self.personaggi_rag)}\n\n"
            f"Scegli ESATTAMENTE {tot_cattivi} Nemici dal dataset:\n"
            f"{chr(10).join(self.creature_rag)}\n\n"
            f"Scegli {tot_oggetti} Oggetti dal dataset:\n"
            f"{chr(10).join(self.oggetti_rag) if self.oggetti_rag else 'Usa oggetti base (Pozione, Amleto)'}\n\n"
            f"Costruisci 'citta_con_nemici_list' mappando l'indice (0 a {tot_citta - 1}) ai nemici scelti. "
            f"Assicurati che l'ultimo indice ({tot_citta - 1}) abbia 'is_boss'=True."
        )
        
        try:
            response = self.agent.run(prompt)
            data = response.content.model_dump()
            data["citta_con_nemici"] = {
                item["indice_citta"]: (item["nemico"], item["is_boss"]) 
                for item in data["citta_con_nemici_list"]
            }
            return data
        except Exception as e:
            print(f"⚠️ Errore Agno Casting Director: {e}. Fallback su metodo deterministico.")
            npc_scelti = random.sample(self.personaggi_rag, tot_npc) if tot_npc > 0 else ["Viandante Misterioso"]
            creature_scelte = random.sample(self.creature_rag, tot_cattivi) if tot_cattivi > 0 else ["Ombra Minacciosa"]
            boss_grezzo = creature_scelte[0]
            match_nome = re.search(r'^\[(.*?)\]', boss_grezzo)
            nome_boss = match_nome.group(1).strip() if match_nome else boss_grezzo.split('\n')[0].replace('[', '').replace(']', '').strip()
            desc_boss = re.sub(r'^\[.*?\]\s*', '', boss_grezzo).strip()
            boss_finale_str = (f"[{nome_boss}]\n👑 BOSS FINALE E OBIETTIVO SUPREMO DELLA CAMPAGNA 👑\n"
                               f"Per completare e vincere definitivamente il gioco, devi raggiungere la sua tana e sconfiggere questo avversario mortale in combattimento!\n\n{desc_boss}")
            oggetti_scelti = random.sample(self.oggetti_rag, tot_oggetti) if self.oggetti_rag else ["[Pozione Elfica]", "[Amleto d'Ombra]"]
            nodi_arricchiti = []
            citta_con_nemici = {tot_citta - 1: (creature_scelte[0], True)}
            indici_disponibili = [idx for idx in range(1, tot_citta - 1)]
            for idx_nem, cr in enumerate(creature_scelte[1:], start=1):
                if indici_disponibili:
                    idx_citta = indici_disponibili.pop(0 if idx_nem % 2 == 1 else -1)
                    citta_con_nemici[idx_citta] = (cr, False)
                else:
                    citta_con_nemici[idx_nem % tot_citta] = (cr, False)
            for i in range(len(cartografo_output["nodi"])):
                riga = cartografo_output["nodi"][i]
                npc_i = npc_scelti[i % len(npc_scelti)]
                nome_npc = npc_i.split('\n')[0].replace('[', '').replace(']', '').strip()
                if i in citta_con_nemici:
                    nem_grezzo, is_boss = citta_con_nemici[i]
                    nome_nem = nem_grezzo.split('\n')[0].replace('[', '').replace(']', '').strip()
                    etichetta = f"👑 BOSS FINALE: {nome_nem}" if is_boss else f"Pericolo: {nome_nem}"
                    riga += f" <-- (🧑 NPC residente: {nome_npc} | ⚔️ {etichetta})"
                else:
                    riga += f" <-- (🧑 NPC residente: {nome_npc} | 🌿 Zona Sicura)"
                nodi_arricchiti.append("    " + riga if i > 0 else riga)
            
            return {
                "npc_selezionati": npc_scelti,
                "creature_selezionate": creature_scelte,
                "mappa_arricchita": "\n".join(nodi_arricchiti),
                "tot_npc": len(npc_scelti),
                "tot_cattivi": len(creature_scelte),
                "boss_finale_str": boss_finale_str,
                "nome_boss": nome_boss,
                "oggetti_scelti": oggetti_scelti,
                "citta_con_nemici": citta_con_nemici
            }


class LoreMasterAgent:
    """Maestro di Lore - sintetizza mappa e casting, genera il system prompt e il prologo (tramite Agno)."""
    def __init__(self):
        self.agent = Agent(
            name="Lore Master Agent",
            model=OpenAIChat(id=os.environ.get("STORY_MODEL_NAME", os.environ.get("MODEL_NAME", "gpt-4o"))),
            instructions=[
                "Sei il Lore Master. Il tuo compito è narrare l'inizio dell'avventura.",
                "Genera il prologo racchiuso nel tag [PERGAMENA] e l'azione iniziale in [AZIONE_INIZIALE].",
                "Non inventare elementi non presenti nella mappa fornita. Sii immersivo e fedele alle istruzioni di formato."
            ]
        )

    def esegui(self, map_size: str, scheda_giocatore: str, cartografo_output: dict, casting_output: dict, 
               tema: str, tema_desc: str, difficolta: str, difficolta_desc: str) -> dict:
        print("📜 [Agente 3: Maestro di Lore] Sintesi narrativa tramite Agno Agent...")
        
        mappa_completa = casting_output["mappa_arricchita"]
        npc_list = casting_output["npc_selezionati"]
        nemici_list = casting_output["creature_selezionate"]
        nome_boss = casting_output["nome_boss"]
        
        nomi_oggetti = [o.split('\n')[0].replace('[', '').replace(']', '').strip() for o in casting_output["oggetti_scelti"]]
        if "Equipaggiamento:" in scheda_giocatore:
            scheda_arricchita = scheda_giocatore.replace("Equipaggiamento:", f"Equipaggiamento: {', '.join(nomi_oggetti)}, ")
        else:
            parti = scheda_giocatore.split("Punti Ferita:")
            if len(parti) == 2:
                scheda_arricchita = parti[0] + f"Equipaggiamento: {', '.join(nomi_oggetti)}\nPunti Ferita:" + parti[1]
            else:
                scheda_arricchita = scheda_giocatore + f"\nEquipaggiamento: {', '.join(nomi_oggetti)}"
        
        nomi_nemici = []
        for c in nemici_list:
            m = re.search(r'^\[(.*?)\]', c)
            if m:
                nomi_nemici.append(m.group(1).strip())
            else:
                nomi_nemici.append(c.split('\n')[0].strip())
        
        nomi_npc = []
        for n in npc_list:
            m = re.search(r'^\[(.*?)\]', n)
            if m:
                nomi_npc.append(m.group(1).strip())
            else:
                nomi_npc.append(n.split('\n')[0].strip())
        
        nomi_zone = []
        for nodo in cartografo_output["nodi"]:
            m = re.search(r'^\[(.*?)\]', nodo)
            if m:
                nomi_zone.append(m.group(1).strip())
        
        sistema_gameplay = f"""Agisci come un Dungeon Master esperto di giochi di ruolo testuali e narrazione collaborativa.

=== AMBIENTAZIONE E TONO ({tema.upper()}) ===
{tema_desc}

=== LIVELLO DI DIFFICOLTÀ ({difficolta.upper()}) ===
{difficolta_desc}

=== LA SCHEDA DEL GIOCATORE CON OGGETTI DI PARTENZA ===
{scheda_arricchita}

=== GEOGRAFIA E POSIZIONI (LA MAPPA MULTI-AGENTE) ===
Il mondo di gioco della campagna è composto esattamente da {cartografo_output['tot_ambientazioni']} località interconnesse:
{mappa_completa}

ATTENZIONE FONDAMENTALE SUL BOSS FINALE E SUI NUMERI:
1. IL BOSS FINALE DA SCONFIGGERE PER COMPLETARE IL GIOCO È: **{nome_boss}**.
2. Nella mappa ci sono ESATTAMENTE {cartografo_output['tot_ambientazioni']} località/città, {casting_output['tot_npc']} NPC e {casting_output['tot_cattivi']} Nemici/Mostri.

=== PROGRESSIONE LINEARE OBBLIGATORIA ===
Zone disponibili: {', '.join(nomi_zone)}
NPC disponibili: {', '.join(nomi_npc)}
Nemici disponibili: {', '.join(nomi_nemici)}

=== REGOLE SUI DADI, AZIONI E GIOCO DI RUOLO ===
- Un tiro di 1 è un Fallimento Critico (disastroso ma narrativamente interessante).
- Un tiro di 20 è un Successo Critico (spettacolare ed eroico).
- Tiri da 2 a 10 tendono a fallire o riuscire con costo, da 11 a 19 tendono ad avere successo.

=== REGOLE DI RISPOSTA ===
Rispondi SEMPRE con pura narrazione immersiva in seconda persona. NON usare MAI tag tecnici, meta-commenti o formattazione speciale nelle risposte. Scrivi solo la storia, le azioni dei personaggi e i dialoghi.
IMPORTANTE - LUNGHEZZA: Sii completo ma CONCISO e BREVE. Le risposte devono essere di massimo 2-3 brevi paragrafi (circa 100-150 parole totali). Evita descrizioni prolisse o inutili lungaggini; la narrazione deve essere dinamica, incalzante e diretta.
"""

        # Prompt esteso SOLO per l'agente Agno (fase di creazione iniziale, NON salvato nella chat_history)
        sistema_agente = sistema_gameplay + f"""
=== STRUTTURA DELLA RISPOSTA CHE DEVI SCRIVERE ORA (SOLO PER QUESTA GENERAZIONE INIZIALE) ===
Devi dividere obbligatoriamente la tua risposta iniziale in TRE sezioni usando questi tag esatti:

[TAPPE_STORIA]
Genera una lista numerata di tappe obbligatorie della storia. Ogni tappa deve contenere:
- Il numero della tappa
- La zona dove si svolge (usando il tag della mappa, es. CENTRO, NORD, EST...)
- L'obiettivo da completare
- Il nome dell'NPC o nemico coinvolto
Formato ESATTO per ogni riga: "N. [ZONA] Descrizione dell'obiettivo (coinvolge: NomePersonaggio)"
L'ultima tappa DEVE essere lo scontro con il Boss Finale {nome_boss}.

[PERGAMENA]
- Paragrafo 1 (Il Mondo e la Minaccia): Introduci l'Ambientazione [CENTRO] e la minaccia suprema di **{nome_boss}**.
- Paragrafo 2 (Il Protagonista e il bottino): Menziona il giocatore, la sua classe e gli oggetti speciali.

[AZIONE_INIZIALE]
- Scrivi 2-3 righe molto dirette e incalzanti in cui metti il giocatore di fronte a un'azione o a un bivio immediato.
"""
        
        chat_history = [{"role": "system", "content": sistema_gameplay}]
        progressione = []
        
        try:
            response = self.agent.run(sistema_agente)
            dm_reply = response.content
            
            if "[TAPPE_STORIA]" in dm_reply:
                parti_tappe = dm_reply.split("[TAPPE_STORIA]")
                if len(parti_tappe) > 1:
                    testo_tappe = parti_tappe[1]
                    for tag_stop in ["[PERGAMENA]", "[AZIONE_INIZIALE]"]:
                        if tag_stop in testo_tappe:
                            testo_tappe = testo_tappe.split(tag_stop)[0]
                            break
                    for riga in testo_tappe.strip().split('\n'):
                        riga = riga.strip()
                        if riga and (riga[0].isdigit() or riga.startswith('-')):
                            progressione.append(riga)
            
            if "[PERGAMENA]" in dm_reply and "[AZIONE_INIZIALE]" in dm_reply:
                testo_pergamena = dm_reply.split("[PERGAMENA]")[1].split("[AZIONE_INIZIALE]")[0].strip()
                testo_azione = dm_reply.split("[AZIONE_INIZIALE]")[1].strip()
                # Puliamo la risposta per la history
                dm_reply = f"{testo_pergamena}\n\n{testo_azione}"
            elif "[AZIONE_INIZIALE]" in dm_reply:
                parti = dm_reply.split("[AZIONE_INIZIALE]")
                testo_pergamena = parti[0].replace("[PERGAMENA]", "").strip()
                # Rimuovi eventuale spazzatura prima del prologo (come il prompt di sistema ripetuto o le tappe)
                if "[TAPPE_STORIA]" in testo_pergamena:
                    testo_pergamena = testo_pergamena.split("[TAPPE_STORIA]")[-1].strip()
                # Rimuovi l'elenco delle tappe puntate/numerate rimaste in cima
                linee_pergamena = [line for line in testo_pergamena.split('\n') if not (line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '- ')))]
                testo_pergamena = '\n'.join(linee_pergamena).strip()
                
                testo_azione = parti[1].strip()
                dm_reply = f"{testo_pergamena}\n\n{testo_azione}"
            else:
                testo_pergamena = dm_reply.replace("[PERGAMENA]", "").replace("[TAPPE_STORIA]", "").strip()
                testo_azione = "L'aria attorno a te freme. Cosa decidi di fare per iniziare la tua avventura?"
                dm_reply = f"{testo_pergamena}\n\n{testo_azione}"
                
        except Exception as e:
            print(f"⚠️ Errore Agno LoreMaster: {e}. Attivazione fallback neuro-simbolico...")
            testo_pergamena = (
                f"L'orizzonte di **{cartografo_output['ambientazioni_selezionate'][0].split(chr(10))[0]}** si apre davanti a te. "
                f"L'atmosfera {tema} permea l'aria, mentre ti prepari alla sfida finale contro **{nome_boss}**. "
                f"La mappa conta {cartografo_output['tot_ambientazioni']} località, custodita da {casting_output['tot_npc']} figure misteriose "
                f"e minacciata da {casting_output['tot_cattivi']} entità ostili. Porti con te: {', '.join(nomi_oggetti)}."
            )
            testo_azione = "Senti un rumore di passi avvicinarsi dall'ombra. Sguaini la tua arma o decidi di esplorare l'area circostante?"
            dm_reply = f"[PERGAMENA]\n{testo_pergamena}\n\n[AZIONE_INIZIALE]\n{testo_azione}"
            chat_history.append({"role": "assistant", "content": dm_reply})
            
            progressione = [
                f"1. [CENTRO] Parla con gli abitanti locali per scoprire informazioni sulla minaccia (coinvolge: {nomi_npc[0] if nomi_npc else 'NPC locale'})",
                f"2. [{nomi_zone[1] if len(nomi_zone) > 1 else 'NORD'}] Raggiungi la zona e affronta la prima sfida (coinvolge: {nomi_nemici[1] if len(nomi_nemici) > 1 else 'Nemico'})",
                f"3. [{nomi_zone[-1] if nomi_zone else 'PROFONDITÀ'}] Affronta il Boss Finale (coinvolge: {nome_boss})"
            ]
            
        testo_pergamena = re.sub(r'\[DANNI:\s*\d+\]', '', testo_pergamena).strip()
        testo_azione = re.sub(r'\[DANNI:\s*\d+\]', '', testo_azione).strip()
        
        if not any(m.get("role") == "assistant" for m in chat_history):
            chat_history.append({"role": "assistant", "content": dm_reply})
            
        # Costruzione Tappe Strutturate (Logica in Python garantita)
        tappe_strutturate = []
        step_id = 1
        tot_citta = cartografo_output["tot_ambientazioni"]
        citta_nem = casting_output.get("citta_con_nemici", {})
        citta_nem_int = {int(k): v for k, v in citta_nem.items()}
        
        for i in range(tot_citta):
            nodo_grezzo = cartografo_output["nodi"][i]
            match_tag = re.search(r'^\[(.*?)\]:\s*(.*)', nodo_grezzo, flags=re.DOTALL)
            zona_tag = match_tag.group(1).strip() if match_tag else f"ZONA-{i+1}"
            testo_ambiente = match_tag.group(2).strip() if match_tag else "Luogo Sconosciuto"
            nome_luogo = testo_ambiente.split('\n')[0].replace('[', '').replace(']', '').split('<--')[0].strip()
            
            npc_grezzo = npc_list[i % len(npc_list)]
            npc_nome = npc_grezzo.split('\n')[0].replace('[', '').replace(']', '').strip()
            is_last = (i == tot_citta - 1)
            
            if i == 0:
                tappe_strutturate.append({
                    "id": step_id, "zona_tag": zona_tag, "nome_luogo": nome_luogo,
                    "personaggio": npc_nome, "obiettivo": f"Parla con {npc_nome} a {nome_luogo}",
                    "completato": False, "is_boss": False, "tipo": "npc"
                })
                step_id += 1
                if i in citta_nem_int and not citta_nem_int[i][1]:
                    nem_nome = citta_nem_int[i][0].split('\n')[0].replace('[', '').replace(']', '').strip()
                    tappe_strutturate.append({
                        "id": step_id, "zona_tag": zona_tag, "nome_luogo": nome_luogo,
                        "personaggio": nem_nome, "obiettivo": f"Sconfiggi {nem_nome} a {nome_luogo}",
                        "completato": False, "is_boss": False, "tipo": "combattimento"
                    })
                    step_id += 1
            elif not is_last:
                tappe_strutturate.append({
                    "id": step_id, "zona_tag": zona_tag, "nome_luogo": nome_luogo,
                    "personaggio": npc_nome, "obiettivo": f"Incontra e collabora con {npc_nome} a {nome_luogo}",
                    "completato": False, "is_boss": False, "tipo": "npc"
                })
                step_id += 1
                if i in citta_nem_int and not citta_nem_int[i][1]:
                    nem_nome = citta_nem_int[i][0].split('\n')[0].replace('[', '').replace(']', '').strip()
                    tappe_strutturate.append({
                        "id": step_id, "zona_tag": zona_tag, "nome_luogo": nome_luogo,
                        "personaggio": nem_nome, "obiettivo": f"Affronta e sconfiggi {nem_nome} a {nome_luogo}",
                        "completato": False, "is_boss": False, "tipo": "combattimento"
                    })
                    step_id += 1
            else:
                tappe_strutturate.append({
                    "id": step_id, "zona_tag": zona_tag, "nome_luogo": nome_luogo,
                    "personaggio": npc_nome, "obiettivo": f"Raggiungi {nome_luogo} e consulta {npc_nome}",
                    "completato": False, "is_boss": False, "tipo": "npc"
                })
                step_id += 1
                tappe_strutturate.append({
                    "id": step_id, "zona_tag": zona_tag, "nome_luogo": nome_luogo,
                    "personaggio": nome_boss, "obiettivo": f"Sconfiggi il Boss Finale {nome_boss} a {nome_luogo}",
                    "completato": False, "is_boss": True, "tipo": "boss"
                })
                step_id += 1

        progressione = [f"{t['id']}. [{t['zona_tag']}] {t['obiettivo']} (coinvolge: {t['personaggio']})" for t in tappe_strutturate]
        lista_bestiario = [casting_output["boss_finale_str"]] + [c for i, c in enumerate(nemici_list) if i != 0]
        
        lista_tappe_diario = []
        for t in tappe_strutturate:
            if t["id"] == 1:
                stato = "⏳ In Corso / Obiettivo Attuale"
                titolo = f"[👑 Tappa {t['id']} (BOSS FINALE E OBIETTIVO SUPREMO): {t['zona_tag']} - {t['personaggio']}]" if t.get("is_boss") else f"[Tappa {t['id']}: {t['zona_tag']} - {t['personaggio']}]"
                icona_coinvolto = "👑 Boss Finale" if t.get("is_boss") else ("⚔️ Nemico Ostile" if t.get("tipo") == "combattimento" else "👤 NPC Alleato/Informatore")
                testo_step = f"{titolo}\n📍 **Luogo / Zona:** {t['nome_luogo']} ({t['zona_tag']})\n{icona_coinvolto}: **{t['personaggio']}**\n📖 **Punto della Narrazione:** {t['obiettivo']}\n⚡ **Stato Tappa:** {stato}"
                lista_tappe_diario.append(testo_step)

        diario = {
            "👑 Boss Finale e Nemici (Bestiario)": lista_bestiario,
            "📜 Personaggi Incontrati (NPC)": npc_list,
            "🗺️ Luoghi della Mappa": cartografo_output["ambientazioni_selezionate"],
            "🎒 Il Protagonista e Oggetti (Personaggio)": [f"[Il Protagonista e Inventario]\n{scheda_arricchita}"] + casting_output["oggetti_scelti"],
            "🎯 Percorso e Tappe Obbligatorie": lista_tappe_diario
        }
        
        return {
            "chat_history": chat_history,
            "diario": diario,
            "mappa_mondo": mappa_completa,
            "prologo": testo_pergamena,
            "azione_iniziale": testo_azione,
            "personaggio_arricchito": scheda_arricchita,
            "progressione": progressione,
            "tappe_strutturate": tappe_strutturate,
            "statistiche_agenti": {
                "tot_ambientazioni": cartografo_output["tot_ambientazioni"],
                "tot_npc": casting_output["tot_npc"],
                "tot_cattivi": casting_output["tot_cattivi"],
                "boss_finale": nome_boss,
                "map_size": map_size
            }
        }


def orchestra_creazione_mondo(map_size: str, tema: str, tema_desc: str, difficolta: str, difficolta_desc: str,
                              scheda_giocatore: str, ambientazioni_rag: list, personaggi_rag: list, 
                              creature_rag: list, oggetti_rag: list) -> dict:
    """Orchestrazione della pipeline multi-agente usando Agno."""
    print(f"\n============================================================")
    print(f"🚀 AVVIO PIPELINE MULTI-AGENTE (AGNO) PER CREAZIONE STORIA ({map_size.upper()})")
    print(f"============================================================")
    
    cartografo = CartografoAgent(ambientazioni_rag)
    cartografo_out = cartografo.esegui(map_size, tema_desc)
    
    casting = CastingDirectorAgent(personaggi_rag, creature_rag, oggetti_rag)
    casting_out = casting.esegui(map_size, cartografo_out, tema_desc)
    
    loremaster = LoreMasterAgent()
    loremaster_out = loremaster.esegui(
        map_size=map_size, scheda_giocatore=scheda_giocatore,
        cartografo_output=cartografo_out, casting_output=casting_out,
        tema=tema, tema_desc=tema_desc,
        difficolta=difficolta, difficolta_desc=difficolta_desc
    )
    
    print(f"✅ Creazione mondo Multi-Agente Agno completata!")
    return loremaster_out
