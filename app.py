import random
import os
import sys
import re
import json
import textwrap
from openai import OpenAI
from flask import Flask, request, jsonify, send_from_directory, session

# Forza l'I/O in UTF-8 per visualizzare correttamente i caratteri accentati su Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Carica le variabili dal file .env se presente
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

# --- 1. CONFIGURAZIONE API ---
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL")
)

# --- 2. FUNZIONE DI LETTURA FILE TXT (CORRETTA) ---
def carica_mattoncini(nome_file):
    if not os.path.exists(nome_file):
        print(f"⚠️  ATTENZIONE: File '{nome_file}' non trovato.")
        return ["Nessuna informazione disponibile."]
    
    with open(nome_file, 'r', encoding='utf-8') as f:
        testo = f.read().strip()
        # Divide il testo SOLO quando trova uno o più "a capo" seguiti da "["
        elementi = [blocco.strip() for blocco in re.split(r'\n+(?=\[)', testo) if blocco.strip()]
        return elementi if elementi else ["Nessuna informazione disponibile."]

# --- CREAZIONE DINAMICA DEL PERSONAGGIO DA FILE ---
def genera_personaggio():
    # 1. Legge gli archetipi dal file txt
    archetipi = carica_mattoncini('player.txt')
    
    # Se il file è vuoto o non esiste, usa un fallback
    if not archetipi or archetipi[0] == "Nessuna informazione disponibile.":
        archetipo_scelto = "[Avventuriero Sconosciuto]\nRazza e Classe: Umano Guerriero\nEquipaggiamento: Spada e scudo."
    else:
        archetipo_scelto = random.choice(archetipi)
    
    # 2. Tiro dei dadi per le statistiche fisiche e mentali (3d6)
    forza = random.randint(3, 18)
    destrezza = random.randint(3, 18)
    intelligenza = random.randint(3, 18)
    costituzione = random.randint(3, 18)
    
    # 3. Assembla la scheda finale (Testo base + Dadi)
    scheda_completa = f"""{archetipo_scelto}
Statistiche (Generate coi Dadi):
- FORZA: {forza} (colpire duro, sollevare, spingere)
- DESTREZZA: {destrezza} (agilità, furtività, schivare, armi a distanza)
- INTELLIGENZA: {intelligenza} (magia, indagare, capire meccanismi)
- COSTITUZIONE: {costituzione} (resistenza fisica, salute)
Punti Ferita: 100/100"""
    
    return scheda_completa

# --- 3. CARICAMENTO DATI ---
ambientazioni = carica_mattoncini('ambient.txt')
personaggi = carica_mattoncini('npc.txt')
creature = carica_mattoncini('enemies.txt')

print("=" * 60)
print(" ⚔️  MORPHEUS GENESIS - SERVER WEB  ⚔️ ")
print("=" * 60)
print(f"Dati caricati: {len(ambientazioni)} ambientazioni, {len(personaggi)} personaggi, {len(creature)} creature.")

# --- 4. FLASK APP ---
app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.urandom(24)

# Stato di gioco in-memory (single player)
game_state = {
    "chat_history": [],
    "diario": {},
    "personaggio": "",
    "mappa": "",
    "attivo": False
}

# ============================
#  MAPPATURA TEMA → TESTO
# ============================
TEMI = {
    "dark-fantasy": "Dark Fantasy: regni corrotti dall'oscurità, magia proibita, atmosfera cupa e minacciosa. I colori dominanti sono il nero, il porpora e il rosso sangue.",
    "high-fantasy": "High Fantasy: terre epiche con eroi leggendari, draghi antichi e magia potente. L'atmosfera è grandiosa e avventurosa, ispirata a Tolkien e D&D classico.",
    "gothic-horror": "Gothic Horror: castelli infestati, vampiri, maledizioni ancestrali e nebbie eterne. L'atmosfera è claustrofobica, misteriosa e piena di orrore psicologico.",
    "steampunk": "Steampunk: un mondo dove la tecnologia a vapore si mescola con la magia. Ingranaggi, automi, dirigibili e invenzioni bizzarre dominano il paesaggio."
}

DIFFICOLTA = {
    "easy": "Novizio: i nemici sono deboli e la storia è fluida. Il giocatore ha maggiori probabilità di successo nei tiri dado. Sii generoso con le ricompense e clemente con i fallimenti.",
    "normal": "Avventuriero: equilibrio tra sfida e narrazione. I tiri dado seguono le regole standard. Sfide stimolanti ma eque.",
    "hard": "Veterano: i nemici sono letali e le risorse scarse. Anche tiri medio-alti possono fallire contro avversari potenti. Le conseguenze degli errori sono serie.",
    "hardcore": "Hardcore: morte permanente possibile. Ogni errore può essere fatale. I nemici sono spietati, le trappole mortali e non c'è pietà. Solo abilità e strategia possono salvare il giocatore."
}


# ============================
#  FUNZIONE PER DISEGNARE LA PERGAMENA
# ============================
def stampa_pergamena(testo):
    lunghezza_riga = 64
    righe_formattate = []
    
    # Suddivide il testo del Master rispettando i paragrafi
    for paragrafo in testo.split('\n'):
        if paragrafo.strip() == '':
            righe_formattate.append('')
        else:
            righe_formattate.extend(textwrap.wrap(paragrafo, width=lunghezza_riga))
            
    # Pulisce lo schermo prima di mostrare la pergamena
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Disegna la pergamena
    print("     ____________________________________________________________________")
    print("    / \\                                                                  \\")
    print("   |   |                                                                  |")
    print("    \\_ |                                                                  |")
    for riga in righe_formattate:
        # Il <64 assicura che lo spazio a destra sia riempito correttamente
        print(f"       |  {riga:<64}  |")
    print("       |                                                                  |")
    print("       |  ________________________________________________________________|")
    print("        \\_/______________________________________________________________/")

# ============================
#  ROUTE: HOMEPAGE
# ============================
@app.route('/')
def homepage():
    return send_from_directory('.', 'dnd_homepage.html')


@app.route('/game')
def game_page():
    return send_from_directory('.', 'dnd_game.html')


# ============================
#  API: AVVIA NUOVA PARTITA
# ============================
@app.route('/api/start', methods=['POST'])
def start_game():
    global game_state
    
    data = request.get_json()
    tema = data.get('theme', 'dark-fantasy')
    difficolta = data.get('difficulty', 'normal')
    map_size = data.get('map_size', 'medium')
    
    # Determina il numero di località in base alla dimensione mappa
    MAP_SIZES = {
        "small": 3,
        "medium": random.randint(4, 6),
        "large": 10
    }
    num_localita = MAP_SIZES.get(map_size, 4)
    
    # Genera il personaggio
    giocatore_attuale = genera_personaggio()
    
    # Estrai ambientazioni (limita al massimo disponibile)
    num_amb = min(num_localita, len(ambientazioni))
    ambient_scelta = random.sample(ambientazioni, num_amb)
    
    # Estrai NPC e creature (più di uno per mappe grandi)
    num_npc = max(1, num_localita // 3)
    num_creature = max(1, num_localita // 3)
    npc_scelti = random.sample(personaggi, min(num_npc, len(personaggi)))
    creature_scelte = random.sample(creature, min(num_creature, len(creature)))
    
    # Nomi delle direzioni per i nodi della mappa
    DIREZIONI = [
        "CENTRO", "NORD", "EST", "OVEST", "SUD",
        "NORD-EST", "NORD-OVEST", "SUD-EST", "SUD-OVEST", "PROFONDITÀ"
    ]
    
    # Costruisci la Mappa a Nodi dinamicamente
    righe_mappa = []
    for i in range(num_amb):
        dir_label = DIREZIONI[i] if i < len(DIREZIONI) else f"ZONA-{i+1}"
        riga = f"[{dir_label}]: {ambient_scelta[i]}"
        
        if i == 0:
            riga += " <-- (Tu sei qui)"
        elif i < len(npc_scelti) + 1 and (i - 1) < len(npc_scelti):
            riga += f" <-- (Presenza avvistata: {npc_scelti[i - 1]})"
        elif (i - 1 - len(npc_scelti)) >= 0 and (i - 1 - len(npc_scelti)) < len(creature_scelte):
            idx_c = i - 1 - len(npc_scelti)
            riga += f" <-- (Pericolo rilevato: {creature_scelte[idx_c]})"
        
        righe_mappa.append("    " + riga if i > 0 else riga)
    
    mappa_mondo = "\n".join(righe_mappa)
    
    # Inizializza il Diario
    diario = {
        "La Tua Storia": giocatore_attuale,
        "Mappa e Posizioni": mappa_mondo,
        "Luoghi Esplorati": [ambient_scelta[0]],
        "Personaggi Incontrati": npc_scelti,
        "Bestiario (Nemici Noti)": creature_scelte
    }
    
    # Costruisci il prompt di sistema con tema e difficoltà
    desc_tema = TEMI.get(tema, TEMI["dark-fantasy"])
    desc_diff = DIFFICOLTA.get(difficolta, DIFFICOLTA["normal"])
    
    sistema = f"""Agisci come un Dungeon Master esperto di giochi di ruolo testuali. 

=== AMBIENTAZIONE E TONO ===
{desc_tema}

=== LIVELLO DI DIFFICOLTÀ ===
{desc_diff}

=== LA SCHEDA DEL GIOCATORE ===
{giocatore_attuale}

=== GEOGRAFIA E POSIZIONI (LA MAPPA) ===
{mappa_mondo}

=== REGOLE DI ESPLORAZIONE E SPOSTAMENTO ===
1. POSIZIONE ATTUALE: Il gioco inizia con il giocatore nella zona [CENTRO]. Descrivi questo luogo nel Prologo.
2. VIAGGIO: Se il giocatore decide di spostarsi (es. va a NORD o verso EST), cambia l'ambientazione e fai incontrare l'NPC o il Nemico associato a quella zona.
3. COERENZA SPAZIALE: Rispetta rigorosamente i luoghi della mappa. Non far apparire l'NPC o il Nemico se il giocatore non si reca nella loro rispettiva zona.

=== REGOLE SUI DADI, AZIONI E GIOCO DI RUOLO ===
4. RISOLUZIONE CON I DADI: Ogni volta che il giocatore descrive un'azione, riceverai anche un [Tiro d20]. Narra l'esito incrociando questo tiro con le Statistiche della Scheda.
    - Un tiro di 1 è un Fallimento Critico (disastroso).
    - Un tiro di 20 è un Successo Critico (spettacolare).
    - Tiri da 2 a 10 tendono a fallire, da 11 a 19 tendono ad avere successo.
5. GIOCO DI RUOLO: Usa Personalità, Difetto, Obiettivo e Segreto del giocatore per creare tentazioni o bivi morali.
6. BREVITÀ ESTREMA (FONDAMENTALE): Il Prologo è descrittivo, ma DOPO il prologo, ogni tua risposta deve essere un "botta e risposta" rapido. Usa MASSIMO 2-3 frasi brevi per turno. Vai dritto al punto.
7. IL GIOCATORE È IL PROTAGONISTA: Non descrivere MAI cosa prova, cosa pensa o le azioni non dichiarate dal giocatore. Limita la tua narrazione alle conseguenze delle sue azioni e alle reazioni del mondo/PNG.
8. FORMATTAZIONE: Metti in **grassetto** nomi e oggetti. Usa il *corsivo* per i suoni.

=== STRUTTURA DEL PROLOGO CHE DEVI SCRIVERE ORA ===
- Paragrafo 1 (Il Mondo): Introduci l'Ambientazione con una descrizione viscerale e immersiva. Fai capire al giocatore l'atmosfera del luogo in cui si trova (suoni, odori, luci).
- Paragrafo 2 (Il Protagonista e lo Scopo): Inserisci organicamente il giocatore nella scena. Menziona il suo nome, la sua razza e classe, ma soprattutto il suo Obiettivo o il suo Background. Spiega brevemente perché si trova in questo luogo proprio per inseguire quel fine.
- Paragrafo 3 (L'Innesco dell'Azione): Fai entrare in scena il Personaggio (NPC) o fai percepire l'indizio del Nemico per creare tensione e dare il via all'avventura. Termina la narrazione in modo netto, lasciando la scena in sospeso".
"""
    
    chat_history = [{"role": "system", "content": sistema}]
    
    try:
        # Genera il primo messaggio (Prologo)
        response = client.chat.completions.create(
            model=os.environ.get("MODEL_NAME", "gpt-4o-mini"),
            messages=chat_history,
            temperature=0.75
        )
        dm_reply = response.choices[0].message.content
        
        chat_history.append({"role": "assistant", "content": dm_reply})
        
        # Salva lo stato di gioco
        game_state = {
            "chat_history": chat_history,
            "diario": diario,
            "personaggio": giocatore_attuale,
            "mappa": mappa_mondo,
            "tema": tema,
            "difficolta": difficolta,
            "attivo": True
        }
        
        return jsonify({
            "success": True,
            "personaggio": giocatore_attuale,
            "mappa": mappa_mondo,
            "prologo": dm_reply,
            "tema": tema,
            "difficolta": difficolta
        })
        
    except Exception as e:
        print(f"\nErrore di connessione: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================
#  API: AZIONE DEL GIOCATORE
# ============================
@app.route('/api/action', methods=['POST'])
def player_action():
    global game_state
    
    if not game_state["attivo"]:
        return jsonify({"success": False, "error": "Nessuna partita attiva."}), 400
    
    data = request.get_json()
    player_input = data.get('action', '').strip()
    
    if not player_input:
        return jsonify({"success": False, "error": "Azione vuota."}), 400
    
    # Tiro del dado (d20)
    tiro_dado = random.randint(1, 20)
    messaggio_con_dado = f"{player_input}\n[Tiro d20 del sistema per questa azione: {tiro_dado}]"
    
    # Aggiungi alla chat history
    game_state["chat_history"].append({"role": "user", "content": messaggio_con_dado})
    
    try:
        # L'IA pensa e risponde
        response = client.chat.completions.create(
            model=os.environ.get("MODEL_NAME", "gpt-4o-mini"),
            messages=game_state["chat_history"],
            temperature=0.75
        )
        
        dm_reply = response.choices[0].message.content
        game_state["chat_history"].append({"role": "assistant", "content": dm_reply})
        
        return jsonify({
            "success": True,
            "dm_reply": dm_reply,
            "tiro_dado": tiro_dado
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================
#  API: DIARIO
# ============================
@app.route('/api/diary', methods=['GET'])
def get_diary():
    if not game_state["attivo"]:
        return jsonify({"success": False, "error": "Nessuna partita attiva."}), 400
    
    return jsonify({
        "success": True,
        "diario": game_state["diario"]
    })


# ============================
#  API: SALVATAGGIO
# ============================
@app.route('/api/save', methods=['POST'])
def save_game():
    if not game_state["attivo"]:
        return jsonify({"success": False, "error": "Nessuna partita attiva."}), 400
    
    save_data = {
        "history": game_state["chat_history"],
        "diario": game_state["diario"],
        "personaggio": game_state["personaggio"],
        "mappa": game_state["mappa"],
        "tema": game_state.get("tema", "dark-fantasy"),
        "difficolta": game_state.get("difficolta", "normal")
    }
    
    with open("savegame.json", "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=4)
    
    return jsonify({"success": True, "message": "Partita salvata con successo!"})


# ============================
#  API: CARICAMENTO
# ============================
@app.route('/api/load', methods=['POST'])
def load_game():
    global game_state
    
    if not os.path.exists("savegame.json"):
        return jsonify({"success": False, "error": "Nessun salvataggio trovato."}), 404
    
    with open("savegame.json", "r", encoding="utf-8") as f:
        save_data = json.load(f)
    
    game_state = {
        "chat_history": save_data.get("history", []),
        "diario": save_data.get("diario", {}),
        "personaggio": save_data.get("personaggio", ""),
        "mappa": save_data.get("mappa", ""),
        "tema": save_data.get("tema", "dark-fantasy"),
        "difficolta": save_data.get("difficolta", "normal"),
        "attivo": True
    }
    
    # Trova l'ultimo messaggio del DM
    ultimo_dm = ""
    for msg in reversed(game_state["chat_history"]):
        if msg["role"] == "assistant":
            ultimo_dm = msg["content"]
            break
    
    return jsonify({
        "success": True,
        "personaggio": game_state["personaggio"],
        "mappa": game_state["mappa"],
        "ultimo_messaggio": ultimo_dm,
        "tema": game_state["tema"],
        "difficolta": game_state["difficolta"]
    })


# ============================
#  API: CONTROLLA SALVATAGGIO
# ============================
@app.route('/api/check-save', methods=['GET'])
def check_save():
    exists = os.path.exists("savegame.json")
    return jsonify({"exists": exists})


# ============================
#  AVVIO SERVER
# ============================
if __name__ == '__main__':
    print("\n🌐 Server avviato su http://localhost:5000")
    print("   Apri il browser e vai su http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)