import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from knowledge.chroma_store import DungeonMemory

# test manuale
mem = DungeonMemory("test_session")
mem.add_event("Il giocatore ha incontrato il re scheletrico nella sala del trono", turn=1, event_type="npc")
print(mem.query("chi ho incontrato nel castello?"))  # deve restituire l'evento