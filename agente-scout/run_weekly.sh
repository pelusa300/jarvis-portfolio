#!/bin/bash
cd /Users/your_username/Mis-Agentes/agente-scout
/Users/your_username/Mis-Agentes/agente-scout/.venv/bin/python3 -c "import sys; sys.path.insert(0, '.'); from scout_runner import run; run('weekly')" >> logs/scout.log 2>&1
