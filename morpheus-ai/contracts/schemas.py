from pydantic import BaseModel
from typing import List, Optional, Any

# TODO: Sostituire con i campi esatti che mi hai mostrato in precedenza
class RulesResult(BaseModel):
    is_valid: bool
    explanation: str

class WorldState(BaseModel):
    current_location: str
    active_characters: List[str]
    inventory: Optional[List[str]] = []
    # Aggiungi altri campi necessari per il tracking
