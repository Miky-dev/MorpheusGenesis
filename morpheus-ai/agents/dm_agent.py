from agno.agent import Agent
from agno.models.groq import Groq
from contracts.schemas import StoryScene
from agents.rules_agent import rules_agent
from agents.lore_agent import lore_agent

def ask_rules_agent(action: str) -> str:
    """
    Usa questo strumento se l'azione del giocatore richiede l'applicazione di regole di gioco.
    Esempi: attaccare, tirare dadi, compiere prove di forza o abilità.
    Restituisce l'esito meccanico e matematico dell'azione.
    """
    response = rules_agent.run(action)
    return str(getattr(response, 'content', response))

def ask_lore_agent(query: str) -> str:
    """
    Usa questo strumento se il giocatore vuole parlare con un NPC, leggere un testo antico o indagare sulla lore del mondo.
    Restituisce informazioni di background, segreti e le risposte dei personaggi.
    """
    response = lore_agent.run(query)
    return str(getattr(response, 'content', response))


DM_INSTRUCTIONS = """
Sei l'Orchestratore e Narratore (Dungeon Master) di Morpheus Genesis.
Sei il cuore del sistema e l'unico agente che genera l'output finale mostrato ai giocatori.

IL TUO FLUSSO DI LAVORO:
1. Ricevi l'input del giocatore e il contesto dello stato del gioco (coordinate, loot, ecc.).
2. Capisci l'intento dell'azione.
3. Se l'azione richiede regole (combattimenti, prove), CHIAMA LO STRUMENTO `ask_rules_agent`.
4. Se l'azione riguarda parlare con un NPC o scoprire la lore, CHIAMA LO STRUMENTO `ask_lore_agent`.
5. Se l'azione è semplice (es. "Apro la porta", "Mi sposto a nord"), puoi risolvere senza chiamare strumenti, descrivendo direttamente il risultato basandoti sulle coordinate/connessioni lette dallo stato.
6. Alla fine, unisci TUTTE le informazioni raccolte in una narrazione fluida ed epica in lingua italiana.

=== DIRETTIVA LINGUISTICA E STILE ===
- RISPONDI ESCLUSIVAMENTE IN LINGUA ITALIANA.
- La narrazione deve essere coinvolgente. Non elencare mai statistiche o ID tecnici.
- Se l'azione genera loot (fornito dal contesto), descrivilo in modo sensoriale ("Trovi una spada logora dal tempo...").

=== STORICO E MEMORIA ===
Hai accesso allo storico immediato della chat. Mantieni coerenza con le azioni precedenti.

=== FORMATO RISPOSTA (JSON STRICT) ===
Devi SEMPRE rispondere con un JSON compatibile con lo schema richiesto (StoryScene).
"""

dm_agent = Agent(
    name="Orchestrator_DM",
    model=Groq(id="openai/gpt-oss-20b", temperature=0.7),
    instructions=DM_INSTRUCTIONS,
    tools=[ask_rules_agent, ask_lore_agent],
    # output_schema rimosso: Groq non supporta JSON mode + tool calling contemporaneamente.
    # La validazione dello schema StoryScene è gestita da safe_agent_run() in utils.py.
    num_history_messages=5
)