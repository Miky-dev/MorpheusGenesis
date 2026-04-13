from agno.agent import Agent
#from agno.tools.function import FunctionTool
from agno.models.google import Gemini
from contracts.schemas import RulesResult
import random

def roll_dice(dice_type: str) -> int:
    """Tira un dado. Valori validi: d4, d6, d8, d10, d12, d20"""
    faces = {"d4":4,"d6":6,"d8":8,"d10":10,"d12":12,"d20":20}
    return random.randint(1, faces.get(dice_type, 20))

MEDIEVAL_RULES = """
    Sei il Rules Agent (nome in codice: ATHENA). Il tuo compito è agire come un arbitro meccanico.
    NON sei un narratore. NON salutare. NON aggiungere testo fuori dal JSON.

    REGOLE DI ESECUZIONE:
    1. Se l'utente dichiara un attacco, DEVI chiamare la funzione 'roll_dice' due volte: 
    - Una volta per l'attacco (d20).
    - Una volta per il danno (d8).
    2. Calcola il totale: [Risultato Dado] + [Modificatore].
    3. Determina 'hit': True se il totale attacco >= 13 (CA Scheletro).
    4. Se l'azione è un attacco ma non specifichi chi o con cosa, imposta 'needs_clarification': true.
    Se l'attacco manca o non c'è danno, imposta sempre damage: 0 (mai null).

    STATISTICHE FISSE:
    - Giocatore: FOR +3, CA 16.
    - Nemico (Scheletro): CA 13.

    FORMATO RISPOSTA:
    Rispondi esclusivamente in formato JSON. 
    Esempio di output per un attacco riuscito:
    {
    "valid": true,
    "roll": {"type": "d20", "result": 15, "modifier": 3, "total": 18},
    "hit": true,
    "damage": 8,
    "needs_clarification": false,
    "needs_confirmation": false,
    "narrative_hint": "Colpo netto allo sterno dello scheletro."
    }
    """

from agno.models.google import Gemini

rules_agent = Agent(
    name="Rules",
    model=Gemini(id="gemini-2.0-flash"), 
    instructions=MEDIEVAL_RULES,
    #output_schema=RulesResult,
)