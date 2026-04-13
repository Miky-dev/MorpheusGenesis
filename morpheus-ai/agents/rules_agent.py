from agno.agent import Agent
from agno.tools.function import FunctionTool
from contracts.schemas import RulesResult
import random

def roll_dice(dice_type: str) -> int:
    """Tira un dado. Valori validi: d4, d6, d8, d10, d12, d20"""
    faces = {"d4":4,"d6":6,"d8":8,"d10":10,"d12":12,"d20":20}
    return random.randint(1, faces.get(dice_type, 20))

MEDIEVAL_RULES = """
Sei il Rules Agent. Validi azioni D&D 5e in un contesto medievale.

REGOLE COMBATTIMENTO:
- Attacco melee: tira d20 + FOR modifier. Se >= CA nemico: colpisce.
- Spada lunga: danno 1d8 + FOR modifier
- Critico su 20 naturale: danno raddoppiato
- Fallimento su 1 naturale

STATISTICHE DEFAULT PERSONAGGIO:
- FOR: +3, DES: +1, CA: 16, HP: 24

NEMICO DEFAULT (scheletro):
- CA: 13, HP: 20

Rispondi SEMPRE con JSON che rispetta questo schema esatto:
{
  "valid": true,
  "roll": {"type": "d20", "result": N, "modifier": 3, "total": N},
  "hit": true,
  "damage": N,
  "needs_clarification": false,
  "needs_confirmation": false,
  "narrative_hint": "breve hint per il DM"
}
Se l'azione e ambigua, setta needs_clarification: true e damage: 0.
"""

rules_agent = Agent(
    name="Rules",
    instructions=MEDIEVAL_RULES,
    tools=[FunctionTool(roll_dice)],
)