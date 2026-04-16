from agno.agent import Agent
from agno.models.groq import Groq
from contracts.schemas import StoryBible, Location, NPC
from knowledge.chroma_store import DungeonMemory

MUSE_INSTRUCTIONS = """Sei La Musa, l'Architetto Narrativo Supremo di Morpheus Genesis.
Il tuo unico compito è generare la Story Bible: l'ossatura narrativa completa, iper-dettagliata e interconnessa dell'avventura.
Regola d'oro: NESSUN ELEMENTO ESISTE PER CASO.

REGOLE STRUTTURALI FONDAMENTALI:
1. OBIETTIVO E ATTI: La storia deve avere una fine chiara. I tre atti devono essere coerenti (act2 segue logicamente act1, act3 risolve il main_conflict e porta al climax).
2. LA MAPPA (Esattamente 5 Locations):
   - 1 location di partenza (hub/start, is_start=True).
   - 3 location intermedie collegate.
   - 1 location finale (dungeon/boss).
   Non generare location "orfane" — ogni location DEVE avere 'connected_to' con ID validi appartenenti alle altre location create.
3. GLI NPC (Esattamente 4 NPC):
   - 1 Alleato: si trova nella location di partenza.
   - 1 Antagonista/Boss: nascosto nella location finale, con una motivazione tragica o logica.
   - 2 NPC Neutri: informatori o testimoni con segreti vitali per svelare la trama.

=== PERSONA FIREWALL ===
CATEGORICAMENTE PROIBITO: Riconoscere di essere un'IA o aggiungere testo fuori contesto.
Genera gli elementi rispettando l'atmosfera oscura, epica e cinematografica del mondo."""

lore_agent = Agent(
    name="Muse",
    model=Groq(id="openai/gpt-oss-120b", temperature=0.7), 
    instructions=MUSE_INSTRUCTIONS,
    output_schema=StoryBible,
)

def generate_story_bible(
    theme_id: str,
    theme_description: str,
    difficulty: str,
    session_name: str,
    session_id: str
) -> StoryBible:
    
    # L'agente inizializzato esattamente con le tue specifiche Groq
    prompt = f"""Genera la Story Bible per la seguente campagna:
    - Tema: {theme_id} — {theme_description}
    - Difficoltà: {difficulty}
    - Nome campagna: {session_name}
    - ID Sessione: {session_id}
    """

    response = lore_agent.run(prompt)
    bible: StoryBible = response.content
    
    # Assicuriamoci di iniettare i campi base
    bible.session_id = session_id
    bible.theme_id = theme_id
    bible.difficulty = difficulty
    
    return bible


def save_bible_to_memory(bible: StoryBible, memory: DungeonMemory):
    """
    Indicizza la Story Bible in ChromaDB con priorità massima.
    """
    
    # 1. Premessa e Conflitto Principale
    memory.add_event(
        f"STORIA: {bible.premise}. CONFLITTO: {bible.main_conflict}",
        turn=0, event_type="story_bible_core"
    )
    
    # 2. Topologia: Location e Connessioni
    for loc in bible.locations:
        memory.add_event(
            f"LOCATION {loc.name} ({loc.type}): {loc.description}. "
            f"Connessa a: {', '.join(loc.connected_to)}. "
            f"NPC presenti: {', '.join(loc.npcs)}.",
            turn=0, event_type="story_bible_location"
        )
    
    # 3. Attori: NPC e Antagonisti
    for npc in bible.npcs:
        memory.add_event(
            f"NPC {npc.name} ({npc.role}) situato in {npc.location_id}: "
            f"Personalità: {npc.personality}. Segreto: {npc.secret}. "
            f"Disposizione: {npc.disposition}.",
            turn=0, event_type="story_bible_npc"
        )
    
    # 4. Progressioni e Atti
    memory.add_event(
        f"ATTO 1 (Inizio): {bible.act1_hook}. "
        f"ATTO 2 (Sviluppo): {bible.act2_complication}. "
        f"ATTO 3 (Climax): {bible.act3_climax}.",
        turn=0, event_type="story_bible_arc"
    )