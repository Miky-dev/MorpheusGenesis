import random
import os
import sys
import re
import json
import textwrap
import uuid
import datetime
from openai import OpenAI
from flask import Flask, request, jsonify, send_from_directory, session
import importlib
import combat_engine
import story_agents
import guardrails

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

# config API e rotazione chiavi
_groq_keys_raw = os.environ.get("GROQ_API_KEYS", os.environ.get("OPENAI_API_KEY", ""))
GROQ_API_KEYS = [k.strip() for k in _groq_keys_raw.split(",") if k.strip()]
if GROQ_API_KEYS and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = GROQ_API_KEYS[0]
_current_key_index = 0
_base_url = os.environ.get("OPENAI_BASE_URL")

def _crea_client(api_key):
    """Crea un client OpenAI."""
    return OpenAI(api_key=api_key, base_url=_base_url)

# Client iniziale
client = _crea_client(GROQ_API_KEYS[0]) if GROQ_API_KEYS else OpenAI()

def chiama_ia(messages, temperature=0.75):
    """Chiama l'API con retry su 429."""
    global client, _current_key_index
    
    model = os.environ.get("MODEL_NAME", "gpt-4o-mini")
    tentativi_fatti = 0
    max_tentativi = len(GROQ_API_KEYS)
    
    while tentativi_fatti < max_tentativi:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            return response
        except Exception as e:
            error_str = str(e)
            # Controlla se è un errore 429 (Rate Limit)
            if "429" in error_str or "rate_limit" in error_str.lower():
                tentativi_fatti += 1
                if tentativi_fatti < max_tentativi:
                    # Passa alla chiave successiva
                    _current_key_index = (_current_key_index + 1) % len(GROQ_API_KEYS)
                    nuova_chiave = GROQ_API_KEYS[_current_key_index]
                    client = _crea_client(nuova_chiave)
                    print(f"⚠️  Rate limit raggiunto! Rotazione alla chiave API #{_current_key_index + 1}/{len(GROQ_API_KEYS)}...")
                else:
                    # Tutte le chiavi esaurite
                    raise Exception(
                        f"🚫 Tutte le {len(GROQ_API_KEYS)} chiavi API hanno raggiunto il rate limit. "
                        f"Riprova tra qualche minuto."
                    )
            else:
                # Altro tipo di errore, rilancia direttamente
                raise


# stessa logica di chiama_ia ma col modello premium, todo unificare
def chiama_ia_premium(messages, temperature=0.7):
    """Versione premium per la storia (usa STORY_MODEL_NAME)."""
    global client, _current_key_index
    
    model = os.environ.get("STORY_MODEL_NAME", os.environ.get("MODEL_NAME", "gpt-4o-mini"))
    print(f"🧠 [Modello Premium] Utilizzo modello: {model}")
    tentativi_fatti = 0
    max_tentativi = len(GROQ_API_KEYS)
    
    while tentativi_fatti < max_tentativi:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            return response
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate_limit" in error_str.lower():
                tentativi_fatti += 1
                if tentativi_fatti < max_tentativi:
                    _current_key_index = (_current_key_index + 1) % len(GROQ_API_KEYS)
                    nuova_chiave = GROQ_API_KEYS[_current_key_index]
                    client = _crea_client(nuova_chiave)
                    print(f"⚠️  Rate limit raggiunto! Rotazione alla chiave API #{_current_key_index + 1}/{len(GROQ_API_KEYS)}...")
                else:
                    raise Exception(
                        f"🚫 Tutte le {len(GROQ_API_KEYS)} chiavi API hanno raggiunto il rate limit. "
                        f"Riprova tra qualche minuto."
                    )
            else:
                raise


# lettura file txt
def carica_mattoncini(nome_file):
    if not os.path.exists(nome_file):
        print(f"⚠️  ATTENZIONE: File '{nome_file}' non trovato.")
        return ["Nessuna informazione disponibile."]
    
    with open(nome_file, 'r', encoding='utf-8') as f:
        testo = f.read().strip()
        # Divide il testo SOLO quando trova uno o più "a capo" seguiti da "["
        elementi = [blocco.strip() for blocco in re.split(r'\n+(?=\[)', testo) if blocco.strip()]
        return elementi if elementi else ["Nessuna informazione disponibile."]

# generazione personaggio
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

# caricamento dati
ambientazioni = carica_mattoncini('ambient.txt')
personaggi = carica_mattoncini('npc.txt')
creature = carica_mattoncini('enemies.txt')
oggetti = carica_mattoncini('oggetti.txt')

print("=" * 60)
print(" ⚔️  MORPHEUS GENESIS - SERVER WEB  ⚔️ ")
print("=" * 60)
print(f"Dati caricati: {len(ambientazioni)} ambientazioni, {len(personaggi)} personaggi, {len(creature)} creature, {len(oggetti)} oggetti magici.")
print(f"🔑 Chiavi API caricate: {len(GROQ_API_KEYS)} (rotazione automatica attiva)" if len(GROQ_API_KEYS) > 1 else f"🔑 Chiave API caricata: 1")

# flask app
app = Flask(__name__, static_folder='.', static_url_path='')
# Usa una chiave segreta fissa per preservare la sessione tra i riavvii del server
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "morpheus_genesis_secret_key_fixed_2026")
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=30)

# Stato di gioco in-memory (multi-player concorrente)
game_states = {}

def get_session_id():
    session.permanent = True
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def get_game_state():
    sid = get_session_id()
    if sid not in game_states:
        game_states[sid] = {
            "chat_history": [],
            "diario": {},
            "personaggio": "",
            "mappa": "",
            "combat": {"active": False},
            "attivo": False,
            "posizione_attuale": {"zona_tag": "CENTRO", "nome_luogo": "Centro", "is_zona_sicura": True, "nemico_zona": None},
            "nemici_sconfitti": []
        }
    return game_states[sid]

def set_game_state(new_state):
    sid = get_session_id()
    game_states[sid] = new_state


def trova_file_salvataggio(sid=None):
    """Restituisce il percorso del file di salvataggio per la sessione o il salvataggio più recente come fallback."""
    if not sid:
        sid = get_session_id()
    
    path_sessione = f"saves/savegame_{sid}.json"
    if os.path.exists(path_sessione):
        return path_sessione
        
    # Fallback 1: Cerca il file più recente nella cartella saves/
    if os.path.exists("saves"):
        files = [os.path.join("saves", f) for f in os.listdir("saves") if f.startswith("savegame_") and f.endswith(".json")]
        if files:
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            return files[0]
            
    # Fallback 2: savegame.json nella radice
    if os.path.exists("savegame.json"):
        return "savegame.json"
        
    return None


def _salva_su_disco():
    """Salva game_state su savegame_<sid>.json e su savegame.json (auto-save server-side)."""
    game_state = get_game_state()
    if not game_state.get("attivo"):
        return
    try:
        save_data = {
            "history":            game_state["chat_history"],
            "diario":             game_state["diario"],
            "personaggio":        game_state["personaggio"],
            "mappa":              game_state["mappa"],
            "tema":               game_state.get("tema", "dark-fantasy"),
            "difficolta":         game_state.get("difficolta", "normal"),
            "hp":                 game_state.get("hp", 100),
            "combat":             game_state.get("combat", {"active": False}),
            "posizione_attuale":  game_state.get("posizione_attuale", {"zona_tag": "CENTRO", "nome_luogo": "", "is_zona_sicura": True, "nemico_zona": None}),
            "nemici_sconfitti":   game_state.get("nemici_sconfitti", []),
            "progressione":       game_state.get("progressione", []),
            "tappe_strutturate":  game_state.get("tappe_strutturate", []),
            "tappa_attiva_idx":   game_state.get("tappa_attiva_idx", 0)
        }
        os.makedirs("saves", exist_ok=True)
        sid = get_session_id()
        with open(f"saves/savegame_{sid}.json", "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        with open("savegame.json", "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        with open("debug.log", "a", encoding="utf-8") as dlog:
            import traceback
            dlog.write(f"Errore salvataggio disco: {e}\n{traceback.format_exc()}\n")
        print(f"Errore salvataggio disco: {e}")


# temi e difficoltà
TEMI = {
    "dark-fantasy": "Dark Fantasy: regni corrotti dall'oscurità, magia proibita, atmosfera cupa e minacciosa. I colori dominanti sono il nero, il porpora e il rosso sangue.",
    "high-fantasy": "High Fantasy: terre epiche con eroi leggendari, draghi antichi e magia potente. L'atmosfera è grandiosa e avventurosa, ispirata a Tolkien e D&D classico.",
    "gothic-horror": "Gothic Horror: castelli infestati, vampiri, maledizioni ancestrali e nebbie eterne. L'atmosfera è claustrofobica, misteriosa e piena di orrore psicologico.",
    "steampunk": "Steampunk: un mondo dove la tecnologia a vapore si mescola con la magia. Ingranaggi, automi, dirigibili e invenzioni bizzarre dominano il paesaggio."
}

DIFFICOLTA = {
    "easy": "Novizio: Fai da 'guida benevola'. I PNG sono più amichevoli e bendisposti, le trappole sono sempre preannunciate chiaramente prima che scattino, e gli errori del giocatore non sono mai puniti severamente. Dai suggerimenti e sii molto generoso con gli oggetti curativi.",
    "normal": "Avventura: L'IA si comporta da arbitro neutrale, seguendo le classiche regole di D&D. Sfide bilanciate e narrazione standard e realistica.",
    "hardcore": "Hardcore: Sii spietato, dark e punitivo. I PNG mentono, sono sospettosi o cercano di ingannare il giocatore, le trappole scattano senza preavviso infliggendo danni diretti, e l'ambiente stesso cerca di uccidere il protagonista ad ogni passo. Nessuna pietà per gli errori strategici."
}


# route homepage
@app.route('/')
def homepage():
    return send_from_directory('.', 'dnd_homepage.html')


@app.route('/game')
def game_page():
    return send_from_directory('.', 'dnd_game.html')


# avvia nuova partita
@app.route('/api/start', methods=['POST'])
def start_game():
    game_state = get_game_state()
    
    data = request.get_json()
    tema = data.get('theme', 'dark-fantasy')
    difficolta = data.get('difficulty', 'normal')
    map_size = data.get('map_size', 'medium')
    
    # Genera il personaggio
    giocatore_attuale = genera_personaggio()
    
    # Costruisci le descrizioni di tema e difficoltà
    desc_tema = TEMI.get(tema, TEMI["dark-fantasy"])
    desc_diff = DIFFICOLTA.get(difficolta, DIFFICOLTA["normal"])
    
    try:
        importlib.reload(story_agents)
        importlib.reload(combat_engine)
        
      
        req_amb = 4; req_npc = 4; req_cattivi = 2
        if map_size == "medium":
            req_amb = 6; req_npc = 6; req_cattivi = 3
        elif map_size == "large":
            req_amb = 10; req_npc = 10; req_cattivi = 5
            
      
        amb_sample = random.sample(ambientazioni, min(req_amb + 2, len(ambientazioni)))
        npc_sample = random.sample(personaggi, min(req_npc + 2, len(personaggi)))
        creature_sample = random.sample(creature, min(req_cattivi + 2, len(creature)))
        oggetti_sample = random.sample(oggetti, min(req_npc + 2, len(oggetti)))
        
  
        risultato_agenti = story_agents.orchestra_creazione_mondo(
            map_size=map_size,
            tema=tema,
            tema_desc=desc_tema,
            difficolta=difficolta,
            difficolta_desc=desc_diff,
            scheda_giocatore=giocatore_attuale,
            ambientazioni_rag=amb_sample,
            personaggi_rag=npc_sample,
            creature_rag=creature_sample,
            oggetti_rag=oggetti_sample
        )
        
        chat_history = risultato_agenti["chat_history"]
        diario = risultato_agenti["diario"]
        mappa_mondo = risultato_agenti["mappa_mondo"]
        testo_pergamena = risultato_agenti["prologo"]
        testo_azione = risultato_agenti["azione_iniziale"]
        personaggio_finale = risultato_agenti.get("personaggio_arricchito", giocatore_attuale)
        
        # Salva lo stato di gioco in memoria
        new_state = {
            "chat_history": chat_history,
            "diario": diario,
            "personaggio": personaggio_finale,
            "mappa": mappa_mondo,
            "tema": tema,
            "difficolta": difficolta,
            "hp": 100,
            "combat": {"active": False},
            "attivo": True,
            "posizione_attuale": {"zona_tag": "CENTRO", "nome_luogo": "", "is_zona_sicura": True, "nemico_zona": None},
            "nemici_sconfitti": [],
            "progressione": risultato_agenti.get("progressione", []),
            "tappe_strutturate": risultato_agenti.get("tappe_strutturate", []),
            "tappa_attiva_idx": 0
        }
        set_game_state(new_state)
        game_state = get_game_state()
        _update_player_position(game_state)
        _salva_su_disco()
        
        return jsonify({
            "success": True,
            "personaggio": personaggio_finale,
            "mappa": mappa_mondo,
            "prologo": testo_pergamena,
            "azione_iniziale": testo_azione,
            "tema": tema,
            "difficolta": difficolta,
            "hp": 100
        })
        
    except Exception as e:
        print(f"\nErrore di connessione o nella creazione Multi-Agente: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Ripristina automaticamente lo stato se il server è stato riavviato
def ripristina_stato_da_salvataggio():
    save_path = trova_file_salvataggio()
    if save_path and os.path.exists(save_path):
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                save_data = json.load(f)
            new_state = {
                "chat_history": save_data.get("history", []),
                "diario": save_data.get("diario", {}),
                "personaggio": save_data.get("personaggio", ""),
                "mappa": save_data.get("mappa", ""),
                "tema": save_data.get("tema", "dark-fantasy"),
                "difficolta": save_data.get("difficolta", "normal"),
                "hp": save_data.get("hp", 100),
                "combat": save_data.get("combat", {"active": False}),
                "attivo": True,
                "posizione_attuale": save_data.get("posizione_attuale", {"zona_tag": "CENTRO", "nome_luogo": "", "is_zona_sicura": True, "nemico_zona": None}),
                "nemici_sconfitti": save_data.get("nemici_sconfitti", []),
                "progressione": save_data.get("progressione", []),
                "tappe_strutturate": save_data.get("tappe_strutturate", []),
                "tappa_attiva_idx": save_data.get("tappa_attiva_idx", 0)
            }
            set_game_state(new_state)
            _update_diary_steps(get_game_state())
            _salva_su_disco()
            return True
        except Exception as e:
            print(f"Errore ripristino automatico: {e}")
    return False


# helper per rilevamento combattimento
def _detect_current_enemy(game_state):
    history = game_state.get("chat_history", [])
    known_enemies = list(combat_engine.BESTIARY_STATS.keys())
    
    tappe = game_state.get("tappe_strutturate", [])
    idx_attiva = game_state.get("tappa_attiva_idx", 0)
    tappa_attiva = tappe[idx_attiva] if (tappe and idx_attiva < len(tappe)) else {}
    is_on_boss_step = tappa_attiva.get("is_boss", False)
    
    # 1. Controlla se la tappa attiva è una sfida di combattimento non ancora completata e non è il boss (se non siamo alla fine)
    if tappa_attiva.get("tipo") in ["combattimento", "boss"] and not tappa_attiva.get("completato"):
        if is_on_boss_step or not tappa_attiva.get("is_boss", False):
            nem_tappa = tappa_attiva.get("personaggio", "").strip()
            if nem_tappa:
                return nem_tappa

    # 2. Controlla gli ultimi 8 messaggi in chat se menzionano un nemico noto (escludendo il boss se non siamo all'ultima tappa)
    for msg in reversed(history[-8:]):
        content_lower = msg.get("content", "").lower()
        for k_enemy in known_enemies:
            if k_enemy in content_lower:
                if not is_on_boss_step and any(b in k_enemy for b in ["lich", "drago", "fenice", "fungo colossale", "boss"]):
                    continue
                return k_enemy
                
    # 3. Controlla nel Diario -> escludendo il primo elemento (Boss Finale) se non siamo alla tappa finale!
    diario = game_state.get("diario", {})
    bestiario = diario.get("👑 Boss Finale e Nemici (Bestiario)", diario.get("Bestiario (Nemici Noti)", []))
    if bestiario and isinstance(bestiario, list) and len(bestiario) > 0:
        start_idx = 0 if is_on_boss_step else 1
        for nemico_diario in bestiario[start_idx:]:
            nem_lower = nemico_diario.lower()
            for k_enemy in known_enemies:
                if k_enemy in nem_lower or nem_lower in k_enemy:
                    return k_enemy
        if len(bestiario) > 1 and not is_on_boss_step:
            match_nem = re.search(r'\[([^\]]+)\]', bestiario[1])
            return match_nem.group(1).strip() if match_nem else bestiario[1].split('\n')[0].replace('[', '').replace(']', '').strip()
        elif is_on_boss_step and len(bestiario) > 0:
            match_b = re.search(r'\[(?:👑\s*BOSS FINALE:\s*)?([^\]]+)\]', bestiario[0], re.IGNORECASE)
            return match_b.group(1).strip() if match_b else bestiario[0].split('\n')[0].replace('[', '').replace(']', '').strip()
            
    return "Lupo delle Nebbie"


def _parse_map_nodes(mappa_str):
    nodes = []
    if not mappa_str:
        return nodes
    for line in mappa_str.split('\n'):
        line_clean = line.strip()
        if not line_clean or not line_clean.startswith('['):
            continue
        match_tag = re.search(r'\[([^\]]+)\]\s*([^<-]+)', line_clean)
        if not match_tag:
            continue
        tag = match_tag.group(1).strip()
        nome_luogo = match_tag.group(2).strip()
        
        is_zona_sicura = "Zona Sicura" in line_clean
        nemico_zona = None
        if not is_zona_sicura:
            match_nem = re.search(r'(?:Pericolo:|BOSS FINALE:)\s*([^)]+)\)', line_clean)
            if match_nem:
                nemico_zona = match_nem.group(1).strip()
            else:
                parti_pipe = line_clean.split('|')
                if len(parti_pipe) > 1:
                    candidato = parti_pipe[-1].replace('⚔️', '').replace(')', '').strip()
                    if candidato and "Zona Sicura" not in candidato:
                        nemico_zona = candidato
        nodes.append({
            "zona_tag": tag,
            "nome_luogo": nome_luogo,
            "is_zona_sicura": is_zona_sicura,
            "nemico_zona": nemico_zona
        })
    return nodes


def _update_player_position(game_state):
    nodes = _parse_map_nodes(game_state.get("mappa", ""))
    if not nodes:
        return
        
    if not game_state.get("posizione_attuale") or not game_state["posizione_attuale"].get("nome_luogo"):
        centro_node = next((n for n in nodes if n["zona_tag"].upper() == "CENTRO"), nodes[0])
        game_state["posizione_attuale"] = centro_node
        
    history = game_state.get("chat_history", [])
    if not history:
        return
        
    for msg in reversed(history[-6:]):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break
    else:
        return
        
    aree_disponibili = ", ".join([f"[{n['zona_tag']}] {n['nome_luogo']}" for n in nodes])
    prompt = f"""Analizza il messaggio del giocatore per capire se ha intenzione di viaggiare/spostarsi verso una nuova area.
Aree della mappa: {aree_disponibili}
Messaggio: "{last_user_msg}"

Rispondi SOLO con il tag dell'area di destinazione (es. NORD, CENTRO, SUD, ecc.) se il giocatore vuole muoversi.
Se il giocatore sta solo parlando, combattendo o facendo un'azione senza muoversi, rispondi ESATTAMENTE con: NESSUN_MOVIMENTO.
Non aggiungere alcuna spiegazione."""

    try:
        response = chiama_ia([{"role": "user", "content": prompt}], temperature=0.0)
        risposta_llm = response.choices[0].message.content.strip(" .\n\"'").upper()
        
        if "NESSUN_MOVIMENTO" not in risposta_llm:
            for node in nodes:
                # Confronta il tag o parte del nome del luogo
                if node["zona_tag"].upper() == risposta_llm or risposta_llm in node["nome_luogo"].upper():
                    game_state["posizione_attuale"] = node
                    return
    except Exception as e:
        print(f"⚠️ Errore nell'aggiornamento posizione tramite LLM: {e}")


def _get_active_enemy_at_location(game_state):
    pos = game_state.get("posizione_attuale", {})
    if pos.get("is_zona_sicura", True):
        return None
        
    nemico = pos.get("nemico_zona")
    sconfitti = game_state.get("nemici_sconfitti", [])
    
    if nemico and nemico not in sconfitti:
        return nemico
        
    return None


def _is_combat_trigger(player_input, game_state):
    text_lower = player_input.lower().strip()
    
    # Parola chiave di attacco o azione marziale/magica di scontro
    combat_keywords = [
        "attacc", "colpis", "fendente", "affond", "lanci", "combatt", "spada", 
        "arco", "ascia", "pugnal", "martello", "bastone", "mancina", "lancia", "dardo", 
        "balestra", "mazza", "falcetto", "incant", "fuoco", "fulmine", "runa", "arma",
        "affront", "sconfigg", "uccid", "ammazz", "elimina", "distrugg"
    ]
    if any(k in text_lower for k in combat_keywords):
        return True
        
    # Controlla se il testo corrisponde a un'arma o oggetto di difesa nell'equipaggiamento
    personaggio = game_state.get("personaggio", "").lower()
    for line in personaggio.split('\n'):
        if any(hdr in line for hdr in ["equipaggiamento:", "armi:", "oggetti:"]):
            items = line.split(":", 1)[-1].split(",")
            for item in items:
                item_clean = item.strip()
                if item_clean and item_clean != "—" and item_clean in text_lower:
                    if any(w in item_clean for w in ["spada", "arco", "ascia", "pugnal", "martello", "bastone", "mancina", "lancia", "dardo", "balestra", "mazza", "falcetto", "staffa", "lama"]):
                        return True
    return False


def _update_diary_steps(game_state):
    tappe = game_state.get("tappe_strutturate", [])
    idx_attiva = game_state.get("tappa_attiva_idx", 0)
    
    # Ricostruzione fallback se tappe_strutturate è vuoto (da un vecchio salvataggio o avvio precedente)
    if not tappe and game_state.get("progressione"):
        tappe = []
        for idx_p, p_str in enumerate(game_state["progressione"]):
            match_z = re.search(r'\[(.*?)\]\s*(.*?)(?:\s*\(coinvolge:\s*(.*?)\))?$', p_str)
            zona = match_z.group(1).strip() if match_z else f"ZONA-{idx_p+1}"
            ob = match_z.group(2).strip() if match_z else p_str
            coinvolto = match_z.group(3).strip() if (match_z and match_z.group(3)) else "Sconosciuto"
            is_boss = ("boss" in ob.lower() or "boss" in coinvolto.lower() or idx_p == len(game_state["progressione"])-1)
            tappe.append({
                "id": idx_p + 1,
                "zona_tag": zona,
                "nome_luogo": f"Luogo in {zona}",
                "personaggio": coinvolto,
                "obiettivo": ob,
                "completato": (idx_p < idx_attiva),
                "is_boss": is_boss,
                "tipo": "boss" if is_boss else "npc"
            })
        game_state["tappe_strutturate"] = tappe

    if not tappe or "diario" not in game_state:
        return

    if idx_attiva >= len(tappe):
        game_state["diario"]["🎯 Percorso e Tappe Obbligatorie"] = [
            "🏆 **TUTTE LE TAPPE COMPLETATE! VITTORIA SUPREMA!**\n\n"
            "Hai completato con successo l'intero percorso narrativo ed eliminato la minaccia finale. La tua leggenda è compiuta! 🎉"
        ]
        return
        
    lista_tappe_diario = []
    for t in tappe:
        t_id = t.get("id", 1)
        if t.get("completato") or t_id <= idx_attiva:
            stato = "✅ Completata"
        elif t_id == (idx_attiva + 1):
            stato = "⏳ In Corso / Obiettivo Attuale"
        else:
            stato = "🔒 Bloccata (Da Completare in Ordine)"
            
        if t.get("is_boss"):
            titolo = f"[👑 Tappa {t_id} (BOSS FINALE E OBIETTIVO SUPREMO): {t['zona_tag']} - {t['personaggio']}]"
            icona_coinvolto = "👑 Boss Finale"
        else:
            titolo = f"[Tappa {t_id}: {t['zona_tag']} - {t['personaggio']}]"
            icona_coinvolto = "⚔️ Nemico Ostile" if t.get("tipo") == "combattimento" else "👤 NPC Alleato/Informatore"
            
        testo_step = (
            f"{titolo}\n"
            f"📍 **Luogo / Zona:** {t.get('nome_luogo', '')} ({t.get('zona_tag', '')})\n"
            f"{icona_coinvolto}: **{t.get('personaggio', '')}**\n\n"
            f"🎯 **Cosa devi fare:** {t.get('obiettivo', '')}\n\n"
            f"⚡ **Stato:** {stato}"
        )
        # Mostra SOLO la tappa attualmente in corso (nascondendo quelle vecchie completate)
        if t_id == idx_attiva + 1:
            lista_tappe_diario.append(testo_step)
        
    game_state["diario"]["🎯 Percorso e Tappe Obbligatorie"] = lista_tappe_diario


def _check_advance_step(game_state, trigger_character_name=None, is_combat_win=False, from_llm_tag=False, player_input="", dm_reply=""):
    tappe = game_state.get("tappe_strutturate", [])
    idx = game_state.get("tappa_attiva_idx", 0)
    print(f"\n[DEBUG _check_advance_step] Chiamata con: idx={idx}, len(tappe)={len(tappe)}, from_llm_tag={from_llm_tag}, is_combat_win={is_combat_win}, trigger={trigger_character_name}")
    if not tappe or idx >= len(tappe):
        print(f"[DEBUG _check_advance_step] USCITA ANTICIPATA: tappe vuote={not tappe}, idx({idx}) >= len(tappe)({len(tappe)})")
        return False
    
    tappa = tappe[idx]
    print(f"[DEBUG _check_advance_step] Tappa corrente: id={tappa.get('id')}, personaggio={tappa.get('personaggio')}, completato={tappa.get('completato')}, tipo={tappa.get('tipo')}")
    if tappa.get("completato"):
        print(f"[DEBUG _check_advance_step] USCITA: tappa già completata!")
        return False
        
    avanza = False
    if from_llm_tag:
        avanza = True
        print(f"[DEBUG _check_advance_step] avanza=True (from_llm_tag)")
    elif is_combat_win and trigger_character_name:
        nem_tappa = tappa.get("personaggio", "").lower()
        trig_lower = trigger_character_name.lower()
        if nem_tappa in trig_lower or trig_lower in nem_tappa or any(w in trig_lower for w in nem_tappa.split() if len(w) > 3):
            avanza = True
            print(f"[DEBUG _check_advance_step] avanza=True (combat_win match: '{trig_lower}' vs '{nem_tappa}')")
        else:
            print(f"[DEBUG _check_advance_step] combat_win ma NESSUN MATCH: '{trig_lower}' vs '{nem_tappa}'")
    elif not avanza and dm_reply and not tappa.get("is_boss"):
        # Verifica fallback solo su frasi inequivocabili di completamento o successo della missione/tappa per l'NPC attuale
        coinvolto = tappa.get("personaggio", "").strip()
        nomi = [w.lower() for w in re.findall(r'\w+', coinvolto) if len(w) > 3]
        testo_azione = (player_input + " " + dm_reply).lower()
        if nomi and any(n in testo_azione for n in nomi):
            success_phrases = [
                "ti consegna", "ti dona", "ti affida", "ottieni il", "ricevi il", 
                "ti permette di accedere", "hai superato la prova", "hai dimostrato il tuo valore", 
                "ti rivela il segreto", "ti svela", "missione compiuta", "obiettivo completato"
            ]
            if any(p in dm_reply.lower() for p in success_phrases):
                avanza = True
                print(f"[DEBUG _check_advance_step] avanza=True (fallback phrases match)")
            
    if avanza:
        tappa["completato"] = True
        game_state["tappa_attiva_idx"] = idx + 1
        print(f"[DEBUG _check_advance_step] ✅ AVANZAMENTO! tappa_attiva_idx ora = {idx + 1}")
        _update_diary_steps(game_state)
        return True
    print(f"[DEBUG _check_advance_step] ❌ NON avanzato. avanza={avanza}")
    return False


# azione del giocatore (route principale)
@app.route('/api/action', methods=['POST'])
def player_action():
    game_state = get_game_state()
    
    if not game_state["attivo"]:
        if not ripristina_stato_da_salvataggio():
            return jsonify({"success": False, "error": "Nessuna partita attiva."}), 400
    
    data = request.get_json()
    player_input = data.get('action', '').strip()
    
    if not player_input:
        return jsonify({"success": False, "error": "Azione vuota."}), 400

    # blocco preventivo: se il player prova ad andare dal boss prima di aver
    # completato le tappe, intercettiamo e rispondiamo narrativamente
    _tappe_check = game_state.get("tappe_strutturate", [])
    _idx_check = game_state.get("tappa_attiva_idx", 0)
    _tappa_check = _tappe_check[_idx_check] if (_tappe_check and _idx_check < len(_tappe_check)) else {}
    _is_boss_step_now = _tappa_check.get("is_boss", False)

    if _tappe_check and not _is_boss_step_now:
        # Ricava nome e zona del boss
        _boss_tappa = next((t for t in _tappe_check if t.get("is_boss")), None)
        _nome_boss_check = _boss_tappa.get("personaggio", "") if _boss_tappa else ""
        _zona_boss_check = _boss_tappa.get("zona_tag", "") if _boss_tappa else ""
        _luogo_boss_check = _boss_tappa.get("nome_luogo", _zona_boss_check) if _boss_tappa else _zona_boss_check

        _parole_boss_check = set()
        if _nome_boss_check:
            for _w in re.findall(r'\w+', _nome_boss_check.lower()):
                if len(_w) > 3 and _w not in {"signore", "delle", "degli", "della", "grande", "reale", "boss", "finale"}:
                    _parole_boss_check.add(_w)
        if _zona_boss_check:
            _parole_boss_check.add(_zona_boss_check.lower())
        if _luogo_boss_check:
            for _w in re.findall(r'\w+', _luogo_boss_check.lower()):
                if len(_w) > 3:
                    _parole_boss_check.add(_w)

        # Verbi che indicano un tentativo di raggiungere/interagire col boss (non solo attaccare)
        _verbi_avvicinamento = [
            "vado", "vado da", "vado dal", "vado verso", "mi dirigo", "mi avvicino",
            "cerco", "cerco il", "cerco la", "trovo", "incontro", "parlo", "parlo con",
            "raggiungo", "arrivo", "entro", "entro nella", "mi reco", "mi porto",
            "devo andare", "voglio andare", "voglio trovare", "voglio parlare",
        ]
        _input_lower = player_input.lower()
        _ha_verbo = any(v in _input_lower for v in _verbi_avvicinamento)
        _ha_boss = (
            ("boss" in _input_lower) or
            (_parole_boss_check and any(pb in _input_lower for pb in _parole_boss_check))
        )

        if _ha_verbo and _ha_boss and _nome_boss_check:
            _tappa_n = _tappa_check.get("id", 1)
            _tappa_ob = _tappa_check.get("obiettivo", "completare la tappa corrente")
            _pers_tappa = _tappa_check.get("personaggio", "")
            _zona_tappa = _tappa_check.get("zona_tag", "")
            _luogo_tappa = _tappa_check.get("nome_luogo", _zona_tappa)
            # (random è già importato in cima)
            _blocchi_narrativi = [
                f"Una nebbia densa e innaturale si leva dal terreno non appena ti avvicini alla direzione di **{_nome_boss_check}**. "
                f"Le tue gambe si bloccano, come se forze invisibili ti impedissero di proseguire. "
                f"Un sussurro freddo risuona nell'aria: *\"Non sei ancora pronto... ci sono cose che devi prima affrontare.\"*\n\n"
                f"🗺️ *Hai ancora da completare la **Tappa {_tappa_n}**: {_tappa_ob}. Cerca **{_pers_tappa}** a {_luogo_tappa}.*",

                f"Ti muovi con decisione verso la tana di **{_nome_boss_check}**, ma un cancello di pietra riunica sbarra il cammino. "
                f"Le rune brillano di un rosso cupo: nessuno può attraversarle senza aver prima dimostrato il proprio valore.\n\n"
                f"Un viandante che passa ti osserva e scuote la testa: *\"Torna quando avrai trovato ciò che cerchi da **{_pers_tappa}** a {_luogo_tappa}. Solo allora le rune ti lasceranno passare.\"*",

                f"Il sentiero verso **{_nome_boss_check}** è avvolto da una maledizione antica. "
                f"Ad ogni passo che fai in quella direzione, il terreno sembra cedere e respingerti indietro.\n\n"
                f"Un corvo posato su un ramo gracchia tre volte, come se volesse attirare la tua attenzione verso un'altra direzione. "
                f"*Senti che dovresti prima occuparti di qualcosa di più urgente: **{_pers_tappa}** a **{_luogo_tappa}** ti aspetta.*",
            ]
            _dm_reply = random.choice(_blocchi_narrativi)
            game_state["chat_history"].append({"role": "user", "content": player_input})
            game_state["chat_history"].append({"role": "assistant", "content": _dm_reply})
            print(f"[BOSS LOCK] Tentativo di raggiungere '{_nome_boss_check}' bloccato. Tappa corrente: {_tappa_n}")
            return jsonify({
                "success": True,
                "dm_reply": _dm_reply,
                "hp": game_state.get("hp", 100),
                "tiro_dado": None
            })

    was_already_in_combat = game_state.get("combat", {}).get("active", False)
    importlib.reload(combat_engine)

    
    # Se NON siamo già in combattimento, ma l'utente utilizza un'arma o sferra un attacco,
    # attiviamo AUTOMATICAMENTE la modalità combattimento locale SOLO se c'è un nemico nella posizione attuale
    if not was_already_in_combat and _is_combat_trigger(player_input, game_state):
        _update_player_position(game_state)
        
        tappe = game_state.get("tappe_strutturate", [])
        idx_attiva = game_state.get("tappa_attiva_idx", 0)
        tappa_attiva = tappe[idx_attiva] if (tappe and idx_attiva < len(tappe)) else {}
        
        # Verifica se l'input del giocatore tenta di attaccare il Boss Finale anzitempo
        bestiario = game_state.get("diario", {}).get("👑 Boss Finale e Nemici (Bestiario)", [])
        nome_boss = ""
        for t in tappe:
            if t.get("is_boss"):
                nome_boss = t.get("personaggio", "").strip()
                break
        if not nome_boss and bestiario and len(bestiario) > 0:
            match_b = re.search(r'\[(?:👑\s*BOSS FINALE:\s*)?([^\]]+)\]', bestiario[0], re.IGNORECASE)
            nome_boss = match_b.group(1).strip() if match_b else bestiario[0].split('\n')[0].replace('[', '').replace(']', '').strip()
            
        parole_boss = set()
        if nome_boss:
            for w in re.findall(r'\w+', nome_boss.lower()):
                if len(w) > 3 and w not in ["signore", "delle", "degli", "della", "grande", "reale"]:
                    parole_boss.add(w)
        if bestiario and len(bestiario) > 0:
            for w in re.findall(r'\w+', bestiario[0].lower()):
                if len(w) > 3 and w not in ["boss", "finale", "signore", "delle", "degli", "della", "grande", "reale"]:
                    parole_boss.add(w)

        is_attacking_boss = False
        if (parole_boss and any(pb in player_input.lower() for pb in parole_boss)) or "boss" in player_input.lower():
            is_attacking_boss = True
            
        if is_attacking_boss and not tappa_attiva.get("is_boss", False):
            # IL BOSS NON È ANCORA ATTACCABILE! BLOCCO SCRIPTATO E INTERCETTAZIONE!
            tappa_num = tappa_attiva.get("id", 1)
            tappa_ob = tappa_attiva.get("obiettivo", "completare le tappe precedenti della storia")
            dm_reply = (
                f"🛡️ **ATTACCO AL BOSS BLOCCATO (PERCORSO INCOMPLETO)**\n\n"
                f"Tenti di scagliarti o puntare la tua arma direttamente contro **{nome_boss or 'il Boss Finale'}**, ma una barriera magica, la distanza o le regole celestiali del santuario impediscono qualsiasi scontro marziale anticipato contro la minaccia suprema!\n\n"
                f"*(Per poter affrontare il Boss Supremo in combattimento devi prima completare la **Tappa {tappa_num}** in corso: \"{tappa_ob}\")*"
            )
            game_state["chat_history"].append({"role": "user", "content": player_input})
            game_state["chat_history"].append({"role": "assistant", "content": dm_reply})
            return jsonify({
                "success": True,
                "dm_reply": dm_reply,
                "hp": game_state.get("hp", 100),
                "tiro_dado": None
            })

        enemy_name = _get_active_enemy_at_location(game_state)
        
        if not enemy_name:
            pos = game_state.get("posizione_attuale", {})
            # Combattimento se la zona ha un nemico assegnato e non è già sconfitto
            if not pos.get("is_zona_sicura", True) and pos.get("nemico_zona"):
                nemico_zona = pos.get("nemico_zona")
                sconfitti = game_state.get("nemici_sconfitti", [])
                if nemico_zona not in sconfitti:
                    enemy_name = nemico_zona
        
        # Fallback basato sulla tappa attiva: se la tappa corrente è di combattimento/boss,
        # il nemico della tappa è attaccabile anche se il tracker di posizione non si è aggiornato
        if not enemy_name and tappa_attiva.get("tipo") in ["combattimento", "boss"]:
            nemico_tappa = tappa_attiva.get("personaggio", "").strip()
            sconfitti = game_state.get("nemici_sconfitti", [])
            if nemico_tappa and nemico_tappa not in sconfitti:
                enemy_name = nemico_tappa
                    
        if enemy_name:
            # Assicurati che l'enemy_name non sia per sbaglio associato al boss in tappe precedenti
            if not tappa_attiva.get("is_boss", False) and ((parole_boss and any(pb in enemy_name.lower() for pb in parole_boss)) or "boss" in enemy_name.lower()):
                enemy_name = None
                
        if enemy_name:
            difficolta = game_state.get("difficolta", "normal")
            stats = combat_engine.get_enemy_stats(enemy_name, difficolta)
            stats["active"] = True
            is_boss_target = tappa_attiva.get("is_boss", False) and ((parole_boss and any(pb in enemy_name.lower() for pb in parole_boss)) or "boss" in enemy_name.lower())
            stats["is_boss"] = is_boss_target
            game_state["combat"] = stats
        else:
            pos = game_state.get("posizione_attuale", {})
            luogo_nome = pos.get("nome_luogo") or pos.get("zona_tag") or "questa zona"
            if pos.get("nemico_zona") and pos.get("nemico_zona") in game_state.get("nemici_sconfitti", []):
                motivo = f"Hai già sconfitto **{pos.get('nemico_zona')}** in questa area e l'hai ripulita dalle minacce."
            else:
                motivo = f"Ci troviamo in una **Zona Sicura ({luogo_nome})** dove non sono presenti nemici da affrontare in combattimento marziale."
                
            dm_reply = (
                f"🛡️ **NESSUN NEMICO DA ATTACCARE NELLA ZONA**\n\n"
                f"Sguaini la tua arma ed assumi una posizione di combattimento a **{luogo_nome}**, ma guardandoti con attenzione ti accorgi che non c'è alcun bersaglio ostile da attaccare qui ({motivo}).\n\n"
                f"*(Per entrare in combattimento marziale devi prima esplorare o recarti in un'area dove è presente una minaccia ⚔️)*"
            )
            game_state["chat_history"].append({"role": "user", "content": player_input})
            game_state["chat_history"].append({"role": "assistant", "content": dm_reply})
            return jsonify({
                "success": True,
                "dm_reply": dm_reply,
                "hp": game_state.get("hp", 100),
                "tiro_dado": None
            })
        
    # Se siamo in COMBATTIMENTO LOCALE (senza API LLM)
    if game_state.get("combat", {}).get("active"):
        res = combat_engine.risolvi_turno_combattimento(player_input, game_state)
        if res and res.get("success"):
            if res.get("combat", {}).get("enemy_hp", 1) <= 0 or (not game_state.get("combat", {}).get("active", False) and game_state.get("combat", {}).get("hp", 1) <= 0):
                defeated_enemy = res.get("combat", {}).get("enemy_name") or game_state.get("combat", {}).get("enemy_name")
                if defeated_enemy and defeated_enemy not in game_state.setdefault("nemici_sconfitti", []):
                    game_state["nemici_sconfitti"].append(defeated_enemy)
                    # Verifica se lo scontro fa avanzare la tappa corrente del percorso scriptato
                    avanzato = _check_advance_step(game_state, trigger_character_name=defeated_enemy, is_combat_win=True)
                    if avanzato:
                        idx_nuovo = game_state.get("tappa_attiva_idx", 0)
                        tappe_tot = game_state.get("tappe_strutturate", [])
                        if idx_nuovo >= len(tappe_tot):
                            res["dm_reply"] += "\n\n🏆 **[VITTORIA SUPREMA - CAMPAGNA COMPLETATA!]** Hai sconfitto l'avversario finale! La campagna si conclude con un trionfo epico!"
                        else:
                            res["dm_reply"] += f"\n\n✨ **[TAPPA COMPLETATA]** Hai superato l'obiettivo! Ti attende la **Tappa {idx_nuovo + 1}** del percorso."
                    
            if not was_already_in_combat:
                enemy_name_title = game_state["combat"].get("enemy_name", "Nemico")
                intro_msg = (
                    f"⚔️ **MODALITÀ COMBATTIMENTO ATTIVATA vs {enemy_name_title.upper()}!**\n"
                    f"*(Da questo momento lo scontro è risolto in locale tramite dadi d20 e calcolo danni senza chiamare l'IA)*\n\n"
                )
                res["dm_reply"] = intro_msg + res["dm_reply"]
                
            game_state["chat_history"].append({"role": "user", "content": player_input})
            game_state["chat_history"].append({"role": "assistant", "content": res["dm_reply"]})
            
            # Se il giocatore muore in combattimento
            if game_state.get("hp", 100) <= 0:
                save_path = trova_file_salvataggio()
                if save_path and os.path.exists(save_path):
                    try:
                        os.remove(save_path)
                    except Exception as e:
                        print(f"Errore rimozione salvataggio: {e}")
                if os.path.exists("savegame.json"):
                    try:
                        os.remove("savegame.json")
                    except Exception:
                        pass
                game_state["attivo"] = False
                
            return jsonify(res)
            
    # Tiro del dado (d20) per esplorazione narrative con LLM
    tiro_dado = random.randint(1, 20)
    messaggio_con_dado = f"{player_input}\n[Tiro d20 del sistema per questa azione: {tiro_dado}]"
    
    # Aggiungi alla chat history
    game_state["chat_history"].append({"role": "user", "content": messaggio_con_dado})
    _update_player_position(game_state)
    
    try:
        # --- AGENTE CONTROLLORE DEL DIALOGO & STEERING SCRIPTATO ---
        messages_for_llm = list(game_state["chat_history"])
        tappe = game_state.get("tappe_strutturate", [])
        idx_attiva = game_state.get("tappa_attiva_idx", 0)
        if tappe and idx_attiva < len(tappe):
            tappa_attiva = tappe[idx_attiva]

            # Costruiamo informazioni di contesto sulle tappe rimanenti per la guida degli NPC
            tappe_rimanenti = [t for t in tappe if not t.get("completato") and t["id"] != tappa_attiva["id"]]
            tappa_boss = next((t for t in tappe if t.get("is_boss")), None)
            nome_boss_str = tappa_boss.get("personaggio", "il Boss Finale") if tappa_boss else "il Boss Finale"
            zona_boss_str = tappa_boss.get("zona_tag", "") if tappa_boss else ""
            nome_luogo_boss_str = tappa_boss.get("nome_luogo", zona_boss_str) if tappa_boss else zona_boss_str

            # Posizione attuale del giocatore
            pos_attuale = game_state.get("posizione_attuale", {})
            zona_corrente = pos_attuale.get("zona_tag", "")
            nome_luogo_corrente = pos_attuale.get("nome_luogo", zona_corrente)

            # Verifica se il giocatore si trova nella zona della tappa attiva o in una zona "sbagliata"
            zona_tappa = tappa_attiva.get("zona_tag", "")
            in_zona_giusta = (zona_corrente.upper() == zona_tappa.upper())

            # Verifica se il giocatore si trova nella zona del boss (da bloccare)
            in_zona_boss = zona_boss_str and (zona_corrente.upper() == zona_boss_str.upper())
            tutte_tappe_completate = (idx_attiva >= len(tappe) - 1) or (tappa_attiva.get("is_boss", False))

            steering_prompt = {
                "role": "system",
                "content": (
                    f"=== DIRETTIVE VINCOLANTI DEL CONTROLLORE DI STORIA ===\n\n"

                    f"STATO CORRENTE DELLA CAMPAGNA:\n"
                    f"- Tappa attiva: {tappa_attiva['id']}/{len(tappe)} | Zona richiesta: [{tappa_attiva['zona_tag']}] - {tappa_attiva.get('nome_luogo', '')}\n"
                    f"- Personaggio/Nemico coinvolto nella tappa: **{tappa_attiva['personaggio']}**\n"
                    f"- Obiettivo da completare: {tappa_attiva['obiettivo']}\n"
                    f"- Posizione attuale del giocatore: [{zona_corrente}] - {nome_luogo_corrente}\n"
                    f"- Il giocatore è nella zona giusta per la tappa: {'SÌ' if in_zona_giusta else 'NO — si trova altrove'}\n"
                    f"- Boss Finale: **{nome_boss_str}** nella zona [{zona_boss_str}] ({nome_luogo_boss_str})\n"
                    f"- Tutte le tappe pre-boss completate: {'SÌ' if tutte_tappe_completate else 'NO'}\n\n"

                    f"REGOLA 1 — BOSS FINALE INACCESSIBILE FINCHÉ LE TAPPE NON SONO COMPLETE:\n"
                    f"{'ATTENZIONE: il giocatore è nella zona del boss MA non ha completato tutte le tappe! ' if in_zona_boss and not tutte_tappe_completate else ''}"
                    f"Se il giocatore si trova nella zona [{zona_boss_str}] oppure cerca di raggiungere **{nome_boss_str}** in qualunque modo "
                    f"(parlare, avvicinarsi, cercarlo, attaccarlo, incontrarlo) E la tappa attiva NON è quella del boss: "
                    f"DEVI IMPEDIRLO in modo narrativo e immersivo. Esempi: una barriera magica sigilla l'accesso, "
                    f"una nebbia innaturale lo rispedisce indietro, i guardiani dell'antro bloccano il passaggio, "
                    f"una maledizione lo immobilizza. NON spiegare mai il motivo in termini meta-game. "
                    f"Il boss non è visibile, non è raggiungibile, non risponde a nessun tentativo di contatto "
                    f"finché le tappe precedenti non sono completate.\n\n"

                    f"REGOLA 2 — SE IL GIOCATORE È NELLA ZONA SBAGLIATA (non quella della tappa attiva):\n"
                    f"Gli NPC e gli abitanti del luogo [{zona_corrente}] dove si trova il giocatore "
                    f"DEVONO fornire indizi narrativi immersivi che lo guidino verso la tappa corrente. "
                    f"Fanno questo in modo naturale: menzionano voci, leggende, avvertimenti o informazioni "
                    f"che puntano verso la zona [{tappa_attiva['zona_tag']}] e verso **{tappa_attiva['personaggio']}**. "
                    f"Esempi di dialogo NPC: "
                    f"'Ho sentito dire che {tappa_attiva['personaggio']} sa qualcosa di fondamentale...', "
                    f"'Se cerchi risposte, dovresti andare a {tappa_attiva.get('nome_luogo', tappa_attiva['zona_tag'])}', "
                    f"'Si dice che senza prima affrontare {tappa_attiva['personaggio']} nessuno possa andare oltre...'. "
                    f"NON bloccare fisicamente il giocatore in questa zona — lascialo libero di muoversi, "
                    f"ma ogni NPC incontrato deve spingere narrativamente verso la tappa corretta.\n\n"

                    f"REGOLA 3 — INDIRIZZAMENTO OCCULTO (se il giocatore è nella zona giusta):\n"
                    f"Il giocatore si trova già nella zona corretta [{tappa_attiva['zona_tag']}]. "
                    f"Spingi dialoghi e eventi verso l'incontro/completamento con **{tappa_attiva['personaggio']}**. "
                    f"Se il giocatore cerca di ignorare questo obiettivo e vagare altrove, riportalo al centro "
                    f"della scena con eventi improvvisi, chiamate degli NPC, o ostacoli narrativi.\n\n"

                    f"REGOLA 4 — SBLOCCO TAPPA (completamento):\n"
                    f"Se il giocatore compie un'azione anche solo vagamente in linea con l'obiettivo della tappa, o se cerca di completarla, DEVI fargliela completare senza prolungare. Narra il successo E inserisci OBBLIGATORIAMENTE questo tag alla fine:\n"
                    f"[STEP_COMPLETATO]\n\n"

                    f"REGOLA 5 — ILLUSIONE DI LIBERTÀ:\n"
                    f"Il giocatore deve sempre percepire libertà totale. NON usare mai frasi meta-game "
                    f"come 'devi completare la tappa X' o 'non puoi andare lì perché è uno script'. "
                    f"Ogni blocco o indirizzamento deve essere narrativo, immersivo e coerente col mondo fantasy.\n\n"

                    f"REGOLA 6 — STILE E BREVITÀ:\n"
                    f"La risposta deve essere COMPLETA MA BREVE E CONCISA. "
                    f"Scrivi al massimo 2-3 brevi paragrafi (circa 100-150 parole in totale). "
                    f"Evita descrizioni prolisse, giri di parole o spiegazioni inutili. Rispondi all'azione del giocatore in modo diretto e incalzante.\n"
                    f"=============================================================="
                )
            }
            messages_for_llm.append(steering_prompt)


        # --- PALETTI DI SICUREZZA AI (GUARDRAILS) ---
        # Conta il turno corrente (numero di messaggi 'user' in history)
        turno_numero = sum(1 for m in game_state["chat_history"] if m.get("role") == "user")
        esito_guardrail = guardrails.applica_guardrails(player_input, messages_for_llm, turno_numero)

        if esito_guardrail["bloccato"]:
            # Injection rilevata: blocca la chiamata LLM e rispondi in modo narrativo
            risposta_blocco = esito_guardrail["risposta_blocco"]
            game_state["chat_history"].append({"role": "assistant", "content": risposta_blocco})
            return jsonify({
                "success": True,
                "dm_reply": risposta_blocco,
                "tiro_dado": None,
                "hp": game_state.get("hp", 100),
                "danni_subiti": 0
            })

        # Usa i messaggi arricchiti con i guardrail invece della lista originale
        messages_for_llm = esito_guardrail["messages_for_llm"]

        # L'IA pensa e risponde guidata dal Controllore del Dialogo e dai Guardrail
        response = chiama_ia(messages_for_llm)
        
        dm_reply = response.choices[0].message.content
        
        # Verifica se l'IA o l'interazione narrativa hanno completato la tappa scriptata
        avanzato = False
        print(f"\n[DEBUG player_action] Risposta LLM ricevuta. Controllo tag STEP_COMPLETATO...")
        print(f"[DEBUG player_action] '[STEP_COMPLETATO]' in dm_reply = {'[STEP_COMPLETATO]' in dm_reply}")
        print(f"[DEBUG player_action] 'STEP_COMPLETATO' in dm_reply = {'STEP_COMPLETATO' in dm_reply}")
        print(f"[DEBUG player_action] tappa_attiva_idx PRIMA = {game_state.get('tappa_attiva_idx', 0)}")
        if "[STEP_COMPLETATO]" in dm_reply or "STEP_COMPLETATO" in dm_reply or "[TAPPA COMPLETATA]" in dm_reply:
            dm_reply = dm_reply.replace("[STEP_COMPLETATO]", "").replace("STEP_COMPLETATO", "").strip()
            # Se l'LLM ha allucinato la stringa python, rimuoviamola in modo pulito
            dm_reply = re.sub(r'✨\s*\*\*\[TAPPA COMPLETATA\]\*\*.*', '', dm_reply).strip()
            
            avanzato = _check_advance_step(game_state, from_llm_tag=True, player_input=player_input, dm_reply=dm_reply)
            print(f"[DEBUG player_action] Risultato _check_advance_step (from_llm_tag): {avanzato}")
        else:
            avanzato = _check_advance_step(game_state, player_input=player_input, dm_reply=dm_reply)
            print(f"[DEBUG player_action] Risultato _check_advance_step (fallback): {avanzato}")
        print(f"[DEBUG player_action] tappa_attiva_idx DOPO = {game_state.get('tappa_attiva_idx', 0)}")
            
        if avanzato:
            idx_nuovo = game_state.get("tappa_attiva_idx", 0)
            tappe_tot = game_state.get("tappe_strutturate", [])
            if idx_nuovo >= len(tappe_tot):
                dm_reply += "\n\n🏆 **[VITTORIA SUPREMA - CAMPAGNA COMPLETATA!]** Hai completato tutte le tappe della storia e superato ogni sfida del mondo di gioco!"
            else:
                dm_reply += f"\n\n✨ **[TAPPA COMPLETATA]** Hai superato l'obiettivo! Ti attende la **Tappa {idx_nuovo + 1}** del percorso."
        
        # --- SISTEMA DANNI E GAME OVER ---
        match_danni = re.search(r'\[DANNI:\s*(-?\d+)\]', dm_reply)
        danni_subiti = 0
        if match_danni:
            danni_subiti = abs(int(match_danni.group(1)))
            hp_attuali = game_state.get("hp", 100)
            hp_attuali -= danni_subiti
            if hp_attuali < 0:
                hp_attuali = 0
            game_state["hp"] = hp_attuali
            
            # Ripulisce il tag dal testo del DM
            dm_reply = re.sub(r'\[DANNI:\s*-?\d+\]', '', dm_reply).strip()
            
            if hp_attuali <= 0:
                # Permadeath: cancella il file di salvataggio
                save_path = trova_file_salvataggio()
                if save_path and os.path.exists(save_path):
                    try:
                        os.remove(save_path)
                    except Exception as e:
                        print(f"Errore rimozione salvataggio: {e}")
                if os.path.exists("savegame.json"):
                    try:
                        os.remove("savegame.json")
                    except Exception:
                        pass
                game_state["attivo"] = False
        
        # Salviamo la risposta pulita e auto-salviamo su disco
        game_state["chat_history"].append({"role": "assistant", "content": dm_reply})
        _update_player_position(game_state)
        
        with open("debug.log", "a", encoding="utf-8") as dlog:
            dlog.write(f"[DEBUG player_action END] Chiamo _salva_su_disco. tappa_attiva_idx in game_state={game_state.get('tappa_attiva_idx', 0)}\n")
        
        _salva_su_disco()  # Auto-salvataggio server-side dopo ogni risposta
        
        return jsonify({
            "success": True,
            "dm_reply": dm_reply,
            "tiro_dado": tiro_dado,
            "hp": game_state.get("hp", 100),
            "danni_subiti": danni_subiti
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# avvio combattimento locale
@app.route('/api/combat/start', methods=['POST'])
def start_combat():
    game_state = get_game_state()
    if not game_state["attivo"]:
        if not ripristina_stato_da_salvataggio():
            return jsonify({"success": False, "error": "Nessuna partita attiva."}), 400
            
    data = request.get_json() or {}
    enemy_name = data.get('enemy_name', '').strip()
    if not enemy_name:
        _update_player_position(game_state)
        enemy_name = _get_active_enemy_at_location(game_state) or _detect_current_enemy(game_state)
    difficolta = game_state.get("difficolta", "normal")
    
    stats = combat_engine.get_enemy_stats(enemy_name, difficolta)
    stats["active"] = True
    game_state["combat"] = stats
    
    msg_avvio = (
        f"⚔️ **HA INIZIO IL COMBATTIMENTO!** ⚔️\n\n"
        f"Un formidabile **{stats['enemy_name']}** (HP: {stats['enemy_hp']}/{stats['enemy_max_hp']} | CA: {stats['enemy_ac']}) "
        f"si para dinanzi a te in posizione di attacco!\n"
        f"*(Da ora in poi, le tue azioni di combattimento saranno risolte dal motore tattico locale in Python, senza consumare token API!)*"
    )
    game_state["chat_history"].append({"role": "assistant", "content": msg_avvio})
    
    return jsonify({
        "success": True,
        "combat": stats,
        "dm_reply": msg_avvio,
        "hp": game_state.get("hp", 100)
    })

@app.route('/api/combat/flee', methods=['POST'])
def flee_combat():
    game_state = get_game_state()
    if not game_state["attivo"] or not game_state.get("combat", {}).get("active"):
        return jsonify({"success": False, "error": "Non sei in combattimento."}), 400
        
    res = combat_engine.risolvi_turno_combattimento("fuga", game_state)
    if res and res.get("success"):
        game_state["chat_history"].append({"role": "user", "content": "Tento di fuggire dal combattimento!"})
        game_state["chat_history"].append({"role": "assistant", "content": res["dm_reply"]})
        # Se la fuga è riuscita, resetta lo stato combat
        if not res.get("combat", {}).get("active", True):
            game_state["combat"] = {"active": False}
        _update_diary_steps(game_state)
        _salva_su_disco()
        return jsonify(res)
    return jsonify({"success": False, "error": "Errore risoluzione fuga."}), 500


# diario
@app.route('/api/diary', methods=['GET'])
def get_diary():
    game_state = get_game_state()
    if not game_state["attivo"]:
        if not ripristina_stato_da_salvataggio():
            return jsonify({"success": False, "error": "Nessuna partita attiva."}), 400
            
    _update_diary_steps(game_state)
    return jsonify({
        "success": True,
        "diario": game_state["diario"]
    })


# salvataggio
@app.route('/api/save', methods=['POST'])
def save_game():
    game_state = get_game_state()
    if not game_state["attivo"]:
        if not ripristina_stato_da_salvataggio():
            return jsonify({"success": False, "error": "Nessuna partita attiva."}), 400
    
    _salva_su_disco()
    return jsonify({"success": True, "message": "Partita salvata con successo!"})


# caricamento
@app.route('/api/load', methods=['POST'])
def load_game():
    save_path = trova_file_salvataggio()
    if not save_path or not os.path.exists(save_path):
        return jsonify({"success": False, "error": "Nessun salvataggio trovato."}), 404
    
    with open(save_path, "r", encoding="utf-8") as f:
        save_data = json.load(f)
    
    new_state = {
        "chat_history": save_data.get("history", []),
        "diario": save_data.get("diario", {}),
        "personaggio": save_data.get("personaggio", ""),
        "mappa": save_data.get("mappa", ""),
        "tema": save_data.get("tema", "dark-fantasy"),
        "difficolta": save_data.get("difficolta", "normal"),
        "hp": save_data.get("hp", 100),
        "combat": save_data.get("combat", {"active": False}),
        "attivo": True,
        "posizione_attuale": save_data.get("posizione_attuale", {"zona_tag": "CENTRO", "nome_luogo": "", "is_zona_sicura": True, "nemico_zona": None}),
        "nemici_sconfitti": save_data.get("nemici_sconfitti", []),
        "progressione": save_data.get("progressione", []),
        "tappe_strutturate": save_data.get("tappe_strutturate", []),
        "tappa_attiva_idx": save_data.get("tappa_attiva_idx", 0)
    }
    
    set_game_state(new_state)
    game_state = get_game_state()
    _salva_su_disco()
    
    ultimo_dm = ""
    for msg in reversed(game_state["chat_history"]):
        if msg["role"] == "assistant":
            ultimo_dm = msg["content"]
            break
            
    # Rimuove eventuali tag residui per sicurezza
    ultimo_dm_pulito = re.sub(r'\[DANNI:\s*\d+\]', '', ultimo_dm).strip()
    
    return jsonify({
        "success": True,
        "personaggio": game_state["personaggio"],
        "mappa": game_state["mappa"],
        "ultimo_messaggio": ultimo_dm_pulito,
        "tema": game_state["tema"],
        "difficolta": game_state["difficolta"],
        "hp": game_state["hp"],
        "combat": game_state.get("combat", {"active": False}),
        "history": game_state["chat_history"]
    })


# controlla se esiste un save
@app.route('/api/check-save', methods=['GET'])
def check_save():
    save_path = trova_file_salvataggio()
    exists = save_path is not None and os.path.exists(save_path)
    return jsonify({"exists": exists})


# avvio server
if __name__ == '__main__':
    print("\n⚔️  MORPHEUS GENESIS  ⚔️")
    print("="*60)
    print("🌐 Server avviato su http://localhost:5000")
    print("   Apri il browser e vai su http://localhost:5000\n")
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)