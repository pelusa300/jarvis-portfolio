#!/usr/bin/env python3
"""
Jarvis Health-Check — corre a las 8:30am vía LaunchAgent.
Sin llamadas a Anthropic. Puro stdlib + requests.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime
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

# ── Configuración de agentes automáticos ─────────────────────────────────
# frequency_days: antigüedad máxima tolerable del report antes de alertar.
# report=None si el agente no escribe a shared_reports.
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
        "report": None,   # CFO envía a Telegram, no escribe a shared_reports
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
    {
        "name": "ofac",
        "log":    BASE / "agente-ofac/logs/sync.log",
        "report": BASE / "shared_reports/ofac_latest.md",
        "frequency_days": 1,
    },
    {
        "name": "job-applications",
        "log":    BASE / "agente-job-hunter/logs/weekly_report.log",
        "report": BASE / "shared_reports/applications_latest.md",
        "frequency_days": 7,
    },
]

PLU_PROCESS_PATTERN = "agente-plu/app.py"
PLU_LOG             = BASE / "agente-plu/logs/plu.log"


# ── Detección de fallos ───────────────────────────────────────────────────

def _trim(log_line: str, max_chars: int = 120) -> str:
    """
    Limpia una línea de log para Telegram:
    1. Quita el prefijo timestamp + nivel (ej. "2026-10-29 07:39:07,055 [ERROR] ")
    2. Extrae el mensaje de 'message': '...' si hay JSON de Anthropic
    3. Corta en la última palabra completa antes de max_chars
    """
    import re
    # Quitar prefijo de timestamp y nivel: "2026-10-29 07:39:07,055 [ERROR] "
    clean = re.sub(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ \[\w+\] ", "", log_line)
    # Extraer 'message': '...' de JSON de Anthropic si existe
    m = re.search(r"'message':\s*'([^']+)'", clean)
    if m:
        clean = m.group(1)
    # Cortar en la última palabra completa antes de max_chars
    if len(clean) > max_chars:
        cut = clean[:max_chars].rsplit(" ", 1)[0]
        clean = cut + "…"
    return clean


def check_log(log_path: Path) -> str | None:
    """
    Retorna descripción del error si el log de hoy contiene errores,
    None si está limpio o si no hubo actividad hoy.
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
        return _trim(error_lines[0])
    return None


def check_report(report_path: Path | None, frequency_days: int) -> str | None:
    """
    Retorna descripción del error si el report está stale, no existe,
    o su metadata contiene 'status: FAIL'.
    Retorna None si está fresco y sin fallos declarados.
    """
    if report_path is None:
        return None
    if not report_path.exists():
        return f"report no encontrado: {report_path.name}"
    mtime = datetime.fromtimestamp(report_path.stat().st_mtime).date()
    age_days = (TODAY - mtime).days
    if age_days > frequency_days:
        return f"report {report_path.name} tiene {age_days}d de antigüedad (límite: {frequency_days}d)"
    # Check for explicit FAIL status in metadata line (first 3 lines)
    try:
        header = report_path.read_text(errors="replace").splitlines()[:3]
        for line in header:
            if "status: FAIL" in line:
                # Extract reason after "status: FAIL — "
                import re
                m = re.search(r"status: FAIL\s*(?:—\s*)?(.+?)_", line)
                reason = m.group(1).strip() if m else "falla declarada en reporte"
                return f"{report_path.name}: {_trim(reason)}"
    except OSError:
        pass
    return None


def check_plu() -> str | None:
    """
    Si P-LU está corriendo, verifica su log de hoy.
    Si no está corriendo, retorna None (es intencional — the user lo abre manualmente).
    """
    result = subprocess.run(
        ["pgrep", "-f", PLU_PROCESS_PATTERN],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None   # P-LU no está corriendo — OK
    return check_log(PLU_LOG)


def run_checks() -> list[str]:
    """Ejecuta todos los checks. Retorna lista de fallos (vacía = todo OK)."""
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


# ── Telegram ──────────────────────────────────────────────────────────────

def send_telegram(text: str) -> None:
    """Envía mensaje al topic Herramientas Jarvis. Reintenta una vez si falla."""
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
                print(f"[health-check] Telegram falló: {e}", file=sys.stderr)


# ── Sentinel (auto-monitoreo) ─────────────────────────────────────────────

def write_sentinel() -> None:
    SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    SENTINEL.write_text(datetime.now().isoformat())


def check_sentinel() -> str | None:
    """Avisa si el health-check no corrió ayer o antes."""
    if not SENTINEL.exists():
        return None
    last = datetime.fromisoformat(SENTINEL.read_text().strip()).date()
    if (TODAY - last).days > 1:
        return f"health-check no corrió desde {last} (hoy es {TODAY})"
    return None


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    failures: list[str] = []

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
