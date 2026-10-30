#!/bin/bash
set -e
echo "=== Setup JARVIS agente-job-hunter ==="

# Crear directorio de logs
mkdir -p /opt/jarvis/agente-job-hunter/logs
mkdir -p /opt/jarvis/agente-job-hunter/storage

# Instalar dependencias Python (reutiliza el venv de agente-finanzas)
source /opt/jarvis/venv/bin/activate
pip install requests beautifulsoup4 anthropic python-dotenv python-telegram-bot --quiet

# Instalar y arrancar timer systemd
cp /opt/jarvis/agente-job-hunter/jarvis-job-hunter.service /etc/systemd/system/
cp /opt/jarvis/agente-job-hunter/jarvis-job-hunter.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable jarvis-job-hunter.timer
systemctl start jarvis-job-hunter.timer

echo "✅ Setup completo"
systemctl status jarvis-job-hunter.timer --no-pager
