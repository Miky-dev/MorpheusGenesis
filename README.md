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

## 📂 Struttura del Progetto

Il repository è organizzato in modo modulare per separare i vari componenti del sistema:

- **morpheus-ai/**: Root dell'applicazione Python.
    - **agents/**: Definizione e istruzioni degli agenti (Athena, Apollo).
    - **contracts/**: Schemi Pydantic per la validazione della logica di gioco.
    - **knowledge/**: Gestione della memoria persistente e embeddings (ChromaDB).
    - **app.py**: Entry point dell'applicazione Streamlit e gestione turni.
    - **setup_page.py**: Modulo per l'interfaccia di configurazione iniziale.
- **.vscode/**: Configurazioni IDE per l'attivazione automatica dell'ambiente virtuale.

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

## 👥 Roadmap & Divisione del Lavoro

---

### 🔵 Membro A — Backend AI, Agenti Agno & Prompt Engineering

| Stato | File / Componente | Descrizione |
|-------|-------------------|-------------|
| ✅ | `agents/dm_agent.py` | DM Agent Agno (Apollo) con persona narrativa |
| ✅ | `agents/rules_agent.py` | Rules Agent (Athena) con validazione Pydantic e lancio dadi |
| 🔲 | `agents/team.py` | Game Team Agno con logica HITL a 3 livelli |
| 🔲 | `prompts/` | System prompt versionati (16 file: dm + rules per 8 temi) |
| 🔲 | `themes/` | Dataclass `Theme` e 8 implementazioni complete |
| ✅ | `knowledge/chroma_store.py` | Wrapper ChromaDB + indicizzazione eventi di gioco |
| 🔲 | `tests/test_rules_agent.py` | 50 casi di test sul Rules Agent |

---

### 🟣 Membro B — Memory, UI, Valutazione & Deploy

| Stato | File / Componente | Descrizione |
|-------|-------------------|-------------|
| 🔲 | `agents/memory_agent.py` | Memory Agent (Mnemosyne) con KnowledgeBase Agno |
| ✅ | `contracts/schemas.py` | JSON state manager (WorldState, Character, Enemy, RulesResult) |
| ✅ | `setup_page.py` | Schermata selezione tema con card interattive (look Cyberpunk) |
| 🔲 | `ui/game_screen.py` | Schermata di gioco con HUD e Agentic UI completa |
| ✅ | `app.py` | Entry point Streamlit, gestione session state e loop di turno |
| 🔲 | `tests/test_memory.py` | Test precision/recall sul sistema RAG |
| 🔲 | Relazione tecnica finale | Metriche, analisi critica e limiti documentati |

---

### 🤝 Punti di Collaborazione Obbligatoria

| Stato | Settimana | Milestone |
|-------|-----------|-----------|
| ✅ | Settimana 1 | Definire lo schema JSON condiviso tra Rules Agent e DM Agent (`contracts/schemas.py`) |
| ✅ | Settimana 1 | Definire la struttura `WorldState` usata da tutti i moduli |
| 🔲 | Settimana 9 | Integration test end-to-end e preparazione demo orale |
