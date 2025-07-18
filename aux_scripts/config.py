# config.py
from dotenv import load_dotenv
import os

# 1️⃣ Carga variables de entorno desde .env
load_dotenv()

# 2️⃣ Obtén y valida la existencia de la clave API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Falta definir OPENAI_API_KEY en las variables de entorno")
