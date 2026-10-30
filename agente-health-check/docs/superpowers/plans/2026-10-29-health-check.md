# Jarvis Health-Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Script Python diario que verifica que los 5 agentes automáticos de Jarvis corrieron bien y avisa por Telegram si algo falló.

**Architecture:** Un solo script Python síncrono (`health_check.py`) sin llamadas a la API de Anthropic. Lee logs y archivos en disco para detectar fallos. Envía un único mensaje a Telegram topic "Herramientas Jarvis" (thread_id=2) si hay errores, o "Todo OK" los domingos. Se auto-protege con try/except global y sentinel file. LaunchAgent lo dispara a las 8:30am.

**Tech Stack:** Python 3.11+ stdlib (`pathlib`, `datetime`, `subprocess`, `os`) + `requests` para Telegram. Variables de entorno desde `.env` vía `python-dotenv`.

---

## Archivos a crear/modificar

| Acción | Archivo | Responsabilidad |
|---|---|---|
| Crear | `agente-health-check/health_check.py` | Script principal — toda la lógica |
| Crear | `agente-health-check/com.adrianhealthcheck.plist` | LaunchAgent — disparo a 8:30am |
| Crear | `agente-health-check/.env` | TELEGRAM_TOKEN, TELEGRAM_GROUP_ID |
| Crear | `agente-health-check/logs/` | Salida stdout/stderr del LaunchAgent |
| Crear | `agente-health-check/sentinel/` | Archivo `.last_run` para auto-monitoreo |
| Modificar | `CLAUDE.md` (proyecto) | Quitar referencias al Droplet, añadir health-check |
| Modificar | `shared_reports/_index.md` | Añadir health-check como agente |

---

## Task 1: Estructura base y .env

**Files:**
- Crear: `agente-health-check/health_check.py` (esqueleto)
- Crear: `agente-health-check/.env`

- [ ] **Step 1: Crear directorios**

```bash
mkdir -p ~/Mis-Agentes/agente-health-check/logs
mkdir -p ~/Mis-Agentes/agente-health-check/sentinel
```

- [ ] **Step 2: Crear .env copiando credenciales**

El `.env` del health-check toma las mismas credenciales que ya existen en `agente-finanzas/.env`. Copiar los valores (no el archivo completo):

```bash
# agente-health-check/.env
TELEGRAM_TOKEN=<mismo valor que agente-finanzas/.env TELEGRAM_FINANCE_BOT_TOKEN>
TELEGRAM_GROUP_ID=YOUR_TELEGRAM_GROUP_ID
```

- [ ] **Step 3: Crear esqueleto de health_check.py**

```python
#!/usr/bin/env python3
"""
Jarvis Health-Check — corre a las 8:30am vía LaunchAgent.
Sin llamadas a Anthropic. Puro stdlib + requests.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BASE        = Path.home() / "Mis-Agentes"
SENTINEL    = Path(__file__).parent / "sentinel" / ".last_run"
TOKEN       = os.environ["TELEGRAM_TOKEN"]
GROUP_ID    = os.environ["TELEGRAM_GROUP_ID"]
THREAD_ID   = 2          # topic "Herramientas Jarvis"
TODAY       = date.today()
TODAY_STR   = TODAY.isoformat()   # "2026-10-29"
ERROR_WORDS = ("Traceback", "Error", "CRITICAL", "exit code", "Exception")


if __name__ == "__main__":
    pass  # se reemplaza en Task 2
```

- [ ] **Step 4: Commit inicial**

```bash
git add agente-health-check/
git commit -m "feat: agente-health-check — estructura base y .env"
```

---

## Task 2: Configuración de agentes (hardcoded, no _index.md)

**Files:**
- Modificar: `agente-health-check/health_check.py`

- [ ] **Step 1: Añadir la config de agentes después de las constantes**

```python
# ── Configuración de agentes automáticos ──────────────────────────────────
# frequency_days: cuántos días de antigüedad máxima tolera el report antes de alertar.
# report: None si el agente no escribe a shared_reports (e.g. CFO envía solo a Telegram).
AGENTS: list[dict] = [
    {
        "name": "scout",
        "log":    BASE / "agente-scout/logs/scout.log",
        "report": BASE / "shared_reports/scout_latest.md",
        "frequency_days": 1,
    },
    {
        "name": "cfo",
        "log":    BASE / "agente-CFO/logs/launchd_out.log",
        "report": None,   # CFO no escribe a shared_reports — se verifica solo por log
        "frequency_days": 1,
    },
    {
        "name": "flare",
        "log":    BASE / "agente-flare/logs/fetch_flare_error.log",
        "report": BASE / "agente-flare/flare_live_data.json",
        "frequency_days": 1,
    },
    {
        "name": "job-hunter",
        "log":    BASE / "agente-job-hunter/logs/job_hunter.log",
        "report": BASE / "shared_reports/job_market_latest.md",
        "frequency_days": 1,
    },
    {
        "name": "crypto",
        "log":    BASE / "agente-crypto/logs/crypto.log",
        "report": BASE / "shared_reports/crypto_latest.md",
        "frequency_days": 1,
    },
]

PLU_PROCESS_PATTERN = "agente-plu/app.py"
PLU_LOG             = BASE / "agente-plu/logs/plu.log"
```

- [ ] **Step 2: Commit**

```bash
git add agente-health-check/health_check.py
git commit -m "feat: health-check — config hardcoded de agentes"
```

---

## Task 3: Funciones de detección de fallos

**Files:**
- Modificar: `agente-health-check/health_check.py`

- [ ] **Step 1: Añadir función de revisión de log**

Revisa si el log del agente tiene entradas de HOY y si alguna contiene palabras de error.

```python
def check_log(log_path: Path) -> str | None:
    """
    Retorna descripción del error si el log de hoy contiene errores,
    None si está limpio o si el archivo no existe.
    """
    if not log_path.exists():
        return f"log no encontrado: {log_path.name}"
    try:
        lines = log_path.read_text(errors="replace").splitlines()
    except OSError as e:
        return f"no se pudo leer log: {e}"

    today_lines = [l for l in lines if TODAY_STR in l]
    if not today_lines:
        return f"sin actividad hoy en {log_path.name}"

    error_lines = [l for l in today_lines if any(w in l for w in ERROR_WORDS)]
    if error_lines:
        # Retorna la primera línea de error, truncada
        return error_lines[0][:120]
    return None
```

- [ ] **Step 2: Añadir función de revisión de report**

Revisa si el archivo de reporte fue modificado dentro del umbral de frecuencia.

```python
def check_report(report_path: Path | None, frequency_days: int) -> str | None:
    """
    Retorna descripción del error si el report está stale o no existe.
    Retorna None si está fresco.
    """
    if report_path is None:
        return None   # agente sin report — no aplica
    if not report_path.exists():
        return f"report no encontrado: {report_path.name}"
    mtime = datetime.fromtimestamp(report_path.stat().st_mtime).date()
    age_days = (TODAY - mtime).days
    if age_days > frequency_days:
        return f"report {report_path.name} tiene {age_days}d de antigüedad (límite: {frequency_days}d)"
    return None
```

- [ ] **Step 3: Añadir función de verificación de P-LU**

Solo revisa P-LU si el proceso está activo. Si no está corriendo, silencio.

```python
def check_plu() -> str | None:
    """
    Si P-LU está corriendo, verifica su log de hoy.
    Si no está corriendo, retorna None (es intencional).
    """
    result = subprocess.run(
        ["pgrep", "-f", PLU_PROCESS_PATTERN],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None   # P-LU no está corriendo — OK, es manual

    return check_log(PLU_LOG)
```

- [ ] **Step 4: Commit**

```bash
git add agente-health-check/health_check.py
git commit -m "feat: health-check — funciones check_log, check_report, check_plu"
```

---

## Task 4: Envío a Telegram

**Files:**
- Modificar: `agente-health-check/health_check.py`

- [ ] **Step 1: Añadir función send_telegram**

Síncrona, sin async. Reintenta una vez si falla.

```python
def send_telegram(text: str) -> None:
    """Envía mensaje al topic Herramientas Jarvis. Reintenta una vez."""
    url     = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id":           GROUP_ID,
        "message_thread_id": THREAD_ID,
        "text":              text,
        "parse_mode":        "HTML",
    }
    for attempt in range(2):
        try:
            r = requests.post(url, json=payload, timeout=10)
            r.raise_for_status()
            return
        except Exception as e:
            if attempt == 1:
                # Fallo silencioso — escribe al stderr (capturado por launchd)
                print(f"[health-check] Telegram falló: {e}", file=sys.stderr)
```

- [ ] **Step 2: Commit**

```bash
git add agente-health-check/health_check.py
git commit -m "feat: health-check — send_telegram síncrono"
```

---

## Task 5: Lógica principal y auto-monitoreo

**Files:**
- Modificar: `agente-health-check/health_check.py`

- [ ] **Step 1: Añadir función run_checks**

```python
def run_checks() -> list[str]:
    """
    Ejecuta todos los checks. Retorna lista de fallos (vacía = todo OK).
    """
    failures: list[str] = []

    for agent in AGENTS:
        name    = agent["name"]
        log_err = check_log(agent["log"])
        rep_err = check_report(agent["report"], agent["frequency_days"])

        if log_err:
            failures.append(f"<b>{name}</b>: {log_err}")
        if rep_err:
            failures.append(f"<b>{name}</b>: {rep_err}")

    plu_err = check_plu()
    if plu_err:
        failures.append(f"<b>p-lu</b> (activo): {plu_err}")

    return failures
```

- [ ] **Step 2: Añadir sentinel y main**

```python
def write_sentinel() -> None:
    SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    SENTINEL.write_text(datetime.now().isoformat())


def check_sentinel() -> str | None:
    """Retorna aviso si el health-check no corrió ayer."""
    if not SENTINEL.exists():
        return None
    last = datetime.fromisoformat(SENTINEL.read_text().strip()).date()
    if (TODAY - last).days > 1:
        return f"health-check no corrió desde {last} (hoy es {TODAY})"
    return None


def main() -> None:
    failures: list[str] = []

    # Auto-monitoreo: ¿corrimos ayer?
    sentinel_err = check_sentinel()
    if sentinel_err:
        failures.append(f"<b>health-check</b>: {sentinel_err}")

    failures.extend(run_checks())

    if failures:
        msg = "⚠️ <b>Jarvis Health-Check</b>\n\n" + "\n".join(f"• {f}" for f in failures)
        send_telegram(msg)
    elif TODAY.weekday() == 6:   # domingo
        send_telegram("✅ <b>Jarvis Health-Check</b> — Todo OK esta semana.")

    write_sentinel()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            send_telegram(f"🔴 <b>health-check crash</b>: {type(e).__name__}: {e}")
        except Exception:
            pass
        raise
```

- [ ] **Step 3: Commit**

```bash
git add agente-health-check/health_check.py
git commit -m "feat: health-check — lógica principal, sentinel, auto-monitoreo"
```

---

## Task 6: LaunchAgent

**Files:**
- Crear: `agente-health-check/com.adrianhealthcheck.plist`

- [ ] **Step 1: Crear el plist**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.adrianhealthcheck</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/your_username/Mis-Agentes/agente-health-check/health_check.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/your_username/Mis-Agentes/agente-health-check</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/your_username/Mis-Agentes/agente-health-check/logs/health_check.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/your_username/Mis-Agentes/agente-health-check/logs/health_check_error.log</string>

    <key>RunAtLoad</key>
    <false/>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

- [ ] **Step 2: Instalar y verificar**

```bash
cp ~/Mis-Agentes/agente-health-check/com.adrianhealthcheck.plist \
   ~/Library/LaunchAgents/com.adrianhealthcheck.plist

launchctl load ~/Library/LaunchAgents/com.adrianhealthcheck.plist
launchctl list | grep adrianhealthcheck
```

Esperado: aparece `com.adrianhealthcheck` con PID 0 (inactivo — esperando las 8:30am).

- [ ] **Step 3: Commit**

```bash
git add agente-health-check/com.adrianhealthcheck.plist
git commit -m "feat: health-check — LaunchAgent 8:30am"
```

---

## Task 7: Prueba simulando fallo

**Files:**
- Solo prueba en terminal, sin cambios de código.

- [ ] **Step 1: Simular archivo stale de scout**

```bash
# Guardar mtime original
REPORT=~/Mis-Agentes/shared_reports/scout_latest.md

# Cambiar mtime a 3 días atrás
touch -t $(date -v-3d +%Y%m%d%H%M) "$REPORT"
```

- [ ] **Step 2: Correr el script manualmente**

```bash
cd ~/Mis-Agentes/agente-health-check
python3 health_check.py
```

Esperado: mensaje en Telegram topic "Herramientas Jarvis":
```
⚠️ Jarvis Health-Check

• scout: report scout_latest.md tiene 3d de antigüedad (límite: 1d)
```

- [ ] **Step 3: Restaurar el mtime original**

```bash
touch "$REPORT"
```

- [ ] **Step 4: Verificar silencio si todo está OK**

```bash
python3 health_check.py
```

Esperado entre semana: sin mensaje Telegram. Sentinel actualizado:
```bash
cat ~/Mis-Agentes/agente-health-check/sentinel/.last_run
# 2026-10-29T08:31:xx
```

---

## Task 8: Actualizar CLAUDE.md y _index.md

**Files:**
- Modificar: `CLAUDE.md` (raíz del proyecto)
- Modificar: `shared_reports/_index.md`

- [ ] **Step 1: En CLAUDE.md — eliminar referencias al Droplet**

Buscar y eliminar/actualizar cualquier mención de `142.93.203.22`, "Droplet", o "DigitalOcean" en el context de P-LU. Reemplazar por: "P-LU corre localmente en la Mac de Adrian cuando él lo activa."

- [ ] **Step 2: En _index.md — añadir health-check**

Añadir fila en la tabla de "Reportes por dominio":

```markdown
| `health_check_sentinel` | Última ejecución del health-check | health-check | diario |
```

Y en "Estado activo":
```markdown
| sentinel/.last_run | Timestamp de la última ejecución del health-check | health-check | diario |
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md shared_reports/_index.md
git commit -m "docs: quitar referencias a Droplet, añadir health-check a _index.md"
```

---

## Self-Review

**Spec coverage:**
- ✅ LaunchAgent a las 8:30am — Task 6
- ✅ No exit code de launchctl (ajuste #1) — Task 3 usa check_log, no launchctl
- ✅ Frecuencias hardcoded (ajuste #2) — Task 2, campo `frequency_days`
- ✅ Auto-monitoreo con sentinel (ajuste #3) — Task 5 `check_sentinel()`
- ✅ P-LU solo si proceso activo — Task 3 `check_plu()` con pgrep
- ✅ Un solo mensaje Telegram — Task 4 y 5
- ✅ Silencio entre semana, "Todo OK" domingos — Task 5 `main()`
- ✅ Sin API de Anthropic — solo requests + stdlib
- ✅ Simulación de fallo — Task 7
- ✅ CLAUDE.md y _index.md — Task 8
- ✅ Skills-map: health-check es un LaunchAgent, no un skill invocable — NO aplica añadirlo al skills-map

**Placeholder scan:** ninguno encontrado. Todos los pasos tienen código completo.

**Type consistency:** `check_log`, `check_report`, `check_plu` retornan `str | None` en todos los usos. `run_checks` retorna `list[str]`. Consistente en Task 3 y Task 5.
