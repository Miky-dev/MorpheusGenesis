# Morpheus Genesis
**Sistema Multi-Agent per Sessioni GDR Generative**

Questo progetto è un'applicazione intelligente che genera e gestisce sessioni di gioco di ruolo (GDR) in modo autonomo, utilizzando un'architettura multi-agente basata sul framework **Agno**.

## 📖 Panoramica
AI Dungeon Master permette a un giocatore (o a un gruppo in modalità *Couch Co-op*) di immergersi in avventure testuali dinamiche attraverso 8 temi narrativi intercambiabili[cite: 155, 157]. Il sistema non è un semplice chatbot, ma un vero e proprio motore di gioco che valida le azioni, tira dadi e mantiene una memoria persistente del mondo[cite: 156].

### Perché Agno?
Il progetto utilizza **Agno** (framework consigliato dal corso) per l'orchestrazione degli agenti[cite: 160]. Rispetto ad altri framework, Agno permette una gestione più pulita tramite l'oggetto `Team` in modalità `coordinate`, riducendo il boilerplate e migliorando la leggibilità del codice[cite: 161, 162].

## 🛠️ Architettura Tecnica
Il sistema si basa su un **Game Team** che coordina tre agenti specializzati[cite: 156, 198]:

* **DM Agent (Apollo):** Gestisce la narrativa e la persona specifica per ogni tema. Produce testo narrativo e scelte strutturate in JSON[cite: 172, 214].
* **Rules Agent (Athena):** Valida la legalità delle azioni del giocatore, simula i dadi e calcola i danni. L'output è strettamente validato tramite **Pydantic v2**[cite: 173, 214].
* **Memory Agent (Mnemosyne):** Gestisce il KnowledgeBase su **ChromaDB**. Recupera il contesto rilevante per mantenere la coerenza narrativa nel tempo[cite: 174, 214, 220].

### Human-in-the-Loop (HITL)
Il sistema implementa tre livelli di controllo umano[cite: 223]:
1.  **Base:** Ogni turno richiede l'input del giocatore[cite: 224].
2.  **Intermedio:** Richiesta di disambiguazione per azioni non chiare[cite: 225].
3.  **Critico:** Conferma obbligatoria per azioni irreversibili o fatali[cite: 227].

## 🚀 Installazione e Avvio
```bash
# Clona il repository
git clone https://github.com/mikyv9/MorpheusGenesis.git
cd morpheus-ai

# Crea e attiva l'ambiente virtuale
python -m venv venv
source venv/bin/activate  # Su Windows: venv\\Scripts\\activate

# Installa le dipendenze
pip install -r requirements.txt

# Configura le API Key
cp .env.example .env
# Modifica il file .env aggiungendo la tua OPENAI_API_KEY

# Avvia l'applicazione
streamlit run app.py