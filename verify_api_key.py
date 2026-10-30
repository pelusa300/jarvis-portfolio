#!/usr/bin/env python3
"""
Verifica que cada agente carga ANTHROPIC_API_KEY desde ~/.config/jarvis/.env.
No imprime la clave. Solo sí/no por agente.
Correr después de un reinicio para confirmar que el .env central persiste.
"""
from pathlib import Path
import importlib.util, os, sys

CENTRAL_ENV = Path.home() / ".config/jarvis/.env"

def load_env(path: Path) -> dict:
    """Parsea un .env sin python-dotenv para no contaminar os.environ."""
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result

def check(agent: str, env_path: Path) -> None:
    # Simula lo que hace el agente: central primero, local después
    central = load_env(CENTRAL_ENV)
    local   = load_env(env_path)
    merged  = {**central, **local}   # central gana en conflicto
    key     = merged.get("ANTHROPIC_API_KEY", "")
    loaded  = "✅ sí" if key else "❌ no"
    source  = "central" if key and "ANTHROPIC_API_KEY" in central else ("local" if key else "—")
    print(f"  {loaded}  {agent:<18} (fuente: {source})")

print(f"\nArchivo central: {CENTRAL_ENV}")
print(f"Existe:          {'✅ sí' if CENTRAL_ENV.exists() else '❌ no'}\n")

BASE = Path.home() / "Mis-Agentes"
AGENTS = [
    ("scout",       BASE / "agente-scout/.env"),
    ("cfo",         BASE / "agente-finanzas/.env"),
    ("job-hunter",  BASE / "agente-job-hunter/.env"),
    ("plu",         BASE / "agente-plu/../.env"),
    ("finanzas",    BASE / "agente-finanzas/.env"),
]

print("¿Cada agente cargaría ANTHROPIC_API_KEY?")
for name, local_env in AGENTS:
    check(name, local_env)
print()
