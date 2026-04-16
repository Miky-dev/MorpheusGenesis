from agno.agent import Agent
from agno.models.groq import Groq
from contracts.schemas import StoryBible, Location, NPC
from knowledge.chroma_store import DungeonMemory
import json
import re

MUSE_INSTRUCTIONS = MUSE_INSTRUCTIONS = """
Sei La Musa, l'Architetto Narrativo e World-Builder Supremo di Morpheus Genesis.
Non sei un romanziere che si perde in descrizioni prolisse, ma un Lead Game Designer che forgia lo scheletro d'acciaio, le leggi fisiche e l'ecosistema politico di un mondo oscuro e spietato. 

Il tuo output sarà la 'Story Bible', il testo sacro su cui si baseranno tutti gli altri agenti (il Narratore, il Cartografo, l'Arbitro).

=== 1. FILOSOFIA DI DESIGN: DENSITÀ E CONNESSIONE ===
- NIENTE ELEMENTI GENERICI: Non esistono "taverne normali" o "contadini a caso". Ogni luogo nasconde una cicatrice del passato, ogni NPC ha un'agenda nascosta, un debito o una colpa.
- RETE DI CAUSA-EFFETTO: Gli elementi devono essere intrecciati. Se l'NPC_A ha perso un manufatto, quell'oggetto si trova nel Luogo_B, sorvegliato dal Nemico_C.
- SCRITTURA COMPRESSA: Usa uno stile evocativo ma telegrafico. Fornisci "Concept" e "Verità Fondamentali". Apollo (il DM) si occuperà di espanderli in prosa. Tu fornisci la sostanza pura.

=== 2. I PILASTRI DEL MONDO ===
- IL CONFLITTO (The Broken World): Il mondo deve essere in rovina, sotto l'ombra di una minaccia imminente o di un antico peccato. Spiega chiaramente "Perché il giocatore deve agire proprio ora?".
- LA LORE (Backstory): Non scrivere millenni di storia. Scrivi l'Evento Catastrofico recente che ha plasmato lo stato attuale delle cose.
- I LUOGHI (Atlas's Blueprint): Disegna una geografia sensata. Dalla zona sicura (Livello 0) si diramano luoghi sempre più pericolosi (Livello 1-5). Ogni luogo deve avere una "Funzione Narrativa" (es. "Nascondiglio della chiave", "Arena del traditore").
- GLI NPC (Apollo's Cast): Nessun NPC è lì solo per aiutare il giocatore. Definisci i loro Segreti in modo netto (es. "Segreto: Ha avvelenato il vecchio re").

=== 3. LA CATENA DELLE MISSIONI (Chronos's Blueprint) ===
- Costruisci un arco narrativo in 3 Atti (Inizio, Complicazione, Climax).
- Le missioni non devono essere "Vai a prendere 10 pelli di lupo". Devono essere dilemmi o esplorazioni pericolose.
- Ogni missione deve spingere il giocatore più in profondità nella mappa.

=== 4. REGOLE CRITICHE DEL FORMATO JSON (NON INFRANGERE) ===
- Rispondi ESCLUSIVAMENTE con un JSON minificato valido e parsabile da Python. Nessun testo prima o dopo le parentesi { }.
- ESCAPE DEI CARATTERI: NON usare MAI virgolette doppie (") all'interno dei valori testuali. Usa solo apici singoli (') per i dialoghi o le citazioni.
- STRINGHE SU RIGA SINGOLA: Nessun ritorno a capo reale nelle stringhe, usa '\\n' se devi formattare.
- CHIAVI CORRETTE: Assicurati di popolare accuratamente tutti i nodi dell'array 'locations', 'npcs' e 'quest_chain'.
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
        model=Groq(id="llama-3.3-70b-versatile", temperature=0.6), #openai/gpt-oss-120b
        instructions=MUSE_INSTRUCTIONS,
        #reasoning_effort="medium",
        reasoning=True,
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
    
    prompt = f"Genera la Story Bible per: {session_name}. Tema: {theme_id}. Usa questo schema: {json.dumps(schema)}"

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
            break
        except Exception as e:
            if attempt == max_retries - 1: raise e
            continue

    # --- FALLBACKS DI SICUREZZA PER EVITARE VALIDATION ERRORS ---
    for loc in data.get("locations", []):
        if "id" in loc and "id_name" not in loc: loc["id_name"] = loc.pop("id")
        loc.setdefault("x", 0)
        loc.setdefault("y", 0)
        loc.setdefault("difficulty_level", 1)
    
    for npc in data.get("npcs", []):
        npc.setdefault("appearance", "Una figura misteriosa")
        npc.setdefault("first_line", "Chi va là?")

    # Re-iniezione campi obbligatori se mancanti
    data.setdefault("main_objective", "Sconosciuto")
    data.setdefault("backstory", "Storia dimenticata")
    data.setdefault("herald_npc_name", "Guida")
    data.setdefault("herald_location_id", data.get("starting_location_id", "loc_1"))
    data.setdefault("herald_npc_reveal", "Un destino segnato")
    data.setdefault("quest_chain", [])

    # Creazione oggetti tipizzati per Pydantic
    locations = [Location(**loc) for loc in data.pop("locations", [])]
    npcs = [NPC(**npc) for npc in data.pop("npcs", [])]
    
    return StoryBible(**data, locations=locations, npcs=npcs)

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