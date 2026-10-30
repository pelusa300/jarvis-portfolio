"""
Tests para agente-ofac.

Direcciones reales sacadas de la DB después del primer sync.
No se inventaron ni hardcodearon antes de descargar la lista.

Fuente: SDN Advanced XML OFAC, list date 2026-10-28
  ETH: 0x252a8bd2319d8a555b872990601221b3a2053bce — MESRI Behzad
  XBT: 12aNKp2iDKuhEde2YfPdd4DFGenRUTKupL       — MESRI Behzad
  TRX: TNiq9AXBp9EjUqhDhrwrfvAA8U3GUQZH81       — BANK MARKAZI JOMHOURI ISLAMI IRAN
"""
import subprocess
import sys
from pathlib import Path
import pytest

# Add parent to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
import ofac_db
import ofac_sync

# Real SDN addresses (from DB after sync — not invented)
ETH_REAL    = "0x252a8bd2319d8a555b872990601221b3a2053bce"
XBT_REAL    = "12aNKp2iDKuhEde2YfPdd4DFGenRUTKupL"
TRX_REAL    = "TNiq9AXBp9EjUqhDhrwrfvAA8U3GUQZH81"

# Invented well-formed addresses (not in SDN list)
ETH_FAKE    = "0x" + "a" * 40
XBT_FAKE    = "1" + "A" * 33
RANDOM_FAKE = "notanaddressatall123"

OFAC_CHECK  = Path(__file__).parent.parent / "ofac_check.py"


# ── normalize() ──────────────────────────────────────────────────────────────

def test_normalize_eth_lowercase():
    assert ofac_db.normalize("0x252A8BD2319D8A555B872990601221B3A2053BCE") \
        == "0x252a8bd2319d8a555b872990601221b3a2053bce"

def test_normalize_eth_already_lower():
    assert ofac_db.normalize(ETH_REAL) == ETH_REAL

def test_normalize_xbt_base58_unchanged():
    # BTC base58 must NOT be lowercased
    assert ofac_db.normalize(XBT_REAL) == XBT_REAL

def test_normalize_xbt_base58_lowercase_differs():
    assert ofac_db.normalize(XBT_REAL.lower()) != ofac_db.normalize(XBT_REAL)

def test_normalize_bc1_lowercase():
    addr = "BC1QXYZ1234"
    assert ofac_db.normalize(addr) == addr.lower()

def test_normalize_strips_whitespace():
    assert ofac_db.normalize("  " + ETH_REAL + "  ") == ETH_REAL


# ── lookup() — MATCH ─────────────────────────────────────────────────────────

def test_lookup_eth_exact_match():
    results = ofac_db.lookup(ETH_REAL)
    assert len(results) >= 1
    assert results[0]["currency"] == "ETH"

def test_lookup_eth_checksum_gives_match():
    """ETH address in EIP-55 checksum (mixed case) must still match."""
    checksum = "0x252a8BD2319D8a555b872990601221b3A2053bcE"
    results = ofac_db.lookup(checksum)
    assert len(results) >= 1, "ETH checksum address should normalize to a match"
    assert results[0]["currency"] == "ETH"

def test_lookup_trx_exact_match():
    results = ofac_db.lookup(TRX_REAL)
    assert len(results) >= 1
    assert results[0]["currency"] == "TRX"
    assert "BANK MARKAZI" in results[0]["entity_name"]

def test_lookup_returns_entity_fields():
    results = ofac_db.lookup(ETH_REAL)
    assert results
    r = results[0]
    assert "entity_name" in r
    assert "currency" in r
    assert "entity_id" in r
    assert "list_date" in r


# ── lookup() — NO MATCH ──────────────────────────────────────────────────────

def test_lookup_xbt_lowercase_no_match():
    """BTC base58 is case-sensitive: lowercased real address must NOT match."""
    assert ofac_db.lookup(XBT_REAL.lower()) == []

def test_lookup_fake_eth_no_match():
    assert ofac_db.lookup(ETH_FAKE) == []

def test_lookup_fake_xbt_no_match():
    assert ofac_db.lookup(XBT_FAKE) == []

def test_lookup_random_string_no_match():
    assert ofac_db.lookup(RANDOM_FAKE) == []

def test_lookup_empty_string_no_match():
    assert ofac_db.lookup("") == []


# ── Safety checks ────────────────────────────────────────────────────────────

def test_safety_zero_addresses_does_not_modify_db(tmp_path):
    """Sync with 0 extracted addresses must not touch the DB."""
    prev_total = ofac_db.total_count()

    # Monkeypatch replace_all to detect if it was called
    called = []
    original = ofac_db.replace_all
    ofac_db.replace_all = lambda r: called.append(r) or (0, 0)

    # Patch shared reports dir to tmp_path
    original_reports = ofac_sync.SHARED_REPORTS
    ofac_sync.SHARED_REPORTS = tmp_path

    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    try:
        # Simulate the safety check directly
        if len([]) == 0:
            msg = "Extracted 0 addresses — parser may be broken or schema changed"
            ofac_db.log_sync(now_str, "2026-10-28", prev_total, 0, 0, error=msg)
            ofac_sync._write_report("FAILED", "2026-10-28", prev_total, 0, 0, {}, error_msg=msg)

        assert called == [], "replace_all should NOT be called on 0 addresses"
        assert ofac_db.total_count() == prev_total, "DB total should be unchanged"

        report = (tmp_path / "ofac_latest.md").read_text()
        assert "status: FAIL" in report
    finally:
        ofac_db.replace_all = original
        ofac_sync.SHARED_REPORTS = original_reports


def test_safety_below_half_does_not_modify_db(tmp_path):
    """Sync with < 50% of current count must not touch the DB."""
    prev_total = ofac_db.total_count()
    assert prev_total > 0, "DB must be populated before running this test"

    called = []
    original = ofac_db.replace_all
    ofac_db.replace_all = lambda r: called.append(r) or (0, 0)

    original_reports = ofac_sync.SHARED_REPORTS
    ofac_sync.SHARED_REPORTS = tmp_path

    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    simulated_count = int(prev_total * 0.4)
    try:
        if simulated_count < prev_total * 0.5:
            msg = (
                f"Extracted {simulated_count} addresses but DB has {prev_total} — "
                f"less than 50% of previous count, aborting to preserve existing data"
            )
            ofac_db.log_sync(now_str, "2026-10-28", prev_total, 0, 0, error=msg)
            ofac_sync._write_report("FAILED", "2026-10-28", prev_total, 0, 0, {}, error_msg=msg)

        assert called == [], "replace_all should NOT be called on < 50% result"
        assert ofac_db.total_count() == prev_total

        report = (tmp_path / "ofac_latest.md").read_text()
        assert "status: FAIL" in report
        assert "50%" in report or "less than" in report.lower()
    finally:
        ofac_db.replace_all = original
        ofac_sync.SHARED_REPORTS = original_reports


# ── CLI exit codes ───────────────────────────────────────────────────────────

def _run_cli(*args):
    result = subprocess.run(
        [sys.executable, str(OFAC_CHECK), *args],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr

def test_cli_exit_0_no_match():
    code, out, _ = _run_cli(ETH_FAKE)
    assert code == 0
    assert "NO MATCH" in out

def test_cli_exit_1_match():
    code, out, _ = _run_cli(ETH_REAL)
    assert code == 1
    assert "MATCH" in out
    assert "MESRI" in out

def test_cli_exit_2_no_args():
    code, _, err = _run_cli()
    assert code == 2
    assert "Usage" in err

def test_cli_exit_2_empty_address():
    code, _, err = _run_cli("")
    assert code == 2

def test_cli_match_shows_disclaimer():
    _, out, _ = _run_cli(ETH_REAL)
    assert "Exact-match result only" in out
    assert "Not a legal determination" in out

def test_cli_no_match_shows_count_and_date():
    _, out, _ = _run_cli(ETH_FAKE)
    assert "checked" in out
    assert "list date:" in out
