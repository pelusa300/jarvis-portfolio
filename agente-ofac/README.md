# agente-ofac — OFAC Crypto Address Screening

Screens a crypto wallet address against the OFAC SDN List (Specially Designated
Nationals). Zero-cost: no external APIs, pure Python standard library. Runs as a
daily LaunchAgent that keeps a local SQLite database current.

---

## ⚠️ Disclaimer

**This tool performs exact-match screening against the OFAC SDN List. A NO MATCH
result does not confirm the address is safe or unsanctioned.**

This tool does **not** detect:
- Related addresses owned by the same entity
- Cluster wallets or co-spend associations
- Transaction-graph connections to sanctioned addresses

That requires blockchain analytics (e.g., Chainalysis, Elliptic, TRM Labs).

Results produced by this tool are **not legal determinations**. Do not rely on
this tool as your sole compliance control. Consult qualified legal counsel for
sanctions compliance decisions.

---

## Usage

```bash
# First sync (downloads ~128MB XML from OFAC, populates local DB)
python3 ofac_sync.py

# Screen an address
python3 ofac_check.py <address>
```

### Sample output — MATCH

```
$ python3 ofac_check.py 0x252a8bd2319d8a555b872990601221b3a2053bce

MATCH
  Entity:    MESRI Behzad
  Currency:  ETH
  Entity ID: 24003
  List date: 2026-10-28

⚠️  Exact-match result only. Not a legal determination. Does not detect related addresses or transaction-graph connections.
```

### Sample output — NO MATCH

```
$ python3 ofac_check.py 0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef

NO MATCH  (checked 1,074 addresses — list date: 2026-10-28)

⚠️  Exact-match result only. Not a legal determination. Does not detect related addresses or transaction-graph connections.
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | NO MATCH |
| `1` | MATCH found |
| `2` | Error (DB missing, bad input) |

---

## Setup

```bash
# 1. Install (no external dependencies — stdlib only)
#    Requires Python 3.11+

# 2. Initial sync
python3 ofac_sync.py

# 3. Schedule daily sync via LaunchAgent
cp com.jarvis.ofac.plist ~/Library/LaunchAgents/com.jarvis.ofac.plist
# Edit plist: replace your_username with your macOS username
launchctl load ~/Library/LaunchAgents/com.jarvis.ofac.plist
```

---

## Design Decisions

### Address normalization by protocol, not by currency label

Different blockchain address formats have different case-sensitivity rules
at the protocol level:

- **EVM chains** (`0x...` prefix — ETH, ETC, ARB, USDC, etc.): the checksum
  encoding (EIP-55) uses mixed case to embed a checksum, but the underlying
  address is case-insensitive. Stored and compared as lowercase.
- **Bech32 formats** (`bc1...`, `ltc1...`, `bnb1...`): case-insensitive by
  spec. Stored and compared as lowercase.
- **Base58 formats** (Bitcoin `1...`/`3...`, TRX `T...`, XRP `r...`, SOL, XMR,
  ZEC, DASH, etc.): **case-sensitive by protocol**. A lowercase version of a
  Bitcoin address is a different — likely invalid — address. These are stored
  and compared with `.strip()` only, no case conversion.

This means passing a real BTC address in all-lowercase will correctly return
NO MATCH, even if the uppercase version is on the SDN list. The tool reflects
what OFAC published, not a normalized variant.

### Fail-safe sync: DB is never overwritten on a bad result

Before replacing the live database, `ofac_sync.py` runs four checks:

1. Download must succeed (network error → abort, keep old DB)
2. XML must parse without error (malformed response → abort)
3. Extracted address count must be > 0 (parser break → abort)
4. Extracted count must be ≥ 50% of the previous DB total (anomalous drop → abort)

On any failure the old database remains intact, a `status: FAIL` line is written
to `shared_reports/ofac_latest.md`, and the health-check agent raises an alert
immediately — without waiting for a stale timestamp.

### Currency type IDs read from the XML itself

OFAC assigns internal numeric IDs to each cryptocurrency feature type
(e.g., `344` = XBT, `345` = ETH). Instead of hardcoding these IDs, `ofac_sync.py`
reads the `ReferenceValueSets/FeatureTypeValues` section of the XML at parse time
and builds the mapping dynamically, looking for entries whose name starts with
`"Digital Currency Address - "`. When OFAC adds a new cryptocurrency to the list,
the sync picks it up automatically on the next run.

---

## Files

| File | Purpose |
|------|---------|
| `ofac_sync.py` | Download XML, extract addresses, update SQLite, write report |
| `ofac_db.py` | SQLite schema, normalize, lookup, replace_all, sync_log |
| `ofac_check.py` | CLI: screen one address |
| `com.jarvis.ofac.plist` | LaunchAgent — daily sync at 07:00 |
| `tests/test_ofac.py` | 23 tests (normalization, match, no-match, safety, exit codes) |
| `ofac.db` | Local SQLite DB (gitignored) |
| `ofac_data/sdn_advanced.xml` | Cached XML — one copy, overwritten each sync (gitignored) |
| `logs/` | Sync log (gitignored) |

---

## Data source

**OFAC Sanctions List Service — SDN Advanced XML**
`https://www.treasury.gov/ofac/downloads/sanctions/1.0/sdn_advanced.xml`

Published by the U.S. Department of the Treasury, Office of Foreign Assets
Control. Updated irregularly; this agent syncs daily at 07:00.
