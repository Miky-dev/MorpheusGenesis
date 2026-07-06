import random
import os
import sys
import re
from openai import OpenAI

# Forza l'I/O in UTF-8 per visualizzare correttamente i caratteri accentati su Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Carica le variabili dal file .env se presente
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

# --- 1. CONFIGURAZIONE API ---
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL")
)

# --- 2. FUNZIONE DI LETTURA FILE TXT (CORRETTA) ---
def carica_mattoncini(nome_file):
    if not os.path.exists(nome_file):
        print(f"⚠️  ATTENZIONE: File '{nome_file}' non trovato.")
        return ["Nessuna informazione disponibile."]
    
    with open(nome_file, 'r', encoding='utf-8') as f:
        testo = f.read().strip()
        # Divide il testo SOLO quando trova uno o più "a capo" seguiti da "["
        elementi = [blocco.strip() for blocco in re.split(r'\n+(?=\[)', testo) if blocco.strip()]
        return elementi if elementi else ["Nessuna informazione disponibile."]

# --- 3. CARICAMENTO E MOTORE LOGICO ---
ambientazioni = carica_mattoncini('ambient.txt')
personaggi = carica_mattoncini('npc.txt')
creature = carica_mattoncini('enemies.txt')

ambient_scelta = random.choice(ambientazioni)
npc_scelto = random.choice(personaggi)
creatura_scelta = random.choice(creature)

giocatore_attuale = carica_mattoncini('player.txt')[0]

# --- 4. IL MEGA-PROMPT DI SISTEMA (CON PACING MIGLIORATO) ---
sistema = f"""Agisci come un Dungeon Master esperto di giochi di ruolo testuali. 
L'atmosfera del gioco è fantasy medievale e avventurosa, ricca di mistero e creature magiche.

=== LA SCHEDA DEL GIOCATORE ===
{giocatore_attuale}

=== MATTONCINI DELLA SCENA ATTUALE ===
AMBIENTAZIONE: {ambient_scelta}
PERSONAGGIO: {npc_scelto}
NEMICO/PERICOLO: {creatura_scelta}

=== REGOLE DI STILE, RITMO E MECCANICHE ===
1. PACING: Non rovesciare tutte le informazioni addosso al giocatore in una sola volta. 
2. INTRODUZIONE GRADUALE: Descrivi prima i suoni, gli odori e l'ambiente. Inserisci il Personaggio in modo organico.
3. TENSIONE: Il Nemico/Pericolo NON deve attaccare immediatamente. Fai percepire la sua presenza.
4. RISOLUZIONE DELLE AZIONI: Valuta le azioni del giocatore basandoti ESCLUSIVAMENTE sulla "Scheda del Giocatore". Se il giocatore prova un'azione per cui è addestrato (es. furtività per un Ranger), avrà alte probabilità di successo. Se prova azioni in cui è debole (es. usare la forza bruta se è gracile), fallirà o subirà conseguenze.
5. GESTIONE DELL'INVENTARIO: Tieni traccia dell'Inventario Iniziale del giocatore. Se usa una freccia, ricordagli che gliene restano meno.
6. FORMATTAZIONE: Metti in **grassetto** nomi, oggetti e luoghi. Usa il *corsivo* per i suoni.

=== STRUTTURA DEL PROLOGO CHE DEVI SCRIVERE ORA ===
- Paragrafo 1: Descrizione viscerale del luogo. Adatta la prospettiva in base alla Razza/Classe del giocatore.
- Paragrafo 2: Apparizione o interazione con il Personaggio.
- Paragrafo 3: Indizio del Pericolo o della Creatura.
- Chiusura: Vai a capo e chiedi "Cosa fai?".
"""

# --- 5. INIZIALIZZAZIONE DELLA MEMORIA ---
chat_history = [
    {"role": "system", "content": sistema}
]

print("="*60)
print(" ⚔️  MORPHEUS GENESIS LITE - AVVIO SISTEMA  ⚔️ ")
print("="*60)
print(f"Dati caricati: {len(ambientazioni)} ambientazioni, {len(personaggi)} personaggi, {len(creature)} creature.")
print("(Il Master sta preparando la scena, attendi...)\n")

# --- 6. IL CICLO DI GIOCO PRINCIPALE ---
while True:
    try:
        # L'IA pensa e risponde
        response = client.chat.completions.create(
            model=os.environ.get("MODEL_NAME", "gpt-4o-mini"),
            messages=chat_history,
            temperature=0.75 # 0.75 migliora le descrizioni narrative
        )
        
        # Estrazione della risposta
        dm_reply = response.choices[0].message.content
        print(f"\nDUNGEON MASTER:\n{dm_reply}\n")
        
        # Salvataggio nella memoria
        chat_history.append({"role": "assistant", "content": dm_reply})
        
        # Turno del giocatore
        player_input = input("AZIONE (scrivi 'esci' per terminare): ")
        
        if player_input.lower() in ["esci", "quit", "exit"]:
            print("\nGrazie per aver giocato. Partita terminata.")
            break
            
        # Salvataggio dell'azione nella memoria
        chat_history.append({"role": "user", "content": player_input})

    except Exception as e:
        print(f"\nErrore di connessione: {e}")
        break