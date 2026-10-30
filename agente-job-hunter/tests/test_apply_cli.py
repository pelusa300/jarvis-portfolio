"""
Tests para apply.py — se prueban las funciones cmd_* directamente
con argparse.Namespace mock, sin subprocess.
"""
import argparse
import json
import pytest
from pathlib import Path

from tracker.db import init_db, get_application, list_applications, VALID_STATUSES


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    init_db(path)
    import tracker.db as _db
    monkeypatch.setattr(_db, "DB_PATH", path)
    import storage.store as _store
    monkeypatch.setattr(_store, "_DB_PATH", path)
    return path


def _ns(**kwargs) -> argparse.Namespace:
    defaults = {
        "company": None, "title": None, "url": None, "source": None,
        "status": "por aplicar", "date_applied": None,
        "notes": None, "no_reapply_until": None, "from_report": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ── cmd_add ───────────────────────────────────────────────────────────────

def test_cmd_add_basic(capsys, isolated_db):
    from apply import cmd_add
    cmd_add(_ns(company="Coinbase", title="AML Analyst"))
    out = capsys.readouterr().out
    assert "Aplicación #1" in out
    assert "Coinbase" in out


def test_cmd_add_with_status(capsys, isolated_db):
    from apply import cmd_add
    cmd_add(_ns(company="Ripple", title="KYC Spec", status="aplicada",
                date_applied="2026-10-26"))
    apps = list_applications()
    assert apps[0]["status"] == "aplicada"
    assert apps[0]["date_applied"] == "2026-10-26"


def test_cmd_add_with_no_reapply(capsys, isolated_db):
    from apply import cmd_add
    cmd_add(_ns(company="Flex", title="Financial Crimes Analyst",
                status="aplicada", date_applied="2026-10-26",
                no_reapply_until="2027-04-01"))
    apps = list_applications()
    assert apps[0]["no_reapply_until"] == "2027-04-01"


def test_cmd_add_from_report(capsys, isolated_db, tmp_path, monkeypatch):
    from apply import cmd_add
    report = {
        "strict": [],
        "broad": [{"company": "Chainalysis", "title": "Compliance Analyst",
                   "url": "https://ch.com/job", "source": "greenhouse"}],
    }
    report_path = tmp_path / "job_market_latest.json"
    report_path.write_text(json.dumps(report))
    import apply as _apply
    monkeypatch.setattr(_apply, "_REPORT_JSON", report_path)

    cmd_add(_ns(from_report=1, status="por aplicar"))
    apps = list_applications()
    assert apps[0]["company"] == "Chainalysis"
    assert apps[0]["url"] == "https://ch.com/job"


def test_cmd_add_from_report_out_of_range(capsys, isolated_db, tmp_path, monkeypatch):
    from apply import cmd_add
    report = {"strict": [], "broad": [{"company": "X", "title": "Y"}]}
    report_path = tmp_path / "job_market_latest.json"
    report_path.write_text(json.dumps(report))
    import apply as _apply
    monkeypatch.setattr(_apply, "_REPORT_JSON", report_path)

    with pytest.raises(SystemExit):
        cmd_add(_ns(from_report=5, status="por aplicar"))


# ── cmd_update ────────────────────────────────────────────────────────────

def test_cmd_update_status(capsys, isolated_db):
    from apply import cmd_add, cmd_update
    cmd_add(_ns(company="X", title="Y"))
    upd_ns = argparse.Namespace(id=1, status="entrevista", next_step=None,
                                follow_up_date=None, notes=None,
                                no_reapply_until=None, date_applied=None)
    cmd_update(upd_ns)
    assert get_application(1)["status"] == "entrevista"


def test_cmd_update_not_found(capsys, isolated_db):
    from apply import cmd_update
    upd_ns = argparse.Namespace(id=999, status="entrevista", next_step=None,
                                follow_up_date=None, notes=None,
                                no_reapply_until=None, date_applied=None)
    with pytest.raises(SystemExit):
        cmd_update(upd_ns)


def test_cmd_update_no_fields_exits_zero(capsys, isolated_db):
    from apply import cmd_add, cmd_update
    cmd_add(_ns(company="X", title="Y"))
    upd_ns = argparse.Namespace(id=1, status=None, next_step=None,
                                follow_up_date=None, notes=None,
                                no_reapply_until=None, date_applied=None)
    with pytest.raises(SystemExit) as exc_info:
        cmd_update(upd_ns)
    assert exc_info.value.code == 0


# ── cmd_list ──────────────────────────────────────────────────────────────

def test_cmd_list_empty(capsys, isolated_db):
    from apply import cmd_list
    cmd_list(argparse.Namespace(status=None))
    out = capsys.readouterr().out
    assert "No hay aplicaciones" in out


def test_cmd_list_shows_entries(capsys, isolated_db):
    from apply import cmd_add, cmd_list
    cmd_add(_ns(company="Coinbase", title="AML Analyst"))
    cmd_add(_ns(company="Ripple", title="KYC Spec", status="aplicada"))
    cmd_list(argparse.Namespace(status=None))
    out = capsys.readouterr().out
    assert "Coinbase" in out
    assert "Ripple" in out
    assert "Total: 2" in out


def test_cmd_list_filter_by_status(capsys, isolated_db):
    from apply import cmd_add, cmd_list
    cmd_add(_ns(company="A", title="T1"))
    cmd_add(_ns(company="B", title="T2", status="aplicada"))
    capsys.readouterr()  # limpiar outputs de cmd_add
    cmd_list(argparse.Namespace(status="aplicada"))
    out = capsys.readouterr().out
    assert "B" in out
    assert "T1" not in out   # T1 es título de empresa A, no debe aparecer
    assert "Total: 1" in out
