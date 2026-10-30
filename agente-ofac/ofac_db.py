"""
SQLite layer for OFAC crypto address screening.

Schema
------
addresses   — indexed crypto addresses from the SDN list
sync_log    — history of each sync run (added/removed counts)
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "ofac.db"


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS addresses (
                id           INTEGER PRIMARY KEY,
                address      TEXT    NOT NULL,
                address_norm TEXT    NOT NULL,
                currency     TEXT    NOT NULL,
                entity_name  TEXT    NOT NULL,
                entity_id    TEXT,
                list_date    TEXT    NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_addr_norm_cur_ent
                ON addresses(address_norm, currency, entity_id);

            CREATE TABLE IF NOT EXISTS sync_log (
                id         INTEGER PRIMARY KEY,
                synced_at  TEXT NOT NULL,
                list_date  TEXT,
                total      INTEGER,
                added      INTEGER,
                removed    INTEGER,
                error      TEXT
            );
        """)


def normalize(address: str) -> str:
    """
    Normalize an address for comparison.

    EVM chains (0x prefix) and bech32 formats (bc1, ltc1, bnb1) are
    case-insensitive by protocol — lowercase them.
    All other formats (Bitcoin base58 1/3, TRX, XRP, SOL, XMR, etc.)
    are case-sensitive — strip whitespace only.
    """
    addr = address.strip()
    lower = addr.lower()
    if lower.startswith("0x") or lower.startswith("bc1") \
            or lower.startswith("ltc1") or lower.startswith("bnb1"):
        return lower
    return addr


def upsert_addresses(records: list[dict]) -> tuple[int, int]:
    """
    Insert or replace records. Returns (added, unchanged) counts.
    A record is a dict with keys: address, currency, entity_name, entity_id, list_date.
    """
    if not records:
        return 0, 0

    added = 0
    with _conn() as con:
        for r in records:
            norm = normalize(r["address"])
            cur = con.execute(
                "SELECT id FROM addresses WHERE address_norm=? AND currency=? AND entity_id=?",
                (norm, r["currency"], r["entity_id"]),
            ).fetchone()
            if cur is None:
                con.execute(
                    "INSERT INTO addresses(address, address_norm, currency, entity_name, entity_id, list_date) "
                    "VALUES (?,?,?,?,?,?)",
                    (r["address"], norm, r["currency"], r["entity_name"], r["entity_id"], r["list_date"]),
                )
                added += 1
    return added, len(records) - added


def replace_all(records: list[dict]) -> tuple[int, int]:
    """
    Atomically replace all addresses. Returns (added, removed).
    Used on each sync to reflect OFAC additions and removals.
    """
    new_keys = {
        (normalize(r["address"]), r["currency"], r["entity_id"])
        for r in records
    }

    with _conn() as con:
        existing = {
            (row["address_norm"], row["currency"], row["entity_id"])
            for row in con.execute("SELECT address_norm, currency, entity_id FROM addresses")
        }
        to_remove = existing - new_keys
        to_add = [
            r for r in records
            if (normalize(r["address"]), r["currency"], r["entity_id"])
            not in existing
        ]

        for norm, currency, entity_id in to_remove:
            con.execute(
                "DELETE FROM addresses WHERE address_norm=? AND currency=? AND entity_id=?",
                (norm, currency, entity_id),
            )

        seen_new: set[tuple] = set()
        for r in to_add:
            norm = normalize(r["address"])
            key = (norm, r["currency"], r["entity_id"])
            if key in seen_new:
                continue
            seen_new.add(key)
            con.execute(
                "INSERT INTO addresses(address, address_norm, currency, entity_name, entity_id, list_date) "
                "VALUES (?,?,?,?,?,?)",
                (r["address"], norm, r["currency"], r["entity_name"], r["entity_id"], r["list_date"]),
            )

    return len(to_add), len(to_remove)


def lookup(address: str) -> list[dict]:
    """
    Return all SDN matches for a given address (exact match after normalization).
    Returns a list of dicts with keys: entity_name, currency, entity_id, list_date.
    Empty list = no match.
    """
    norm = normalize(address)
    with _conn() as con:
        rows = con.execute(
            "SELECT entity_name, currency, entity_id, list_date "
            "FROM addresses WHERE address_norm = ?",
            (norm,),
        ).fetchall()
    return [dict(row) for row in rows]


def total_count() -> int:
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM addresses").fetchone()[0]


def currency_counts() -> dict[str, int]:
    with _conn() as con:
        rows = con.execute(
            "SELECT currency, COUNT(*) as n FROM addresses GROUP BY currency ORDER BY n DESC"
        ).fetchall()
    return {row["currency"]: row["n"] for row in rows}


def last_list_date() -> str | None:
    with _conn() as con:
        row = con.execute(
            "SELECT list_date FROM addresses ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return row["list_date"] if row else None


def log_sync(synced_at: str, list_date: str, total: int, added: int, removed: int,
             error: str = "") -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO sync_log(synced_at, list_date, total, added, removed, error) "
            "VALUES (?,?,?,?,?,?)",
            (synced_at, list_date, total, added, removed, error or None),
        )


def last_sync() -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM sync_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None
