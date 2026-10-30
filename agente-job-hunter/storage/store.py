from datetime import date
from pathlib import Path
from typing import Optional

from tracker.db import (
    DB_PATH, init_db,
    is_url_seen, save_seen_url, prune_seen_urls,
)

_DB_PATH = DB_PATH


def is_new_job(url: str, db_path: Optional[Path] = None) -> bool:
    path = db_path or _DB_PATH
    init_db(path)
    return not is_url_seen(url, path)


def mark_as_seen(url: str, db_path: Optional[Path] = None) -> None:
    path = db_path or _DB_PATH
    init_db(path)
    save_seen_url(url, date.today().isoformat(), path)


def prune_old_entries(ttl_days: int = 90, db_path: Optional[Path] = None) -> int:
    path = db_path or _DB_PATH
    init_db(path)
    return prune_seen_urls(ttl_days=ttl_days, db_path=path)
