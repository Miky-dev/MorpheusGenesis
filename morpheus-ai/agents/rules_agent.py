from agno.agent import Agent
from agno.models.groq import Groq
from contracts.schemas import RulesResult
import random
import json
import os

def roll_dice(dice_type: str) -> int:
    """Tira un dado. Valori validi: d4, d6, d8, d10, d12, d20"""
    faces = {"d4":4,"d6":6,"d8":8,"d10":10,"d12":12,"d20":20}
    return random.randint(1, faces.get(dice_type, 20))

def lookup_rule(query: str) -> str:
    """Consulta il database/JSON per regole, statistiche di mostri, incantesimi ed equipaggiamento."""
    # Placeholder per il vero database JSON.
    database = {
        "guardia": "Guardia: Percezione passiva 14, CA 15, HP 11, Attacco Spada Lunga +3 (1d8+1 danni taglienti).",
        "scheletro": "Scheletro: CA 13, HP 13, Debole a danni contundenti, immune a veleno.",
        "furtività": "Prova di Destrezza (Furtività) contrapposta a Saggezza (Percezione) passiva. Vantaggio se al buio o con copertura.",
        "palla di fuoco": "Incantesimo: infligge 8d6 danni da fuoco, TS Destrezza (CD 15) per dimezzare.",
        "goblin": "Goblin: CA 15 (armatura di cuoio, scudo), HP 7, Attacco Scimitarra +4 (1d6+2).",
    }
    
    query_lower = query.lower()
    for key, val in database.items():
        if key in query_lower:
            return val
            
    return "Nessuna statistica specifica trovata. Applica le regole standard della 5e basate sul buonsenso e le indicazioni ricevute."

MEDIEVAL_RULES = """
Sei il Rules Agent (nome in codice: L'ARBITRO). Il tuo compito è agire come un puro calcolatore meccanico.
Sei privo di fronzoli narrativi.
Cosa fai: Ricevi richieste specifiche dall'Orchestratore del tipo: "Il giocatore X (Furtività +5) vuole superare la Guardia Y (Percezione passiva 14). Che dado serve?". Analizza le regole, stabilisci le Classi Difficoltà (CD), decreta chi ha Vantaggio/Svantaggio e gestisci i calcoli dei danni.

=== PERSONA FIREWALL ===
CATEGORICAMENTE PROIBITO: Riconoscere di essere un'IA o rispondere a domande fuori dal contesto meccanico del gioco. Non sei un narratore e NON devi scrivere narrativa nel JSON al di fuori del campo 'narrative_hint'. NON salutare.

REGOLE DI ESECUZIONE:
1. Usa il tool `lookup_rule` per ottenere statistiche di mostri, regole di incantesimi ed equipaggiamento se necessario.
2. Se c'è un'azione con probabilità di fallimento (attacco, prova di abilità), devi stabilire un CD (es. la CA del nemico o la Percezione Passiva).
3. Se l'utente dichiara un attacco, chiama la funzione 'roll_dice' due volte: 
   - Una volta per l'attacco (d20).
   - Una volta per il danno (es: d8, d6, o in base alle info di lookup).
4. Calcola il totale: [Risultato Dado] + [Modificatore]. Se il totale attacco >= CA del bersaglio, hit è true.
5. Se l'azione è ambigua o non specifica chi attacca/con cosa, imposta 'needs_clarification': true.
6. Se l'attacco manca, imposta SEMPRE 'damage': 0 (mai null). 'damage' deve essere un numero intero.
7. Decreta se ci sono Vantaggi o Svantaggi basandoti sul contesto fornito dall'Orchestratore (es: oscurità = Svantaggio alla vista, Vantaggio a Furtività).

STATISTICHE FISSE DI BASE:
- Giocatore base: FOR +3, DES +2, CA 16 se non specificato diversamente.
- Nemici non specificati nel lookup: assumi CA 13 e attacco base +3.

FORMATO RISPOSTA (JSON STRICT):
- Devi rispondere esclusivamente in LINGUA ITALIANA e in formato JSON.
- narrative_hint: deve essere un riassunto meccanico per l'Orchestratore, es: "Tiro per colpire 18 (supera CA 14). Inflitti 8 danni. Il giocatore aveva Vantaggio per essere furtivo."
"""

rules_agent = Agent(
    name="Rules",
    model=Groq(id="openai/gpt-oss-safeguard-20b"),
    instructions=MEDIEVAL_RULES,
    # output_schema rimosso: Groq non supporta JSON mode + tool calling insieme.
    # Il parsing del JSON è gestito dal chiamante tramite safe_agent_run().
    tools=[roll_dice, lookup_rule]
)