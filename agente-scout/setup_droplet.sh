#!/bin/bash
set -e
echo "=== Setup JARVIS agente-scout ==="

# Crear directorio de logs
mkdir -p /opt/jarvis/agente-scout/logs

# Instalar dependencias en venv compartido
source /opt/jarvis/venv/bin/activate
pip install APScheduler --quiet
echo "deps OK"

# Instalar y arrancar servicio systemd
cp /opt/jarvis/agente-scout/jarvis-scout.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable jarvis-scout
systemctl start jarvis-scout

echo "✅ Setup completo"
systemctl status jarvis-scout --no-pager
