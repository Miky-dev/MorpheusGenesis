import os
import json

# Forza il modello richiesto PRIMA di importare i moduli che lo leggono dall'ambiente
os.environ["MODEL_NAME"] = "openai/gpt-oss-120b"

import story_agents

# Importiamo i dati di RAG e le costanti dal modulo principale
from app import ambientazioni, personaggi, creature, oggetti, genera_personaggio, TEMI, DIFFICOLTA

def main():
    print("="*60)
    print("🎬 AVVIO SCRIPT DI ESEMPIO GENERAZIONE STORIA (MULTI-AGENTE)")
    print("="*60)

    # Parametri simulati per l'esempio
    tema = 'dark-fantasy'
    difficolta = 'normal'
    map_size = 'small'
    
    desc_tema = TEMI.get(tema, TEMI["dark-fantasy"])
    desc_diff = DIFFICOLTA.get(difficolta, DIFFICOLTA["normal"])
    
    import random

    print("1. Generazione del Personaggio base e Campionamento RAG...")
    giocatore_attuale = genera_personaggio()
    
    # Campioniamo casualmente solo un sottoinsieme dei mattoncini narrativi per non sforare i token
    # (es. diamo all'IA 5 opzioni per 4 slot necessari per una mappa small)
    amb_sample = random.sample(ambientazioni, min(5, len(ambientazioni)))
    npc_sample = random.sample(personaggi, min(5, len(personaggi)))
    creature_sample = random.sample(creature, min(3, len(creature)))
    oggetti_sample = random.sample(oggetti, min(4, len(oggetti)))
    
    print(f"   [!] Selezionati per il prompt: {len(amb_sample)} luoghi, {len(npc_sample)} npc, {len(creature_sample)} nemici per limitare i token.")
    print("Personaggio generato con successo.")
    
    print("2. Esecuzione della pipeline Multi-Agente (Cartografo -> Casting -> LoreMaster)")
    print("   ATTENDERE... l'IA sta creando il mondo (può richiedere qualche decina di secondi).")
    
    # Esegue la funzione esatta che viene chiamata dietro le quinte
    risultato_agenti = story_agents.orchestra_creazione_mondo(
        map_size=map_size,
        tema=tema,
        tema_desc=desc_tema,
        difficolta=difficolta,
        difficolta_desc=desc_diff,
        scheda_giocatore=giocatore_attuale,
        ambientazioni_rag=amb_sample,
        personaggi_rag=npc_sample,
        creature_rag=creature_sample,
        oggetti_rag=oggetti_sample
    )
    
    output_file = "esempio_output_story_agent.json"
    print(f"\n3. Salvataggio del dizionario restituito nel file: {output_file}")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(risultato_agenti, f, ensure_ascii=False, indent=4)
        
    print("\n✅ Generazione completata con successo!")
    print(f"Puoi aprire e mostrare il file '{output_file}' al professore per fargli vedere")
    print("l'effettivo dizionario (JSON) restituito dalla pipeline Multi-Agente.")

if __name__ == "__main__":
    main()
