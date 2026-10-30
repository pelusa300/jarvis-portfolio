import logging
from datetime import date, timedelta
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)
STALE_DAYS = 21
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobTracker/1.0)"}

_CLOSED_PHRASES = [
    "no longer available",
    "position has been filled",
    "job closed",
    "this job has expired",
    "this listing has expired",
    "no longer accepting applications",
    "position is no longer available",
    "job is no longer available",
    "this position has been filled",
]


def _body_signals_closed(text: str) -> bool:
    low = text.lower()
    return any(phrase in low for phrase in _CLOSED_PHRASES)


def check_link(url: Optional[str]) -> str:
    """
    Verifica si un link de vacante sigue activo.
    Estrategia:
      1. HEAD request.
      2. Si HEAD da 404 → "cerrada".
      3. Si HEAD da 405 o 403 → retry con GET.
      4. En GET: 404 → "cerrada"; 200 + body con frase de cierre → "cerrada"; 200 limpio → "ok".
      5. Cualquier otro código o excepción → "no verificado" (nunca marcar cerrada por ambigüedad).
    """
    if not url:
        return "no verificado"
    try:
        head = requests.head(url, timeout=8, allow_redirects=True, headers=_HEADERS)
        if head.status_code == 404:
            return "cerrada"
        if head.status_code == 200:
            return "ok"
        if head.status_code in (403, 405):
            return _check_via_get(url)
        return "no verificado"
    except Exception as exc:
        logger.debug("check_link HEAD %s → %s", url, exc)
        return "no verificado"


def _check_via_get(url: str) -> str:
    try:
        get = requests.get(url, timeout=10, allow_redirects=True, headers=_HEADERS)
        if get.status_code == 404:
            return "cerrada"
        if get.status_code == 200:
            if _body_signals_closed(get.text):
                return "cerrada"
            return "ok"
        return "no verificado"
    except Exception as exc:
        logger.debug("check_link GET %s → %s", url, exc)
        return "no verificado"


def is_stale(date_found: str, stale_days: int = STALE_DAYS) -> bool:
    if not date_found:
        return False
    try:
        found = date.fromisoformat(date_found)
        return (date.today() - found).days > stale_days
    except ValueError:
        return False


def flag_stale(jobs: List[dict], stale_days: int = STALE_DAYS) -> List[dict]:
    for job in jobs:
        job["stale"] = is_stale(
            job.get("date_found") or job.get("date_seen", ""), stale_days
        )
    return jobs
