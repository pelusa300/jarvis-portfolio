import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path.home() / ".config" / "jarvis" / "applications.db"

VALID_STATUSES = {
    "por aplicar", "aplicada", "entrevista",
    "rechazada", "oferta", "sin respuesta", "cerrada",
}
VALID_LINK_STATUSES = {"ok", "no verificado", "cerrada"}

_DDL = """
CREATE TABLE IF NOT EXISTS seen_scrapes (
    url       TEXT PRIMARY KEY,
    date_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    company          TEXT NOT NULL,
    title            TEXT NOT NULL,
    url              TEXT UNIQUE,
    source           TEXT,
    date_found       TEXT,
    date_applied     TEXT,
    status           TEXT NOT NULL DEFAULT 'por aplicar',
    next_step        TEXT,
    follow_up_date   TEXT,
    notes            TEXT,
    no_reapply_until TEXT,
    link_status      TEXT NOT NULL DEFAULT 'no verificado',
    link_checked_at  TEXT
);
"""


def _resolve(db_path: Optional[Path]) -> Path:
    return db_path if db_path is not None else DB_PATH


def get_conn(db_path: Optional[Path] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    path = _resolve(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with get_conn(path) as conn:
        conn.executescript(_DDL)


# ── seen_scrapes ──────────────────────────────────────────────────────────

def load_seen_urls(db_path: Optional[Path] = None) -> List[Dict[str, str]]:
    with get_conn(_resolve(db_path)) as conn:
        rows = conn.execute("SELECT url, date_seen FROM seen_scrapes").fetchall()
    return [dict(r) for r in rows]


def save_seen_url(url: str, date_seen: str, db_path: Optional[Path] = None) -> None:
    with get_conn(_resolve(db_path)) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_scrapes (url, date_seen) VALUES (?, ?)",
            (url, date_seen),
        )


def is_url_seen(url: str, db_path: Optional[Path] = None) -> bool:
    with get_conn(_resolve(db_path)) as conn:
        return conn.execute(
            "SELECT 1 FROM seen_scrapes WHERE url = ?", (url,)
        ).fetchone() is not None


def prune_seen_urls(ttl_days: int = 90, db_path: Optional[Path] = None) -> int:
    cutoff = (date.today() - timedelta(days=ttl_days)).isoformat()
    with get_conn(_resolve(db_path)) as conn:
        cur = conn.execute("DELETE FROM seen_scrapes WHERE date_seen < ?", (cutoff,))
        return cur.rowcount


# ── applications ──────────────────────────────────────────────────────────

def add_application(
    company: str,
    title: str,
    url: Optional[str] = None,
    source: Optional[str] = None,
    date_found: Optional[str] = None,
    date_applied: Optional[str] = None,
    status: str = "por aplicar",
    notes: Optional[str] = None,
    no_reapply_until: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    if status not in VALID_STATUSES:
        raise ValueError(f"Status inválido: '{status}'. Válidos: {VALID_STATUSES}")
    with get_conn(_resolve(db_path)) as conn:
        cur = conn.execute(
            """INSERT INTO applications
               (company, title, url, source, date_found, date_applied,
                status, notes, no_reapply_until)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (company, title, url, source,
             date_found or date.today().isoformat(),
             date_applied, status, notes, no_reapply_until),
        )
        return cur.lastrowid


def update_application(id: int, db_path: Optional[Path] = None, **kwargs: Any) -> None:
    allowed = {
        "status", "date_applied", "next_step", "follow_up_date",
        "notes", "no_reapply_until", "link_status", "link_checked_at",
    }
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise ValueError(f"Status inválido: '{updates['status']}'")
    if "link_status" in updates and updates["link_status"] not in VALID_LINK_STATUSES:
        raise ValueError(f"link_status inválido: '{updates['link_status']}'")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [id]
    with get_conn(_resolve(db_path)) as conn:
        conn.execute(f"UPDATE applications SET {set_clause} WHERE id = ?", values)


def list_applications(
    status: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    with get_conn(_resolve(db_path)) as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY id", (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM applications ORDER BY id"
            ).fetchall()
    return [dict(r) for r in rows]


def get_application(id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with get_conn(_resolve(db_path)) as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (id,)
        ).fetchone()
    return dict(row) if row else None


def is_url_tracked(url: str, db_path: Optional[Path] = None) -> bool:
    with get_conn(_resolve(db_path)) as conn:
        return conn.execute(
            "SELECT 1 FROM applications WHERE url = ?", (url,)
        ).fetchone() is not None


def get_blocked_companies(db_path: Optional[Path] = None) -> List[str]:
    today = date.today().isoformat()
    with get_conn(_resolve(db_path)) as conn:
        rows = conn.execute(
            "SELECT LOWER(company) FROM applications WHERE no_reapply_until > ?",
            (today,),
        ).fetchall()
    return [r[0] for r in rows]


def get_stale_applications(days: int = 7, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_conn(_resolve(db_path)) as conn:
        rows = conn.execute(
            """SELECT * FROM applications
               WHERE status = 'aplicada' AND date_applied <= ?
               ORDER BY date_applied""",
            (cutoff,),
        ).fetchall()
    return [dict(r) for r in rows]
