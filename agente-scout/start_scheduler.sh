#!/bin/bash
# Wrapper para el LaunchAgent — garantiza el entorno correcto
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export HOME="/Users/your_username"

cd /Users/your_username/Mis-Agentes/agente-scout

exec /usr/bin/python3 scout_scheduler.py
