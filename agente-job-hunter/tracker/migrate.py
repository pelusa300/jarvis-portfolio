#!/usr/bin/env python3
"""
Migración one-time: seen_jobs.json → tabla seen_scrapes en applications.db.
Idempotente: si la URL ya existe en seen_scrapes, la omite (INSERT OR IGNORE).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tracker.db import init_db, save_seen_url, load_seen_urls, DB_PATH

SEEN_JOBS_JSON = Path(__file__).parent.parent / "storage" / "seen_jobs.json"


def migrate(db_path=DB_PATH, dry_run=False):
    init_db(db_path)

    if not SEEN_JOBS_JSON.exists():
        print("seen_jobs.json no encontrado — nada que migrar.")
        return 0

    data = json.loads(SEEN_JOBS_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("seen_jobs.json tiene formato inesperado.")
        return 0

    before = len(load_seen_urls(db_path))
    count = 0
    for entry in data:
        url = (entry.get("url") or "").strip()
        date_seen = (entry.get("date_seen") or "").strip()
        if url and date_seen:
            if not dry_run:
                save_seen_url(url, date_seen, db_path)
            count += 1

    after = len(load_seen_urls(db_path))
    print(f"Migración {'(dry-run) ' if dry_run else ''}completa: "
          f"{count} entradas en JSON → {after - before} nuevas en seen_scrapes "
          f"(total: {after})")
    return count


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    migrate(dry_run=dry)
