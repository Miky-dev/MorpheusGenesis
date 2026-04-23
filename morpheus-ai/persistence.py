import json
import os
import streamlit as st
from dataclasses import asdict, is_dataclass
from pydantic import BaseModel
from contracts.schemas import WorldState, Character, Enemy, StoryBible, WorldMap, StoryScene, LocationPopulation, Item

SAVE_DIR = "saves"

def ensure_save_dir():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

class GameStateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if is_dataclass(obj):
            return asdict(obj)
        return super().default(obj)

def save_game_state(session_id: str):
    ensure_save_dir()
    
    # Lista delle chiavi da persistere
    keys_to_save = [
        "page",
        "story_bible",
        "world_map",
        "world_state",
        "visited_locations",
        "current_location_id",
        "last_narrative",
        "current_scene",
        "cinematic_seen",
        "setup_p1_name",
        "setup_p1_class",
        "setup_theme",
        "setup_mood",
        "campaign_name"
    ]
    
    state_to_save = {}
    for key in keys_to_save:
        if key in st.session_state:
            state_to_save[key] = st.session_state[key]
            
    filepath = os.path.join(SAVE_DIR, f"{session_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(state_to_save, f, cls=GameStateEncoder, indent=2)

def load_game_state(session_id: str):
    filepath = os.path.join(SAVE_DIR, f"{session_id}.json")
    if not os.path.exists(filepath):
        return False
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Ripristino oggetti complessi
        if "story_bible" in data and data["story_bible"]:
            data["story_bible"] = StoryBible.model_validate(data["story_bible"])
            
        if "world_map" in data and data["world_map"]:
            data["world_map"] = WorldMap.model_validate(data["world_map"])
            
        if "current_scene" in data and data["current_scene"]:
            data["current_scene"] = StoryScene.model_validate(data["current_scene"])
            
        if "visited_locations" in data and data["visited_locations"]:
            restored_locs = {}
            for loc_id, loc_data in data["visited_locations"].items():
                restored_locs[loc_id] = LocationPopulation.model_validate(loc_data)
            data["visited_locations"] = restored_locs
            
        if "world_state" in data and data["world_state"]:
            ws_data = data["world_state"]
            # Character list
            party = []
            for char_data in ws_data.get("party", []):
                # Handle nested inventory
                inv = []
                for item_data in char_data.get("inventory", []):
                    inv.append(Item.model_validate(item_data))
                
                party.append(Character(
                    name=char_data["name"],
                    char_class=char_data["char_class"],
                    hp=char_data["hp"],
                    max_hp=char_data["max_hp"],
                    ac=char_data.get("ac", 12),
                    level=char_data.get("level", 1),
                    inventory=inv
                ))
            
            # Enemy list
            enemies = []
            for enemy_data in ws_data.get("active_enemies", []):
                enemies.append(Enemy.model_validate(enemy_data))
                
            data["world_state"] = WorldState(
                theme=ws_data["theme"],
                party=party,
                active_enemies=enemies,
                current_location=ws_data["current_location"],
                known_locations=ws_data.get("known_locations", []),
                turn_number=ws_data.get("turn_number", 1),
                active_npc_name=ws_data.get("active_npc_name"),
                combat_log=ws_data.get("combat_log", []),
                memory_summary=ws_data.get("memory_summary", "")
            )
            
        # Applica al session_state
        for key, value in data.items():
            st.session_state[key] = value
            
        return True
    except Exception as e:
        print(f"Errore caricamento salvataggio: {e}")
        return False
