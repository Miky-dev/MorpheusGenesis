import random

# Tabelle di Generazione Casuale per il Loot
WEAPONS = {
    "fantasy": ["Pugnale Arrugginito", "Spada Corta", "Spada Lunga", "Ascia da Battaglia", "Arco Lungo", "Martello da Guerra"],
    "cyberpunk": ["Coltello Termico", "Pistola Cinetica", "Fucile a Pompa Smart", "Katana Monomolecolare", "Mitraglietta Leggera"],
    "sci-fi": ["Pistola Laser", "Fucile al Plasma", "Lama Energetica", "Fucile a Impulsi", "Cannone a Ioni"]
}

ARMORS = {
    "fantasy": ["Veste di Stoffa", "Armatura di Cuoio", "Cotta di Maglia", "Armatura a Piastre", "Scudo di Legno"],
    "cyberpunk": ["Giacca in Kevlar", "Gilet Tattico", "Esoscheletro Leggero", "Armatura Dermale", "Scudo Antisommossa"],
    "sci-fi": ["Tuta Ambientale", "Scudo Deflettore", "Armatura d'Assalto", "Tuta Potenziata", "Campo di Forza Personale"]
}

CONSUMABLES = {
    "fantasy": ["Razione Secca", "Pozione di Cura Minore", "Pozione di Cura Maggiore", "Elisir della Forza", "Antidoto"],
    "cyberpunk": ["Barretta Proteica", "Stimpack", "Medikit Avanzato", "Inalatore di Riflessi", "Kit di Riparazione"],
    "sci-fi": ["Razione di Sintesi", "Bio-Gel Curativo", "Med-Spray", "Kit di Sopravvivenza", "Cella Energetica"]
}

MISC = {
    "fantasy": ["Anello d'Argento", "Gemma Preziosa", "Chiave di Ferro", "Corda di Canapa"],
    "cyberpunk": ["Credchip", "Modulo Dati", "Grimaldello Elettronico", "Componente di Scarto"],
    "sci-fi": ["Cristallo di Memoria", "Rottame Tecnologico", "Pass di Sicurezza", "Unità di Stoccaggio"]
}

def generate_random_loot(difficulty_level: int, theme: str = "fantasy", action_context: str = "") -> dict:
    """
    Genera un oggetto di loot casuale in base alla difficoltà e al tema usando tabelle predefinite.
    Richiamabile dall'Arbitro (Orchestratore) senza usare chiamate LLM.
    """
    theme = theme.lower()
    if theme not in WEAPONS:
        theme = "fantasy"

    # Se l'azione non ha senso per trovare loot, si può gestire qui (es. guardare il cielo)
    if "cielo" in action_context.lower() or "niente" in action_context.lower():
        return None

    # Determina rarità e bonus basati sulla difficoltà (0-5)
    if difficulty_level <= 1:
        rarity = "common"
        bonus = random.randint(0, 1)
    elif difficulty_level <= 3:
        rarity = "rare"
        bonus = random.randint(1, 3)
    else:
        rarity = random.choice(["epic", "legendary"])
        bonus = random.randint(3, 5)

    # Scelta categoria oggetto
    item_category = random.choices(
        ["weapon", "armor", "consumable", "misc"],
        weights=[0.25, 0.25, 0.35, 0.15]
    )[0]
    
    item_data = {
        "rarity": rarity,
        "quantity": 1,
        "durability": 100 if item_category in ["weapon", "armor"] else None,
        "lore_snippet": f"Un oggetto di rarità {rarity} forgiato dalle meccaniche del mondo."
    }

    if item_category == "weapon":
        item_data.update({
            "name": random.choice(WEAPONS[theme]),
            "item_type": "weapon",
            "attack_bonus": bonus,
            "ac_bonus": 0,
            "heal_amount": 0,
            "value": random.randint(10, 50) * max(1, bonus)
        })
    elif item_category == "armor":
        item_data.update({
            "name": random.choice(ARMORS[theme]),
            "item_type": "armor",
            "attack_bonus": 0,
            "ac_bonus": bonus,
            "heal_amount": 0,
            "value": random.randint(15, 60) * max(1, bonus)
        })
    elif item_category == "consumable":
        item_data.update({
            "name": random.choice(CONSUMABLES[theme]),
            "item_type": "consumable",
            "attack_bonus": 0,
            "ac_bonus": 0,
            "heal_amount": random.randint(10, 50) * max(1, bonus),
            "value": random.randint(5, 20) * max(1, bonus),
            "quantity": random.randint(1, 3)
        })
    else:
        item_data.update({
            "name": random.choice(MISC[theme]),
            "item_type": "key_item",
            "attack_bonus": 0,
            "ac_bonus": 0,
            "heal_amount": 0,
            "value": random.randint(1, 100) * max(1, bonus)
        })

    return {
        "found_item": item_data,
        "rarity_roll": random.randint(1, 20),
        "lore_hint": "Statistiche generate dalle tabelle del fato.",
        "inventory_updates": []
    }