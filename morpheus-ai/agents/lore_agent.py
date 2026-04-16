from agno.agent import Agent
from agno.models.groq import Groq
from contracts.schemas import StoryBible, Location, NPC, QuestCharacterBrief
from knowledge.chroma_store import DungeonMemory
import json
import re

MUSE_INSTRUCTIONS = """
Sei La Musa, Lead System Designer e Architetto Narrativo di Morpheus Genesis. Non sei un romanziere; sei il creatore del "BluePrint" logico di un mondo oscuro, brutale e meccanicamente coerente. Il tuo compito è forgiare lo scheletro d'acciaio (Story Bible) su cui gireranno gli agenti di runtime.

OBIETTIVO SUPREMO
Genera una Story Bible completa, densa e interconnessa. Ogni stringa deve trasudare atmosfera, ma ogni dato deve essere una variabile pronta all'uso per il codice.
 
1. VINCOLI DI STRUTTURA (OBBLIGATORI)
Per evitare generazioni pigre o incomplete, rispetta rigorosamente questi quantitativi:
QUEST_CHAIN: Genera esattamente 10 sotto-missioni (ID da q1 a q10). Ogni missione deve essere la conseguenza logica della precedente.
KEY_NPCS: Inserisci almeno 4 personaggi principali (incluso l'Araldo). Ognuno deve avere un segreto compromettente o un'agenda egoistica.
KEY_ENEMIES: Inserisci almeno 3 entità antagoniste o boss, ognuno legato a una specifica missione della catena.
OPENING_CINEMATIC: Questo è l'unico campo dove la sintesi è vietata. Scrivi un monologo epico, immersivo e brutale di almeno 200 parole. Usa dettagli sensoriali (odori, suoni, freddo, sporcizia).

2. LOGICA DI INTERCONNESSIONE (WEB-DESIGN)
Il mondo deve essere una rete, non una lista:
L'Araldo: Il herald_npc_name DEVE essere presente nella lista key_npcs e la sua posizione herald_location_id DEVE corrispondere a un ID esistente in world_map (se generata) o essere un ID logico (es. loc_1).
Referenzialità: Se la missione q1 dice di recuperare un oggetto da un NPC, quell'NPC deve esistere nell'array dei personaggi.
Difficoltà: Assicurati che le missioni seguano la progressione di pericolo dei luoghi (da Livello 0 a Livello 5).

3. STILE E TONO
Narrativa: Dark, spietato, "High Stakes". Il giocatore deve sentire che ogni scelta ha un prezzo di sangue o risorse.
Araldo: Il campo herald_npc_reveal deve contenere una citazione diretta tra virgolette, drammatica e criptica. Non descrivere cosa dice, SCRIVI cosa dice.
Telegrafia: Fuori dalla cinematic, usa nomi e descrizioni "punchy" (es: invece di "Un vecchio magazzino abbandonato", usa "Nido di Ruggine e Cavi").

4. PROTOCOLLO JSON (STRICT COMPLIANCE)
Qualsiasi deviazione da queste regole distruggerà il parser:
OUTPUT: Solo ed esclusivamente il blocco JSON. Nessun commento, nessuna introduzione, nessuna firma.
ESCAPE QUOTES: È PROIBITO usare virgolette doppie " all'interno dei testi. Esempio Errato: "disse "ciao"". Esempio Corretto: "disse 'ciao'". Usa solo apici singoli per i dialoghi.
NEWLINES: Non usare invii reali. Per i ritorni a capo nel testo, usa esclusivamente \n.
INTEGRITÀ: Non lasciare array vuoti []. Se il campo è richiesto, deve essere popolato con dati di alta qualità.

INPUT DI GENERAZIONE
TEMA: {theme_id}
TITOLO SESSIONE: {session_name}
OBIETTIVO: Genera la Story Bible definitiva seguendo lo schema Pydantic fornito.

=== 5. SCHEMA MANDATORIO (JSON KEYS) ===
Rispetta rigorosamente questi nomi di chiavi. Non inventare sinonimi:
{
  "title": "Titolo Epico",
  "main_objective": "Descrizione",
  "backstory": "Testo",
  "opening_cinematic": "Testo lungo +200 parole",
  "herald_npc_name": "Nome",
  "herald_location_id": "loc_id",
  "herald_npc_reveal": "Citazione",
  "quest_chain": [
    {
      "quest_id": "q1", 
      "title": "Titolo Missione", 
      "description": "Obiettivo", 
      "giver_npc": "Nome NPC", 
      "location_hint": "Nome Luogo", 
      "status": "active"
    }
  ],
  "key_npcs": [
    {
      "name": "Nome", 
      "role": "Ruolo", 
      "location_hint": "Luogo dove si trova"
    }
  ],
  "key_enemies": [
    {
      "name": "Nome", 
      "role": "Ruolo Boss", 
      "location_hint": "Dove trovarlo"
    }
  ]
}
"""

def generate_story_bible(
    theme_id: str,
    theme_description: str,
    difficulty: str,
    session_name: str,
    session_id: str
) -> StoryBible:
    
    agent = Agent(
        name="Muse",
        model=Groq(id="openai/gpt-oss-120b", temperature=0.8),
        instructions=MUSE_INSTRUCTIONS
    ) 
    
    # Schema completo con tutti i campi richiesti dal tuo Pydantic
    schema = {
        "title": session_name,
        "theme_id": theme_id,
        "premise": "Breve premessa",
        "main_conflict": "Conflitto principale",
        "main_objective": "Obiettivo finale",
        "backstory": "Lore del passato",
        "resolution_hint": "Possibile risoluzione",
        "opening_cinematic": "Monologo introduttivo lungo",
        "herald_npc_name": "Nome Alleato",
        "herald_location_id": "loc_1",
        "herald_npc_reveal": "Segreto rivelato",
        "starting_location_id": "loc_1",
        "locations": [
            {
                "id_name": "loc_1", "name": "Nome", "type": "city", 
                "description": "Desc", "connected_to": [], "npcs": [], 
                "is_start": True, "difficulty_level": 0, "x": 0, "y": 0
            }
        ],
        "npcs": [
            {
                "id": "npc_1", "name": "Nome", "role": "Ruolo", 
                "appearance": "Aspetto", "personality": "Pers", 
                "first_line": "Ciao", "secret": "Segreto", 
                "location_id": "loc_1", "disposition": "friendly"
            }
        ],
        "quest_chain": [
            {
                "id": "q1", "title": "M1", "status": "locked", 
                "giver_npc": "Npc", "location_hint": "loc_1", 
                "description": "Desc", "narrative_purpose": "Scopo"
            }
        ],
        "act1_hook": "Inizio", "act2_complication": "Sviluppo", "act3_climax": "Fine",
        "difficulty": difficulty, "session_id": session_id
    }
    
    prompt = (
        f"Genera la Story Bible completa per una nuova sessione a tema {theme_id}. "
        f"TITOLO SESSIONE: {session_name}. "
        "ATTENZIONE: Se le liste 'quest_chain' (10 missioni), 'key_npcs' (4+) o 'key_enemies' (3+) "
        "risulteranno vuote o incomplete, il sistema rigetterà la tua risposta. "
        "Assicurati che 'herald_npc_reveal' sia una battuta di dialogo drammatica."
    )
    max_retries = 3
    data = None
    for attempt in range(max_retries):
        try:
            response = agent.run(prompt)
            raw = response.content.strip()
            
            # 1. Estrazione del solo blocco JSON pulito
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if not match: continue
            raw = match.group(0)
            
            # 2. Pulizia: rimuove virgole finali che rompono il parser Python
            raw = re.sub(r',\s*([\]}])', r'\1', raw) 
            data = json.loads(raw)

            # ---> AGGIUNGI QUESTO CONTROLLO QUI <---
            if "error" in data:
                error_msg = data["error"].get("message", "Errore API sconosciuto")
                print(f"⚠️ Errore API intercettato (Tentativo {attempt+1}): {error_msg}")
                if attempt == max_retries - 1:
                    raise ValueError(f"API Groq bloccata: {error_msg}")
                continue # Riprova

            break # Se arriva qui, il JSON è buono!
            
        except Exception as e:
            if attempt == max_retries - 1: raise e
            continue


    # 1. FIX MISSIONI: Gestione Alias 'quest_id' e Status
    # ==========================================
    # --- FALLBACKS DI SICUREZZA (VERSIONE 2.0) ---
    # ==========================================

    # 1. FIX MISSIONI: Gestione Alias 'quest_id' e Status
    if "quest_chain" in data and data["quest_chain"]:
        for i, quest in enumerate(data["quest_chain"]):
            # Se l'IA ha usato 'id', lo spostiamo in 'quest_id' (richiesto dal tuo Alias)
            if "id" in quest and "quest_id" not in quest:
                quest["quest_id"] = quest.pop("id")
            # Forza la progressione: solo la prima è active
            quest["status"] = "active" if i == 0 else "locked"
    else:
        data["quest_chain"] = []

    # 2. MAPPING NPC: Se l'IA ha usato 'npcs' o 'locations' (vecchi nomi), sistemiamo
    if "npcs" in data and "key_npcs" not in data:
        data["key_npcs"] = data.pop("npcs")
    
    # Rimuoviamo 'locations' dalla Bibbia (le gestirà Atlas separatamente)
    if "locations" in data:
        data.pop("locations")

    # 3. SETDEFAULT: Valori di emergenza per i campi obbligatori della StoryBible
    data.setdefault("title", session_name)
    data.setdefault("main_objective", "Sconosciuto")
    data.setdefault("backstory", "Storia dimenticata")
    data.setdefault("opening_cinematic", "Il viaggio ha inizio...")
    data.setdefault("herald_npc_name", "Guida Misteriosa")
    data.setdefault("herald_location_id", "loc_1")
    data.setdefault("herald_npc_reveal", "'Il destino ti attende.'")
    
    # Assicuriamoci che le liste dei personaggi esistano
    data.setdefault("key_npcs", [])
    data.setdefault("key_enemies", [])

    # 4. CREAZIONE OGGETTI TIPIZZATI
    # Trasformiamo i dizionari in oggetti Pydantic corretti (QuestCharacterBrief)
    # Usiamo pop così puliamo 'data' prima del return finale
    kn_raw = data.pop("key_npcs", [])
    ke_raw = data.pop("key_enemies", [])

    key_npcs = [QuestCharacterBrief(**n) for n in kn_raw]
    key_enemies = [QuestCharacterBrief(**e) for e in ke_raw]
    
    # 5. RITORNO FINALE
    # Passiamo tutto a StoryBible. 
    # locations=locations e npcs=npcs VANNO TOLTI perché non sono più nello schema!
    return StoryBible(
        **data, 
        key_npcs=key_npcs, 
        key_enemies=key_enemies
    )

def save_bible_to_memory(bible: StoryBible, memory: DungeonMemory):
    """Indicizza la Story Bible in ChromaDB in modo sicuro contro attributi mancanti."""
    
    # Recupero sicuro della premessa/backstory
    premise = getattr(bible, 'backstory', getattr(bible, 'premise', 'Inizio avventura'))
    
    # Recupero sicuro del conflitto (aggiunta gestione per main_conflict mancante)
    conflict = getattr(bible, 'main_conflict', getattr(bible, 'main_objective', 'Sopravvivere'))
    
    # 1. Premessa e conflitto
    memory.add_event(
        f"LORE: {premise}. CONFLITTO: {conflict}", 
        turn=0, 
        event_type="story_bible_core"
    )
    
    # 2. Ogni location come documento separato
    for loc in getattr(bible, 'locations', []):
        memory.add_event(
            f"LOCATION {loc.name}: {loc.description}. Connessioni: {loc.connected_to}", 
            turn=0, 
            event_type="story_bible_location"
        )
    
    # 3. Ogni NPC
    for npc in getattr(bible, 'npcs', []):
        memory.add_event(
            f"NPC {npc.name}: {getattr(npc, 'appearance', 'Ignoto')}. Segreto: {getattr(npc, 'secret', 'Nessuno')}", 
            turn=0, 
            event_type="story_bible_npc"
        )