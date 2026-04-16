from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Location:
    id: str                    # es. "taverna_del_corvo"
    name: str                  # es. "Taverna del Corvo Nero"
    type: str                  # "city" | "dungeon" | "wilderness" | "poi"
    description: str           # 2-3 righe descrizione atmosferica
    connected_to: list[str]    # id delle location adiacenti
    npcs: list[str]            # id degli NPC presenti
    is_start: bool = False
    is_discovered: bool = False

@dataclass
class NPC:
    id: str
    name: str
    role: str                  # es. "taverniere", "capo della guardia"
    personality: str           # 1 riga
    secret: str                # cosa sa che il giocatore non sa
    location_id: str
    disposition: str           # "friendly" | "neutral" | "hostile"

@dataclass
class StoryBible:
    # STRUTTURA NARRATIVA
    title: str                 # nome della campagna
    theme_id: str
    premise: str               # situazione iniziale in 2 righe
    main_conflict: str         # il problema centrale della storia
    resolution_hint: str       # come si potrebbe risolvere (vago)
    opening_cinematic: str = "" # <--- AGGIUNTO QUI: Monologo introduttivo
    
    # GEOGRAFIA — schema fisso: 1 hub + 3-5 location + 1 dungeon finale
    starting_location_id: str
    locations: list[Location] = field(default_factory=list)
    
    # PERSONAGGI — schema fisso: 1 alleato + 1 antagonista + 2-3 NPC neutri
    npcs: list[NPC] = field(default_factory=list)
    
    # ARCO NARRATIVO — 3 atti fissi
    act1_hook: str = ""        # come inizia l'avventura
    act2_complication: str = "" # il colpo di scena di metà storia
    act3_climax: str = ""      # la resa dei conti finale
    
    # META
    difficulty: str = "Normale"
    session_id: str = ""