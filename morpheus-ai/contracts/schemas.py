from pydantic import BaseModel, Field
from typing import List, Optional, Any


# ==========================================
# SCHEMA PER IL RULES AGENT (MEMBRO A)
# ==========================================
class DiceRoll(BaseModel):
    type: str = Field(description="Tipo di dado tirato, es: 'd20'")
    result: int = Field(description="Il risultato puro uscito sulla faccia del dado")
    modifier: int = Field(description="Il modificatore aggiunto (es. 3)")
    total: int = Field(description="Il totale finale (result + modifier)")

class RulesResult(BaseModel):
    valid: bool = Field(description="True se l'azione è permessa dalle regole")
    roll: Optional[DiceRoll] = Field(default=None, description="Dettagli del tiro, nullo se non ci sono dadi")
    hit: Optional[bool] = Field(default=None, description="True se l'attacco va a segno (supera la CA), null se non c'è attacco")
    damage: Optional[int] = Field(default=0, description="Ammontare dei danni, usa 0 se l'attacco manca")
    needs_clarification: bool = Field(description="True se l'azione è ambigua (HITL livello intermedio)")
    needs_confirmation: bool = Field(description="True se l'azione è irreversibile/critica (HITL livello critico)")
    narrative_hint: str = Field(description="Suggerimento breve per il DM Agent su come descrivere l'esito")


# ==========================================
# SCHEMI PER IL WORLD STATE (MEMBRO B)
# ==========================================
class Character(BaseModel):
    """Rappresenta un singolo giocatore nel Couch Co-op"""
    name: str
    char_class: str
    hp: int
    max_hp: int
    inventory: List[str] = []

class Enemy(BaseModel):
    """Rappresenta un nemico attualmente nella scena"""
    name: str
    hp: int
    max_hp: int  # Added for progress bar
    ac: int  # Classe Armatura (Armor Class)
    status: str = "alive"

class WorldState(BaseModel):
    """Stato globale della partita salvato in JSON"""
    theme: str = Field(default="Medievale", description="Il tema narrativo attuale")
    current_location: str = Field(default="Sconosciuta", description="Dove si trova attualmente il party")
    party: List[Character] = Field(default_factory=list, description="Lista dei giocatori (Couch Co-op)")
    active_enemies: List[Enemy] = Field(default_factory=list, description="Nemici attualmente in combattimento")
    turn_number: int = Field(default=1, description="Contatore dei turni della sessione")

class StoryScene(BaseModel):
    narration: str = Field(description="La narrazione della scena")
    choices: List[str] = Field(description="Lista di opzioni esplicite")
    is_combat: bool = Field(description="True se c'è un nemico")
    inventory_found: str = Field(default="nessuno")
    
    # LA NUOVA REGOLA:
    allow_free_action: bool = Field(
        description="True se il giocatore ha tempo per esplorare liberamente. False se è una situazione di emergenza in cui deve scegliere in fretta tra le opzioni fornite."
    )
    enemy_spawn: Optional[str] = Field(
        default=None,
        description="Se la scena introduce un NUOVO nemico, scrivi 'base' o 'boss'. Altrimenti null."
    )


#schema per spawn e combattimento nemici

class EntityStats(BaseModel):
    hp: int = Field(description="Punti vita massimi del nemico")
    ca: int = Field(description="Classe Armatura per difendersi")

class EntityCombat(BaseModel):
    weapon_name: str = Field(description="Nome dell'arma impugnata")
    attack_modifier: int = Field(description="Bonus da sommare al d20 per colpire")
    damage_dice: str = Field(description="Dado di danno (es. 1d6, 2d8)")
    damage_bonus: int = Field(description="Danni fissi da sommare al risultato del dado")

class EnemyEntity(BaseModel):
    name: str = Field(description="Nome dell'entità")
    enemy_type: str = Field(description="'base' o 'boss'")
    appearance: str = Field(description="Descrizione fisica visiva")
    personality: str = Field(description="Tratto caratteriale o stile di combattimento")
    stats: EntityStats
    combat: EntityCombat