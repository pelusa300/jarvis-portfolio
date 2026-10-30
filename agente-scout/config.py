# agente-scout/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / ".config/jarvis/.env")  # API key central
load_dotenv()                                       # vars locales del agente

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")        # DM personal — fallback
TELEGRAM_GROUP_ID = int(os.getenv("TELEGRAM_GROUP_ID", "0"))  # Supergrupo Jarvis con topics

# Topics del supergrupo Jarvis (message_thread_id)
TOPICS = {
    "herramientas": 2,   # Herramientas Jarvis — reporte diario Scout + alertas
    "crypto":       3,   # Crypto / Flare — reservado, sin usar aún
    "deep_research": 4,  # Deep Research — deep brief de Scout
}

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "")

MODEL = "claude-sonnet-4-6"

# Current system agents the user
AGENTS = [
    "agente-mentor",
    "agente-job-hunter",
    "agente-finanzas",
    "agente-crypto",
    "agente-marketing",
    "agente-scout",
]
