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
    active_npc_name: Optional[str] = Field(default=None, description="Il nome dell'NPC con cui il giocatore sta dialogando, null se nessuno")
    known_locations: List[str] = Field(default_factory=list, description="Lista degli id_name delle location che il giocatore conosce (visitato o sentito nominar)")


class StoryScene(BaseModel):
    narration: str = Field(description="La narrazione della scena")
    choices: List[str] = Field(description="Lista di opzioni esplicite")
    is_combat: bool = Field(description="True se c'è un nemico")
    inventory_found: Optional[str] = Field(default="nessuno", description="Nome dell'oggetto trovato, 'nessuno' o null se non applicabile")
    
    # LA NUOVA REGOLA:
    allow_free_action: bool = Field(
        description="True se il giocatore ha tempo per esplorare liberamente. False se è una situazione di emergenza in cui deve scegliere in fretta tra le opzioni fornite."
    )
    enemy_spawn: Optional[str] = Field(
        default=None,
        description="Se la scena introduce un NUOVO nemico, scrivi 'base' o 'boss'. Altrimenti null."
    )
    
    # AGGIORNAMENTO MISSIONI
    quest_unlocked_id: Optional[str] = Field(default=None, description="ID della missione da attivare (sq_XX)")
    quest_completed_id: Optional[str] = Field(default=None, description="ID della missione completata (sq_XX)")



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


#SCHEMA PER LA MAPPA DI GIOCO
class Location(BaseModel):
    id_name: str = Field(description="Un ID univoco in minuscolo, es: 'taverna_neon'")
    name: str = Field(description="Il nome epico o tematico della località")
    description: str = Field(description="Breve descrizione visiva del luogo")
    x: int = Field(description="Coordinata X sulla mappa (da 0 a 100)")
    y: int = Field(description="Coordinata Y sulla mappa (da 0 a 100)")
    connected_to: List[str] = Field(description="Lista degli id_name dei luoghi raggiungibili da qui")
    difficulty_level: int = Field(ge=0, le=5, description="0=Sicuro (NPC), 1-5=Pericolo crescente")

class WorldMap(BaseModel):
    region_name: str = Field(description="Nome dell'intera regione generata")
    locations: List[Location] = Field(description="Lista di tutte le località sulla mappa")
    spawn_location_id: str = Field(description="L'id_name del luogo esatto dove il giocatore si sveglia all'inizio")

# SCHEMA STORY BIBLE
class SubQuest(BaseModel):
    id: str = Field(description="ID univoco, es: 'sq_01'")
    title: str = Field(description="Titolo breve della missione")
    description: str = Field(description="Cosa deve fare il giocatore (1 frase)")
    giver_npc: str = Field(description="Nome dell'NPC che assegna questa missione")
    location_hint: str = Field(description="Dove deve andare il giocatore")
    status: str = Field(default="locked", description="'locked', 'active', o 'completed'")

class QuestCharacterBrief(BaseModel):
    name: str = Field(description="Nome del personaggio")
    role: str = Field(description="Ruolo narrativo (es. 'Villain principale', 'Alleato chiave')")
    location_hint: str = Field(description="Dove trovarlo nella regione")

class StoryBible(BaseModel):
    title: str = Field(description="Titolo epico dell'avventura")
    main_objective: str = Field(description="L'obiettivo finale del giocatore in 1 frase chiara e motivante")
    backstory: str = Field(description="Contesto narrativo del mondo: cosa è successo, perché è importante (2-3 frasi)")
    opening_cinematic: str = Field(description="Un lungo paragrafo cinematografico (almeno 200 parole) che narra la lore completa, rivela l'obiettivo principale, spiega le regole del mondo (esplorazione, combattimento, NPC, oggetti) e cosa il giocatore può trovare nell'avventura. Deve essere epico, immersivo e in seconda persona.")
    herald_npc_name: str = Field(description="Il nome dell'NPC che rivela la quest principale al giocatore. NON si trova allo spawn.")
    herald_location_id: str = Field(description="L'id_name della location dove si trova l'araldo")
    herald_npc_reveal: str = Field(description="La frase esatta e drammatica con cui l'araldo rivela la quest")
    quest_chain: List[SubQuest] = Field(description="La catena di almeno 10 sub-missioni da completare per arrivare all'obiettivo finale")
    key_npcs: List[QuestCharacterBrief] = Field(default_factory=list, description="Lista degli NPC più importanti della storia con i loro ruoli")
    key_enemies: List[QuestCharacterBrief] = Field(default_factory=list, description="Lista dei nemici/boss più importanti con i loro ruoli")

#SCHEMA GENRAZIONE NPC
class NPC(BaseModel):
    name: str = Field(description="Il nome dell'NPC")
    role: str = Field(description="Il suo ruolo (es. 'Oste', 'Mercante', 'Sopravvissuto ferito')")
    appearance: str = Field(description="Descrizione visiva (1 frase)")
    personality: str = Field(description="Come si pone (es. 'Paranoico', 'Accogliente')")
    first_line: str = Field(description="La primissima frase esatta che dice rivolgendosi al giocatore")

class LocationPopulation(BaseModel):
    location_lore: str = Field(description="La storia, il segreto o l'atmosfera di questo luogo specifico (1-2 frasi)")
    npcs: List[NPC] = Field(description="Lista degli NPC presenti in questo luogo")
    rumors: List[str] = Field(description="2 o 3 dicerie, consigli o avvertimenti sui nemici o sui luoghi vicini")