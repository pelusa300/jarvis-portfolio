import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / ".config/jarvis/.env")  # API key central
load_dotenv()                                       # vars locales del agente

# Credenciales desde .env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Skills hardcodeadas (editar aquí, no en .env)
SKILLS_HAVE = [
    "CAMS", "KYC", "AML", "BSA", "FinCEN", "OFAC",
    "SAR", "CTR", "FATF", "Travel Rule",
    "CDD", "EDD", "sanctions screening", "risk assessment",
    "blockchain", "DeFi",
]

SKILLS_LEARNING = [
    "Chainalysis", "Elliptic", "TRM Labs", "blockchain analytics",
    "MLRO", "CFCS", "CKYC", "SQL", "Python",
    "crypto exchange experience", "ACAMS membership", "FinCEN SAR filing",
]

ALL_SKILLS = SKILLS_HAVE + SKILLS_LEARNING

# Empresas conocidas del ecosistema crypto
KNOWN_CRYPTO_COMPANIES = [
    "Coinbase", "Kraken", "Binance", "Circle", "Gemini",
    "Chainalysis", "Elliptic", "TRM Labs", "Fireblocks",
    "Anchorage", "BitGo", "Paxos", "Ripple", "Consensys",
    "OpenSea", "Uniswap", "Aave", "Compound", "Celsius",
]

# Prioridad de fuentes para tiebreaking (menor índice = mayor prioridad)
SOURCE_PRIORITY = ["remote_ok", "crypto_jobs_list", "web3_career", "linkedin"]
