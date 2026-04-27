from agno.agent import Agent
from agno.models.groq import Groq
from contracts.schemas import StoryBible, Location, NPC, QuestCharacterBrief
from knowledge.chroma_store import DungeonMemory
from utils import parse_json_response
import json
import re

MUSE_INSTRUCTIONS = """
Sei La Musa, Lead System Designer e Architetto Narrativo di Morpheus Genesis. Non sei un romanziere; sei il creatore del "BluePrint" logico di un mondo coerente, ma con una forte impronta stilistica. Il tuo compito è forgiare lo scheletro d'acciaio (Story Bible) su cui gireranno gli agenti di runtime.

=== 1. STILE E TONO (DIRETTIVA SUPREMA) ===
MOOD RICHIESTO: {narrative_style}
GUIDA STILISTICA: {style_guidelines}

=== 2. VINCOLI DI STRUTTURA (OBBLIGATORI) ===
Per evitare generazioni pigre o incomplete, rispetta rigorosamente questi quantitativi:
QUEST_CHAIN: Genera esattamente 10 sotto-missioni (ID da q1 a q10). Ogni missione deve essere la conseguenza logica della precedente.
KEY_NPCS: Inserisci almeno 4 personaggi principali (incluso l'Araldo). Ognuno deve avere un segreto o un'agenda coerente con il mood.
KEY_ENEMIES: Inserisci almeno 3 entità antagoniste o boss, ognuno legato a una specifica missione della catena.
OPENING_CINEMATIC: Questo è l'unico campo dove la sintesi è vietata. Scrivi un monologo epico e immersivo di almeno 200 parole che introduca il giocatore al mondo seguendo il MOOD RICHIESTO.

=== 3. LOGICA DI INTERCONNESSIONE ===
- L'Araldo: Il herald_npc_name DEVE essere presente nella lista key_npcs.
- Referenzialità: Se la missione q1 cita un oggetto o un NPC, questi devono essere definiti nei relativi array.
- Difficoltà: Assicurati che le missioni seguano la progressione di pericolo dei luoghi (da Livello 0 a Livello 5).

=== 4. PROTOCOLLO JSON (STRICT COMPLIANCE) ===
- LINGUA: Rispondi esclusivamente in LINGUA ITALIANA. Ogni campo testuale deve essere in italiano accurato ed evocativo.
- OUTPUT: Solo ed esclusivamente il blocco JSON. Nessun commento.
- JSON KEYS: Usa SEMPRE doppi apici " per le chiavi.
- ESCAPE QUOTES: Usa solo apici singoli ' all'interno dei testi.
- NEWLINES: Usa esclusivamente \\n per i ritorni a capo nel testo.

=== 5. INPUT DI GENERAZIONE ===
TEMA: {theme_id}
TITOLO SESSIONE: {session_name}
OBIETTIVO: Genera la Story Bible definitiva seguendo lo schema Pydantic fornito.

=== 6. SCHEMA MANDATORIO (JSON KEYS) ===
{{
  "title": "Titolo Viscerale e Unico ,",
  "narrative_style": "{narrative_style}",
  "main_objective": "Descrizione",
  "backstory": "Testo",
  "opening_cinematic": "Testo lungo +200 parole",
  "herald_npc_name": "Nome",
  "herald_location_id": "loc_id",
  "herald_npc_reveal": "Citazione drammatica coerente col mood",
  "quest_chain": [
    {{ "quest_id": "q1", "title": "...", "description": "...", "giver_npc": "...", "location_hint": "...", "status": "active" }}
  ],
  "key_npcs": [
    {{ "name": "...", "role": "...", "location_hint": "..." }}
  ],
  "key_enemies": [
    {{ "name": "...", "role": "...", "location_hint": "..." }}
  ]
}}
"""

STYLISTIC_MAPPING = {
    "Oscuro": "Tono cupo, brutale, spietato. Ambientazioni oppressive, pericoli mortali e scelte morali difficili. Il giocatore deve sentire che ogni scelta ha un prezzo di sangue.",
    "Eroico": "Tono epico, ispiratore, avventuroso. Lotte tra il bene e il male, atti di coraggio, onore e trionfo finale. Linguaggio magniloquente e nobile.",
    "Divertente": "Tono ironico, assurdo, grottesco. Dialoghi brillanti, situazioni bizzarre, nemici ridicoli ma pericolosi e umorismo nero. Non aver paura dell'esagerazione.",
    "Tragico": "Tono melancolico, fatale, triste. Senso di ineluttabilità, perdite personali, bellezza in decadenza ed eroismo destinato al fallimento.",
    "Misterioso": "Tono criptico, noir, investigativo. Enigmi, segreti nascosti, atmosfera di sospetto e colpi di scena. Nulla è come sembra.",
    "Guerra": "Tono militare, crudo, tattico. Conflitti di massa, campi di battaglia devastati, onore tra commilitoni e il peso del comando.",
    "Filosofico": "Tono intellettuale, astratto, metaforico. Domande sull'esistenza, morali profonde, simbolismo e riflessioni sul senso del viaggio.",
    "Romantico": "Tono passionale, sentimentale, cavalleresco. Relazioni intense, promesse d'amore, conflitti del cuore e bellezza struggente."
}

def generate_story_bible(
    theme_id: str,
    theme_description: str,
    narrative_style: str,
    difficulty: str,
    session_name: str,
    session_id: str
) -> StoryBible:
    
    style_guidelines = STYLISTIC_MAPPING.get(narrative_style, STYLISTIC_MAPPING["Oscuro"])
    
    session_display_name = session_name if session_name else "DA GENERARE (Titolo Fantastico Originale)"

    formatted_instructions = MUSE_INSTRUCTIONS.format(
        narrative_style=narrative_style,
        style_guidelines=style_guidelines,
        theme_id=theme_id,
        session_name=session_display_name
    )

    agent = Agent(
        name="Muse",
        model=Groq(id="openai/gpt-oss-120b", temperature=0.85), # Temperatura leggermente alzata per favorire la creatività del mood
        instructions=formatted_instructions
    ) 
    
    # Schema completo con tutti i campi richiesti dal tuo Pydantic
    schema = {
        "title": session_name,
        "theme_id": theme_id,
        "narrative_style": narrative_style,
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
        f"MOOD: {narrative_style}. "
        f"TITOLO: {session_display_name}. "
        "Assicurati che OGNI elemento rifletta il tono scelto e che il titolo sia unico e inerente alla storia."
    )
    max_retries = 3
    data = None
    for attempt in range(max_retries):
        try:
            response = agent.run(prompt)
            raw = response.content.strip()
            
            data = parse_json_response(raw, "Muse StoryBible")
            
            if data is None:
                print(f"⚠️ Errore di parsing JSON (Tentativo {attempt+1})")
                if attempt == max_retries - 1:
                    raise ValueError("Impossibile parsare la Story Bible. L'AI ha restituito un formato non valido.")
                continue

            # ---> CONTROLLO ERRORI API <---
            if "error" in data:
                error_msg = data["error"].get("message", "Errore API sconosciuto")
                print(f"⚠️ Errore API intercettato (Tentativo {attempt+1}): {error_msg}")
                if attempt == max_retries - 1:
                    raise ValueError(f"API bloccata: {error_msg}")
                continue # Riprova

            break # Se arriva qui, il JSON è buono!
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"DEBUG: Fallimento parsing JSON al tentativo {attempt+1}")
                raise e
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
    # Usiamo session_name solo se non è nullo, altrimenti un titolo di placeholder
    default_title = session_name if session_name else f"Il Mito di {theme_id}"
    data.setdefault("title", default_title)
    data.setdefault("main_objective", "Sconosciuto")
    data.setdefault("backstory", "Storia dimenticata")
    data.setdefault("opening_cinematic", "Il viaggio ha inizio...")
    data.setdefault("herald_npc_name", "Guida Misteriosa")
    data.setdefault("herald_location_id", "loc_1")
    data.setdefault("herald_npc_reveal", "'Il destino ti attende.'")
    data.setdefault("narrative_style", narrative_style)
    
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
    style = getattr(bible, 'narrative_style', 'Oscuro')
    memory.add_event(
        f"LORE: {premise}. CONFLITTO: {conflict}. MOOD: {style}", 
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