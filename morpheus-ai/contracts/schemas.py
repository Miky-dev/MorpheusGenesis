from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any, Dict
from dataclasses import dataclass, field
import uuid


class Item(BaseModel):
    name: str = Field(description="Nome evocativo dell'oggetto")
    item_type: str = Field(description="'weapon', 'armor', 'consumable' o 'key_item'")
    rarity: str = Field(description="'common', 'rare', 'epic', o 'legendary'")
    description: str = Field(description="Descrizione estetica e sensoriale")
    attack_bonus: Optional[int] = Field(default=None, description="Bonus all'attacco (se arma)")
    ac_bonus: Optional[int] = Field(default=None, description="Bonus alla CA (se armatura)")
    heal_amount: Optional[int] = Field(default=None, description="HP curati (se consumabile)")
    value: int = Field(default=0, description="Valore in monete o crediti")
    lore_snippet: str = Field(description="Una riga di storia o curiosità sull'oggetto")
    quantity: int = Field(default=1, description="Quantità per oggetti cumulabili (es. pozioni)")
    durability: Optional[int] = Field(default=None, description="Percentuale di integrità da 0 a 100 (solo per armi e armature)")



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

class RulesCheck(BaseModel):
    richiede_tiro: bool = Field(description="True se l'azione richiede una prova di abilità o tiro salvezza")
    caratteristica: Optional[str] = Field(default=None, description="Es. 'Destrezza', 'Forza' se richiede_tiro è True")
    cd_suggerita: Optional[int] = Field(default=None, description="La Classe Difficoltà (es. 12)")
    motivo: Optional[str] = Field(default=None, description="Breve spiegazione sul perché (es. 'Cerca di rubare un oggetto')")



# ==========================================
# SCHEMI PER IL WORLD STATE (MEMBRO B)
# ==========================================
@dataclass
class Character:
    name: str
    char_class: str
    hp: int
    max_hp: int
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    ac: int = 12  # Classe Armatura base
    level: int = 1
    # --- NUOVE STATISTICHE ---
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    # -------------------------
    inventory: list[Item] = field(default_factory=list)
    # Bonus di attacco calcolati in base alla classe
    @property
    def attack_bonus(self) -> int:
        bonuses = {"Warrior": 4, "Mage": 5, "Rogue": 6, "Cleric": 3}
        return bonuses.get(self.char_class, 2)

class Enemy(BaseModel):
    """Rappresenta un nemico attualmente nella scena"""
    name: str
    hp: int
    max_hp: int  # Added for progress bar
    ac: int  # Classe Armatura (Armor Class)
    status: str = "alive"

@dataclass
class WorldState:
    theme: str
    party: list['Character']
    active_enemies: list['Enemy']
    current_location: str
    known_locations: list[str] = field(default_factory=list)
    turn_number: int = 1
    active_npc_name: Optional[str] = None
    # Nuovo: Registro per i messaggi di combattimento
    combat_log: list[str] = field(default_factory=list)
    memory_summary: str = "" # Conterrà il 'summary_snapshot' di Mnemosine

class StoryScene(BaseModel): 
    narration: str = Field(description="La narrazione della scena")
    choices: List[str] = Field(description="Lista di opzioni esplicite")
    is_combat: bool = Field(description="True se c'è un nemico")
    allow_free_action: bool = Field(
        description="True se il giocatore ha tempo per esplorare. False se è in emergenza."
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


#SCHEMA PER LA MAPPA DI GIOCO
class Location(BaseModel):
    id_name: str = Field(description="Un ID univoco in minuscolo, es: 'taverna_neon'")
    name: str = Field(description="Il nome epico o tematico della località")
    description: str = Field(description="Breve descrizione visiva del luogo")
    x: int = Field(description="Coordinata X sulla mappa (da 0 a 100)")
    y: int = Field(description="Coordinata Y sulla mappa (da 0 a 100)")
    connected_to: List[str] = Field(description="Lista degli id_name dei luoghi raggiungibili da qui")
    difficulty_level: int = Field(ge=0, le=5, description="0=Sicuro (NPC), 1-5=Pericolo crescente")
    type: Optional[str] = Field(default=None, description="Tipo del luogo: 'hub', 'corridor', 'dungeon', ecc.")

class WorldMap(BaseModel):
    region_name: str = Field(description="Nome dell'intera regione generata")
    locations: List[Location] = Field(description="Lista di tutte le località sulla mappa")
    spawn_location_id: str = Field(description="L'id_name del luogo esatto dove il giocatore si sveglia all'inizio")

# SCHEMA STORY BIBLE
class SubQuest(BaseModel):
    model_config = {"populate_by_name": True}
    id: str = Field(alias="quest_id", description="ID univoco, es: 'sq_01'")
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
    narrative_style: str = Field(description="Il mood o tono della storia scelto dal giocatore")
    main_objective: str = Field(description="L'obiettivo finale del giocatore in 1 frase chiara e motivante")
    backstory: str = Field(description="Contesto narrativo del mondo: cosa è successo, perché è importante (2-3 frasi)")
    opening_cinematic: str = Field(description="Un lungo paragrafo cinematografico (almeno 200 parole) che narra la lore completa, rivela l'obiettivo principale, spiega le regole del mondo (esplorazione, combattimento, NPC, oggetti) e cosa il giocatore può trovare nell'avventura. Deve essere epico, immersivo e in seconda persona.")
    herald_npc_name: str = Field(description="Il nome dell'NPC che rivela la quest principale al giocatore. NON si trova allo spawn.")
    herald_location_id: str = Field(description="L'id_name della location dove si trova l'araldo")
    herald_npc_reveal: str = Field(description="La frase esatta e drammatica con cui l'araldo rivela la quest")
    quest_chain: List[SubQuest] = Field(description="La catena di almeno 10 sub-missioni da completare per arrivare all'obiettivo finale")
    key_npcs: List[QuestCharacterBrief] = Field(default_factory=list, description="Lista degli NPC più importanti della storia con i loro ruoli")
    key_enemies: List[QuestCharacterBrief] = Field(default_factory=list, description="Lista dei nemici/boss più importanti con i loro ruoli")
    @field_validator('opening_cinematic')
    @classmethod
    def check_word_count(cls, v: str) -> str:
        word_count = len(v.split())
        # Alziamo il muro a 120 parole (un paragrafo bello denso)
        if word_count < 120:
            raise ValueError(f"L'opening_cinematic deve essere epico e lungo. Ne ha generate solo {word_count}.")
        return v
        
    @field_validator('quest_chain')
    @classmethod
    def check_quest_count(cls, v):
        if len(v) < 10:
            raise ValueError(f"La catena di missioni è troppo corta ({len(v)}). Servono almeno 10 step.")
        return v

    @field_validator('key_npcs', 'key_enemies')
    @classmethod
    def check_lists_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError("Le liste dei personaggi o dei nemici non possono essere vuote.")
        return v

#SCHEMA GENRAZIONE NPC
class NPC(BaseModel):
    name: str = Field(description="Il nome dell'NPC")
    role: str = Field(description="Il suo ruolo (es. 'Oste', 'Mercante', 'Sopravvissuto ferito')")
    appearance: str = Field(description="Descrizione visiva (1 frase)")
    personality: str = Field(description="Come si pone (es. 'Paranoico', 'Accogliente')")
    first_line: str = Field(description="La primissima frase esatta che dice rivolgendosi al giocatore")

class LocationPopulation(BaseModel):
    location_lore: str = Field(default="Un luogo avvolto nel mistero.", description="La storia, il segreto o l'atmosfera di questo luogo specifico (1-2 frasi)")
    npcs: List[NPC] = Field(default_factory=list, description="Lista degli NPC presenti in questo luogo")
    rumors: List[str] = Field(default_factory=list, description="2 o 3 dicerie, consigli o avvertimenti sui nemici o sui luoghi vicini")


# ==========================================
# SCHEMI PER I NUOVI AGENTI SPECIALIZZATI
# ==========================================

# --- ATLAS (Cartografo) ---
class NavigationResult(BaseModel):
    success: bool = Field(description="True se il movimento è valido, False se bloccato")
    new_location_id: Optional[str] = Field(default=None, description="L'id_name della nuova location se success è True")
    atlas_comment: str = Field(description="Breve nota tecnica per il DM sul perché il movimento è fallito o cosa si vede")
    discovered_ids: List[str] = Field(default_factory=list, description="ID di nuovi luoghi citati nei dialoghi o appena scoperti")

# --- CHRONOS (Quest Agent) ---
# --- CHRONOS (Quest Agent) ---
class QuestUpdate(BaseModel):
    completed_id: Optional[str] = Field(default=None, description="ID della missione appena completata")
    unlocked_id: Optional[str] = Field(default=None, description="ID di una nuova missione sbloccata")
    logic_reasoning: str = Field(description="Spiegazione logica del perché lo stato è cambiato o rimasto fermo")
    objective_delta: Optional[str] = Field(default=None, description="Nota per il DM: come è cambiato l'obiettivo a breve termine")
    discovered_location_ids: List[str] = Field(default_factory=list, description="Lista degli 'id_name' dei luoghi scoperti analizzando i dialoghi e indizi attuali")

# --- HEPHAESTUS (Loot Agent) ---
class InventoryUpdate(BaseModel):
    item_name: str = Field(description="Il nome esatto dell'oggetto nell'inventario da modificare")
    quantity_change: int = Field(default=0, description="Variazione della quantità (es. -1 se consumato/perso)")
    durability_change: int = Field(default=0, description="Variazione della durabilità (es. -5 se usato in combattimento)")
    reason: str = Field(description="Breve motivo narrativo per la modifica")

class LootResponse(BaseModel):
    found_item: Optional[Item] = Field(default=None, description="L'oggetto trovato, nullo se non c'è nulla")
    rarity_roll: Optional[int] = Field(default=None, description="Valore generato (1-100) che ha determinato la rarità")
    lore_hint: Optional[str] = Field(default=None, description="Breve suggerimento per il DM su come descrivere il ritrovamento")
    inventory_updates: List[InventoryUpdate] = Field(default_factory=list, description="Aggiornamenti per consumare, usurare o perdere oggetti già in inventario")
# --- MNEMOSINE (Memory Agent) ---
class MemorySnapshot(BaseModel):
    summary_snapshot: str = Field(description="Riassunto denso e tecnico dell'intera storia finora (max 5 righe)")
    npc_dispositions: Dict[str, str] = Field(default_factory=dict, description="Mappa del tipo {Nome NPC: Atteggiamento/Status}")
    active_flags: List[str] = Field(default_factory=list, description="Eventi o stati persistenti (es. 'villaggio_in_fiamme')")

# --- TACTICAL AGENT ---
class TacticalDecision(BaseModel):
    target: str = Field(description="Il bersaglio scelto dal nemico")
    action_type: str = Field(description="'attack', 'ability', o 'flee'")
    ability_used: Optional[str] = Field(default=None, description="Nome dell'abilità speciale se usata")
    reasoning: str = Field(description="Il ragionamento tattico (es. 'Attacca il mago perché ha meno HP')")