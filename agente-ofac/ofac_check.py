#!/usr/bin/env python3
"""
OFAC crypto address screening — CLI tool.

Usage:
    python3 ofac_check.py <address>

Exit codes:
    0 — NO MATCH
    1 — MATCH found
    2 — Error (DB not found, address missing, etc.)
"""
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "ofac.db"

DISCLAIMER = (
    "⚠️  Exact-match result only. Not a legal determination. "
    "Does not detect related addresses or transaction-graph connections."
)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 ofac_check.py <address>", file=sys.stderr)
        return 2

    address = sys.argv[1].strip()
    if not address:
        print("Error: address cannot be empty", file=sys.stderr)
        return 2

    if not DB_PATH.exists():
        print(
            "Error: ofac.db not found. Run ofac_sync.py first.",
            file=sys.stderr,
        )
        return 2

    try:
        import ofac_db
        matches = ofac_db.lookup(address)
        total = ofac_db.total_count()
        list_date = ofac_db.last_list_date() or "unknown"
    except Exception as exc:
        print(f"Error reading database: {exc}", file=sys.stderr)
        return 2

    if matches:
        print("MATCH")
        for m in matches:
            print(f"  Entity:    {m['entity_name']}")
            print(f"  Currency:  {m['currency']}")
            print(f"  Entity ID: {m['entity_id']}")
            print(f"  List date: {m['list_date']}")
            if len(matches) > 1:
                print()
        print(f"\n{DISCLAIMER}")
        return 1

    print(
        f"NO MATCH  "
        f"(checked {total:,} addresses — list date: {list_date})"
    )
    print(f"\n{DISCLAIMER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
