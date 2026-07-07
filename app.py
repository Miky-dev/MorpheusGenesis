import random
import os
import sys
import re
import json
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

# --- CREAZIONE DINAMICA DEL PERSONAGGIO DA FILE ---
def genera_personaggio():
    # 1. Legge gli archetipi dal file txt
    archetipi = carica_mattoncini('player.txt')
    
    # Se il file è vuoto o non esiste, usa un fallback
    if not archetipi or archetipi[0] == "Nessuna informazione disponibile.":
        archetipo_scelto = "[Avventuriero Sconosciuto]\nRazza e Classe: Umano Guerriero\nEquipaggiamento: Spada e scudo."
    else:
        archetipo_scelto = random.choice(archetipi)
    
    # 2. Tiro dei dadi per le statistiche fisiche e mentali (3d6)
    forza = random.randint(3, 18)
    destrezza = random.randint(3, 18)
    intelligenza = random.randint(3, 18)
    costituzione = random.randint(3, 18)
    
    # 3. Assembla la scheda finale (Testo base + Dadi)
    scheda_completa = f"""{archetipo_scelto}
Statistiche (Generate coi Dadi):
- FORZA: {forza} (colpire duro, sollevare, spingere)
- DESTREZZA: {destrezza} (agilità, furtività, schivare, armi a distanza)
- INTELLIGENZA: {intelligenza} (magia, indagare, capire meccanismi)
- COSTITUZIONE: {costituzione} (resistenza fisica, salute)
Punti Ferita: 100/100"""
    
    return scheda_completa

# --- 3. CARICAMENTO E MOTORE LOGICO ---
ambientazioni = carica_mattoncini('ambient.txt')
personaggi = carica_mattoncini('npc.txt')
creature = carica_mattoncini('enemies.txt')

giocatori = carica_mattoncini('player.txt')

print("="*60)
print(" ⚔️  MORPHEUS GENESIS LITE - AVVIO SISTEMA  ⚔️ ")
print("="*60)
print(f"Dati caricati: {len(ambientazioni)} ambientazioni, {len(personaggi)} personaggi, {len(creature)} creature.")

chat_history = []
diario = {} # <--- NUOVA VARIABILE PER IL DIARIO
carica_salvataggio = False

if os.path.exists("savegame.json"):
    scelta = input("💾 Trovato un salvataggio. Vuoi riprendere la partita? (s/n): ")
    if scelta.lower().startswith('s'):
        with open("savegame.json", "r", encoding="utf-8") as f:
            save_data = json.load(f)
            # Estraiamo separatamente la chat e il diario
            chat_history = save_data.get("history", [])
            diario = save_data.get("diario", {})
        carica_salvataggio = True
        print("\nPartita caricata con successo!\n")
        # Stampa l'ultimo messaggio per rinfrescare la memoria
        print(f"DUNGEON MASTER (Bentornato):\n{chat_history[-1]['content']}\n")

# --- 5. AVVIO NUOVA PARTITA (Se non è stato caricato un salvataggio) ---
if not carica_salvataggio:
    print(f"Dati caricati: {len(ambientazioni)} ambientazioni, {len(personaggi)} personaggi, {len(creature)} creature.")
    
    # NUOVA FASE: TIRO DEI DADI E MOSTRA SCHEDA
    input("\n🎲 Premi INVIO per tirare i dadi e generare il tuo personaggio...")
    
    giocatore_attuale = genera_personaggio() # Chiama la funzione aggiornata con nomi e inventario
    
    

    print("\n" + "="*50)
    print(" 📜 LA TUA SCHEDA PERSONAGGIO 📜")
    print("="*50)
    print(giocatore_attuale)
    print("="*50)
    
    input("\nPremi INVIO per farti trasportare nel mondo di gioco...")
    print("\n(Il Master sta preparando la nuova scena, attendi...)\n")
    
    print("\n(Il Master sta disegnando la mappa del mondo, attendi...)\n")
    
    # 1. Estraiamo PIÙ ambientazioni (es. 4) per popolare le direzioni
    # Assicurati che il file ambientazioni.txt abbia almeno 4 luoghi diversi!
    ambient_scelta = random.sample(ambientazioni, 4)
    
    # 2. Estraiamo NPC e Nemico
    npc_scelto = random.choice(personaggi)
    creatura_scelta = random.choice(creature)

    # 3. Costruiamo la Mappa a Nodi
    mappa_mondo = f"""[CENTRO]: {ambient_scelta[0]} <-- (Tu sei qui)
    [NORD]: {ambient_scelta[1]} <-- (Presenza avvistata: {npc_scelto})
    [EST]: {ambient_scelta[2]} <-- (Pericolo rilevato: {creatura_scelta})
    [OVEST]: {ambient_scelta[3]}
    [SUD]: Terre Selvagge e Inesplorate"""

    # 4. Inizializziamo il Diario con la mappa inclusa
    diario = {
        "La Tua Storia": giocatore_attuale,
        "Mappa e Posizioni": mappa_mondo,
        "Bestiario (Nemici Noti)": [creatura_scelta]
    }

    # --- NUOVO: CREAZIONE DEL DIARIO INIZIALE ---
    diario = {
        "La Tua Storia": giocatore_attuale,
        "Luoghi Esplorati": [ambient_scelta],
        "Personaggi Incontrati": [npc_scelto],
        "Bestiario (Nemici Noti)": [creatura_scelta]
    }

    sistema = f"""Agisci come un Dungeon Master esperto di giochi di ruolo testuali. 
L'atmosfera del gioco è fantasy medievale e avventurosa.

=== LA SCHEDA DEL GIOCATORE ===
{giocatore_attuale}

=== GEOGRAFIA E POSIZIONI (LA MAPPA) ===
{mappa_mondo}

=== REGOLE DI ESPLORAZIONE E SPOSTAMENTO ===
1. POSIZIONE ATTUALE: Il gioco inizia con il giocatore nella zona [CENTRO]. Descrivi questo luogo nel Prologo.
2. VIAGGIO: Se il giocatore decide di spostarsi (es. va a NORD o verso EST), cambia l'ambientazione e fai incontrare l'NPC o il Nemico associato a quella zona.
3. COERENZA SPAZIALE: Rispetta rigorosamente i luoghi della mappa. Non far apparire l'NPC o il Nemico se il giocatore non si reca nella loro rispettiva zona.

=== REGOLE SUI DADI, AZIONI E GIOCO DI RUOLO ===
4. RISOLUZIONE CON I DADI: Ogni volta che il giocatore descrive un'azione, riceverai anche un [Tiro d20]. Narra l'esito incrociando questo tiro con le Statistiche della Scheda.
    - Un tiro di 1 è un Fallimento Critico (disastroso).
    - Un tiro di 20 è un Successo Critico (spettacolare).
    - Tiri da 2 a 10 tendono a fallire, da 11 a 19 tendono ad avere successo.
5. GIOCO DI RUOLO: Usa Personalità, Difetto, Obiettivo e Segreto del giocatore per creare tentazioni o bivi morali.
6. BREVITÀ ESTREMA (FONDAMENTALE): Il Prologo è descrittivo, ma DOPO il prologo, ogni tua risposta deve essere un "botta e risposta" rapido. Usa MASSIMO 2-3 frasi brevi per turno. Vai dritto al punto.
7. IL GIOCATORE È IL PROTAGONISTA: Non descrivere MAI cosa prova, cosa pensa o le azioni non dichiarate dal giocatore. Limita la tua narrazione alle conseguenze delle sue azioni e alle reazioni del mondo/PNG.
8. FORMATTAZIONE: Metti in **grassetto** nomi e oggetti. Usa il *corsivo* per i suoni.

=== STRUTTURA DEL PROLOGO CHE DEVI SCRIVERE ORA ===
- Paragrafo 1 (Il Mondo): Introduci l'Ambientazione con una descrizione viscerale e immersiva. Fai capire al giocatore l'atmosfera del luogo in cui si trova (suoni, odori, luci).
- Paragrafo 2 (Il Protagonista e lo Scopo): Inserisci organicamente il giocatore nella scena. Menziona il suo nome, la sua razza e classe, ma soprattutto il suo Obiettivo o il suo Background. Spiega brevemente perché si trova in questo luogo proprio per inseguire quel fine.
- Paragrafo 3 (L'Innesco dell'Azione): Fai entrare in scena il Personaggio (NPC) o fai percepire l'indizio del Nemico per creare tensione e dare il via all'avventura. Termina la narrazione in modo netto, lasciando la scena in sospeso".
"""
    chat_history = [{"role": "system", "content": sistema}]
    
    try:
        # Genera il primo messaggio (Prologo)
        response = client.chat.completions.create(
            model=os.environ.get("MODEL_NAME", "gpt-4o-mini"),
            messages=chat_history,
            temperature=0.75
        )
        dm_reply = response.choices[0].message.content
        print(f"\nDUNGEON MASTER:\n{dm_reply}\n")
        chat_history.append({"role": "assistant", "content": dm_reply})
    except Exception as e:
        print(f"\nErrore di connessione: {e}")
        sys.exit()

else:
    # Se abbiamo caricato il salvataggio, ristampiamo l'ultima risposta del DM per rinfrescare la memoria
    ultimo_msg = chat_history[-1]["content"]
    print(f"\nDUNGEON MASTER (Bentornato):\n{ultimo_msg}\n")


# --- 6. IL CICLO DI GIOCO PRINCIPALE ---
while True:
    try:
        # Turno del giocatore
        player_input = input("\nAZIONE (scrivi 'esci' per salvare, 'diario' per il codex): ")
        
        # Blocca l'invio a vuoto
        if not player_input.strip():
            continue

        # Comando per aprire il DIARIO
        if player_input.lower() in ["diario", "codex", "scheda"]:
            print("\n" + "="*60)
            print(" 📖 IL TUO DIARIO DI VIAGGIO 📖")
            print("="*60)
            for categoria, contenuti in diario.items():
                print(f"\n--- {categoria.upper()} ---")
                
                if isinstance(contenuti, list):
                    for item in contenuti:
                        # Se l'elemento è a sua volta una lista, lo converte e unisce
                        if isinstance(item, list):
                            print(", ".join(str(i).strip() for i in item) + "\n")
                        else:
                            # Converte forzatamente in stringa prima del ritocco
                            print(str(item).strip() + "\n")
                else:
                    print(str(contenuti).strip())
                    
            print("="*60)
            continue

        # Salvataggio e Uscita
        if player_input.lower() in ["esci", "quit", "exit"]:
            save_data = {
                "history": chat_history,
                "diario": diario
            }
            with open("savegame.json", "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=4)
            print("\n💾 Partita e Diario salvati con successo. Alla prossima!")
            break
            
        # --- TIRO DEL DADO (d20) ---
        tiro_dado = random.randint(1, 20)
        messaggio_con_dado = f"{player_input}\n[Tiro d20 del sistema per questa azione: {tiro_dado}]"
        
        # Salvataggio dell'azione + dado nella memoria
        chat_history.append({"role": "user", "content": messaggio_con_dado})

        # L'IA pensa e risponde
        response = client.chat.completions.create(
            model=os.environ.get("MODEL_NAME", "gpt-4o-mini"),
            messages=chat_history,
            temperature=0.75
        )
        
        # Estrazione della risposta
        dm_reply = response.choices[0].message.content
        print(f"\nDUNGEON MASTER:\n{dm_reply}\n")
        
        # Salvataggio nella memoria
        chat_history.append({"role": "assistant", "content": dm_reply})

    except Exception as e:
        print(f"\nErrore di connessione: {e}")
        break