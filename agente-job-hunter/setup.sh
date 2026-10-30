#!/bin/bash
set -e

echo "=== Job Hunter Setup ==="

# 1. Enforce .gitignore
if ! grep -q "^\.env$" .gitignore 2>/dev/null; then
    echo ".env" >> .gitignore
    echo "✅ Added .env to .gitignore"
fi

# 2. Verificar Python 3.9+
python3 --version | grep -E "3\.(9|1[0-9])" > /dev/null || {
    echo "❌ Python 3.9+ requerido"
    exit 1
}
echo "✅ Python OK"

# 3. Instalar dependencias
pip install -r requirements.txt
echo "✅ Dependencies installed"

# 4. Instalar Playwright browsers
python3 -m playwright install chromium
echo "✅ Playwright Chromium installed"

# 5. Crear seen_jobs.json si no existe
mkdir -p storage logs
if [ ! -f storage/seen_jobs.json ]; then
    echo '[]' > storage/seen_jobs.json
    echo "✅ storage/seen_jobs.json created"
fi

# 6. Generar plist con rutas absolutas
WORKING_DIR="$(pwd)"
PYTHON_PATH="$(python3 -c 'import sys; print(sys.executable)')"
PLIST_DEST="$HOME/Library/LaunchAgents/com.adrianjobhunter.plist"

sed "s|WORKING_DIR_PLACEHOLDER|$WORKING_DIR|g; s|PYTHON_PATH_PLACEHOLDER|$PYTHON_PATH|g" \
    com.adrianjobhunter.plist > "$PLIST_DEST"
echo "✅ plist installed to $PLIST_DEST"

# 7. Cargar en launchd
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"
echo "✅ launchd job registered"

echo ""
echo "🚀 Job Hunter instalado."
echo "   Próxima ejecución automática: lunes a las 8:00 AM"
echo "   Para ejecutar ahora: python3 main.py"
echo "   Logs: logs/job_hunter.log"
