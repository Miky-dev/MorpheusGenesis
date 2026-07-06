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

# --- CREAZIONE DINAMICA DEL PERSONAGGIO ---
def genera_personaggio():
    # Liste di nomi e razze
    nomi = ["Kaelen", "Eryndor", "Tharok", "Lyra", "Grimm", "Sylas", "Vael", "Borek", "Elara", "Doran"]
    razze = ["Umano", "Elfo", "Nano", "Mezzelfo", "Senza-volto"]
    
    # Dizionario per equipaggiamento iniziale
    classi = {
        "Guerriero": "Spadone a due mani, armatura a piastre, una pozione curativa.",
        "Ladro": "Due pugnali, grimaldelli, mantello scuro, fiala di veleno.",
        "Mago": "Bastone di quercia, grimorio degli incantesimi, amuleto arcano.",
        "Ranger": "Arco lungo, 20 frecce, spada corta, razioni da viaggio.",
        "Chierico": "Mazza ferrata, scudo sacro, simbolo divino, ampolla d'acqua santa.",
        "Barbaro": "Ascia bipenne, abiti di pelle, fiasca di forte liquore nanico."
    }
    
    # NUOVO: Lista di Background / Storie personali
    backgrounds = [
        "Veterano Disilluso: Hai combattuto in guerre brutali. Hai visto compagni cadere e ora cerchi un nuovo scopo, o forse solo l'oro per dimenticare.",
        "Nobile Esiliato: La tua famiglia è stata tradita e privata delle sue terre. Viaggi in incognito per accumulare potere e riprenderti ciò che è tuo.",
        "Ricercatore di Verità: Hai letto un frammento di un'antica profezia proibita e hai lasciato la tua casa per svelarne il mistero.",
        "Sopravvissuto: Il tuo villaggio è stato distrutto da creature mostruose. Sei l'unico rimasto e porti le cicatrici (fisiche e mentali) di quella notte.",
        "Fuggiasco: Hai rubato qualcosa di inestimabile a una persona molto potente e ora sei costantemente in movimento per non farti prendere.",
        "Prescelto Riluttante: Un segno di nascita o un evento mistico ti ha marchiato. Molti si aspettano grandi cose da te, ma tu vorresti solo una vita normale e tranquilla."
    ]
    
    # Estrazione casuale
    nome_scelto = random.choice(nomi)
    razza_scelta = random.choice(razze)
    classe_scelta = random.choice(list(classi.keys()))
    equipaggiamento = classi[classe_scelta]
    storia_scelta = random.choice(backgrounds)
    
    # Tiro dei dadi per le statistiche (3 dadi a 6 facce, da 3 a 18)
    forza = random.randint(3, 18)
    destrezza = random.randint(3, 18)
    intelligenza = random.randint(3, 18)
    costituzione = random.randint(3, 18)
    
    # Creazione della scheda aggiornata
    scheda = f"""Nome: {nome_scelto}
Razza e Classe: {razza_scelta} {classe_scelta}
Background: {storia_scelta}
Equipaggiamento: {equipaggiamento}
Statistiche:
- FORZA: {forza} (colpire duro, sollevare, spingere)
- DESTREZZA: {destrezza} (agilità, furtività, schivare, armi a distanza)
- INTELLIGENZA: {intelligenza} (magia, indagare, capire meccanismi)
- COSTITUZIONE: {costituzione} (resistenza fisica, salute)
Punti Ferita: 100/100"""
    
    return scheda

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
carica_salvataggio = False

if os.path.exists("savegame.json"):
    scelta = input("💾 Trovato un salvataggio. Vuoi riprendere la partita? (s/n): ")
    if scelta.lower().startswith('s'):
        with open("savegame.json", "r", encoding="utf-8") as f:
            chat_history = json.load(f)
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
    
    # Estrazioni per l'avventura
    ambient_scelta = random.choice(ambientazioni)
    npc_scelto = random.choice(personaggi)
    creatura_scelta = random.choice(creature)

    sistema = f"""Agisci come un Dungeon Master esperto di giochi di ruolo testuali. 
L'atmosfera del gioco è fantasy medievale e avventurosa.

=== LA SCHEDA DEL GIOCATORE ===
{giocatore_attuale}

=== MATTONCINI DELLA SCENA ATTUALE ===
AMBIENTAZIONE: {ambient_scelta}
PERSONAGGIO: {npc_scelto}
NEMICO/PERICOLO: {creatura_scelta}

=== REGOLE SUI DADI E SULLE AZIONI (FONDAMENTALE) ===
4. RISOLUZIONE CON I DADI: Ogni volta che il giocatore descrive un'azione, riceverai anche un [Tiro d20]. Devi narrare l'esito incrociando questo tiro con la "Scheda del Giocatore".
- Un tiro di 1 è un Fallimento Critico (disastroso).
- Un tiro di 20 è un Successo Critico (spettacolare).
- Tiri da 2 a 10 tendono a fallire, da 11 a 19 tendono ad avere successo.
- Applica dei bonus logici basandoti sulle statistiche del giocatore.
5. INVENTARIO E PACING: Tieni traccia delle risorse. Non rovesciare troppe informazioni insieme. Fai percepire la minaccia senza farla attaccare subito.

=== STRUTTURA DEL PROLOGO CHE DEVI SCRIVERE ORA ===
- Paragrafo 1: Descrizione viscerale del luogo.
- Paragrafo 2: Apparizione o interazione con il Personaggio.
- Paragrafo 3: Indizio del Pericolo.
- Chiusura: Vai a capo e chiedi "Cosa fai?".
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
        player_input = input("\nAZIONE (scrivi 'esci' per SALVARE e terminare): ")
        
        if player_input.lower() in ["esci", "quit", "exit"]:
            with open("savegame.json", "w", encoding="utf-8") as f:
                json.dump(chat_history, f, ensure_ascii=False, indent=4)
            print("\n💾 Partita salvata con successo in 'savegame.json'. Alla prossima!")
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