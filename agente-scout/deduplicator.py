"""
Deduplicator — filtra URLs ya reportadas en los últimos 14 días.
Archivo de estado: agente-scout/seen_urls.json
Formato: {"https://url": "YYYY-MM-DD", ...}
"""
import json
import logging
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

SEEN_URLS_PATH = Path(__file__).parent / "seen_urls.json"
RETENTION_DAYS = 14


def _load() -> dict:
    """Carga seen_urls.json. Si no existe o está corrupto, retorna dict vacío."""
    if not SEEN_URLS_PATH.exists():
        return {}
    try:
        data = json.loads(SEEN_URLS_PATH.read_text())
        if not isinstance(data, dict):
            logger.warning("seen_urls.json malformed (not a dict) — regenerating")
            return {}
        return data
    except Exception as e:
        logger.warning(f"seen_urls.json corrupted ({e}) — regenerating")
        return {}


def _save(seen: dict) -> None:
    try:
        SEEN_URLS_PATH.write_text(json.dumps(seen, indent=2))
    except Exception as e:
        logger.error(f"Could not save seen_urls.json: {e}")


def _parse_date(d: str) -> date:
    try:
        return date.fromisoformat(d)
    except Exception:
        return date.min  # fecha inválida → se limpia en el próximo cleanup


def _cleanup(seen: dict) -> dict:
    """Elimina entradas con más de RETENTION_DAYS días."""
    cutoff = date.today() - timedelta(days=RETENTION_DAYS)
    before = len(seen)
    cleaned = {url: d for url, d in seen.items() if _parse_date(d) >= cutoff}
    removed = before - len(cleaned)
    if removed:
        logger.info(f"deduplicator: cleaned {removed} stale entries (older than {RETENTION_DAYS}d)")
    return cleaned


def filter_seen(findings: list) -> list:
    """
    Filtra hallazgos cuya URL ya fue reportada en los últimos 14 días.
    Actualiza el registro con las URLs nuevas y guarda.
    Retorna solo los hallazgos nuevos.
    """
    seen = _load()
    seen = _cleanup(seen)

    today = date.today().isoformat()
    new_findings = []
    skipped = 0

    for f in findings:
        url = f.get("url", "")
        if not url:
            new_findings.append(f)
            continue
        if url in seen:
            skipped += 1
        else:
            new_findings.append(f)
            seen[url] = today

    if skipped:
        logger.info(f"deduplicator: {skipped} already-seen URLs filtered out")
    logger.info(
        f"deduplicator: {len(new_findings)} new findings after dedup "
        f"(registry: {len(seen)} URLs)"
    )

    _save(seen)
    return new_findings
