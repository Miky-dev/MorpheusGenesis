from agno.agent import Agent
from agno.models.groq import Groq
from contracts.schemas import WorldMap, NavigationResult

# ==========================================
# 1. ATLAS IL CREATORE (Usato solo 1 volta all'inizio)
# ==========================================
ATLAS_GENERATOR_INSTRUCTIONS = """
Sei Atlas, l'Agente Cartografo di Morpheus Genesis.
Il tuo compito è generare la geografia iniziale della regione giocabile.

REGOLE DI CREAZIONE DELLA MAPPA:
1. Genera esattamente tra le 5 e le 7 località (Locations).
2. Spazio 2D: Usa coordinate X e Y da 0 a 100.
3. Connessioni Logiche: Compila 'connected_to' inserendo gli ID delle località vicine. 
4. Coerenza Tematica: Adatta i nomi al Tema scelto.
5. Scegli uno 'spawn_location_id' coerente con l'inizio di un'avventura.
6. PROGRESSIONE: Assegna un 'difficulty_level' (0-5). Lo spawn è livello 0, i vicini 1, e così via a salire.

Rispondi ESCLUSIVAMENTE con un JSON valido che rispetti lo schema WorldMap. Nessun commento extra.
LINGUA: Rispondi esclusivamente in LINGUA ITALIANA. Ogni nome di luogo e descrizione deve essere in italiano evocativo.
"""

map_generator_agent = Agent(
    name="Atlas_Generator",
    model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0.5), # Temp leggermente più alta per inventare nomi
    instructions=ATLAS_GENERATOR_INSTRUCTIONS,
    output_schema=WorldMap,
)

# ==========================================
# 2. ATLAS IL NAVIGATORE (Usato ad ogni turno)
# ==========================================
ATLAS_RUNTIME_INSTRUCTIONS = """
Sei Atlas, l'Agente Navigatore di Morpheus Genesis.
Il tuo compito NON è narrare, ma fare da arbitro spaziale: decidi se il giocatore può muoversi o meno.

RICEVERAI IN INPUT: Azione del giocatore, Posizione attuale, Location conosciute.

=== 1. REGOLE DI VALIDAZIONE ===
- CONTROLLO CONNESSIONE: Movimento permesso SOLO verso luoghi connessi a quello attuale.
- NEBBIA DI GUERRA: Se il luogo è connesso ma NON è tra le 'Known Locations', il movimento fallisce.
- MOVIMENTO FITTIZIO: Se l'azione NON implica spostamento (es. "Attacco", "Parlo", "Esploro la stanza"), imposta success=True e new_location_id=null.

=== 2. SCOPERTA LUOGHI ===
- Se viene menzionato esplicitamente un nuovo luogo nei dialoghi, inserisci il suo ID in 'discovered_ids'.

Rispondi ESCLUSIVAMENTE con un JSON valido per NavigationResult.
"""

map_navigator_agent = Agent(
    name="Atlas_Navigator",
    model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0.1), # Analitico e freddo
    instructions=ATLAS_RUNTIME_INSTRUCTIONS,
    output_schema=NavigationResult,
)