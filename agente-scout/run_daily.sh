#!/bin/bash
# Esperar a que la red esté disponible (máx 60 segundos)
for i in $(seq 1 12); do
    ping -c 1 -W 2 8.8.8.8 &>/dev/null && break
    sleep 5
done

cd /Users/your_username/Mis-Agentes/agente-scout
/Users/your_username/Mis-Agentes/agente-scout/.venv/bin/python3 -c "import sys; sys.path.insert(0, '.'); from scout_runner import run; run('daily')" >> logs/scout.log 2>&1
