import json
import os
from datetime import date, timedelta
from typing import List

SEEN_JOBS_PATH = "storage/seen_jobs.json"


def load_seen_urls(path: str = SEEN_JOBS_PATH) -> List[dict]:
    """Carga el historial de URLs vistas. Devuelve [] si no existe o está corrupto."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            result = json.load(f)
            return result if isinstance(result, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def save_seen_urls(seen: List[dict], path: str = SEEN_JOBS_PATH) -> None:
    """Escritura atómica: escribe a .tmp y renombra."""
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(seen, f, indent=2)
    os.replace(tmp_path, path)


def is_new_job(url: str, seen: List[dict]) -> bool:
    """Devuelve True si la URL no fue vista antes."""
    seen_urls = {entry["url"] for entry in seen}
    return url not in seen_urls


def mark_as_seen(url: str, seen: List[dict]) -> List[dict]:
    """Agrega una URL al historial con la fecha de hoy."""
    return seen + [{"url": url, "date_seen": date.today().isoformat()}]


def prune_old_entries(seen: List[dict], ttl_days: int = 90) -> List[dict]:
    """Elimina entradas con date_seen de más de ttl_days días."""
    cutoff = date.today() - timedelta(days=ttl_days)
    result = []
    for entry in seen:
        try:
            entry_date = date.fromisoformat(entry["date_seen"])
            if entry_date >= cutoff:
                result.append(entry)
        except (ValueError, KeyError):
            pass
    return result
