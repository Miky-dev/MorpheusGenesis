import os
import google.generativeai as genai
from dotenv import load_dotenv

print("1. Caricamento file .env...")
load_dotenv()

# CONTROLLO CHIAVE
api_key = os.getenv("GOOGLE_API_KEY") 
if not api_key:
    # Se hai usato un altro nome nel .env, prova a cercarlo
    api_key = os.getenv("OPENAI_API_KEY")

if api_key:
    print(f"2. Chiave trovata: {api_key[:5]}...{api_key[-5:]}")
    genai.configure(api_key=api_key)
else:
    print("2. ❌ ERRORE: Nessuna chiave trovata nel file .env! Controlla il nome della variabile.")
    exit()

print("3. Richiesta modelli a Google...")
try:
    models = list(genai.list_models())
    print(f"4. Trovati {len(models)} modelli totali.")
    
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            # Stampiamo il nome pulito che serve ad Agno
            clean_name = m.name.replace('models/', '')
            print(f" > Modello valido: {clean_name}")
            
except Exception as e:
    print(f"❌ Errore durante la chiamata: {e}")