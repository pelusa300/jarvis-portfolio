import pytest
from datetime import date, timedelta
from pathlib import Path
from tracker.db import (
    init_db, get_blocked_companies, get_stale_applications,
    add_application, update_application, list_applications, get_application,
    is_url_tracked, load_seen_urls, save_seen_url, is_url_seen,
    prune_seen_urls, VALID_STATUSES,
)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "test.db"
    init_db(path)
    return path


# ── seen_scrapes ──────────────────────────────────────────────────────────

def test_save_and_check_seen_url(db):
    save_seen_url("https://a.com", "2026-10-01", db)
    assert is_url_seen("https://a.com", db) is True
    assert is_url_seen("https://b.com", db) is False


def test_save_seen_url_idempotent(db):
    save_seen_url("https://a.com", "2026-10-01", db)
    save_seen_url("https://a.com", "2026-10-01", db)  # no error, no duplicate
    rows = load_seen_urls(db)
    assert len([r for r in rows if r["url"] == "https://a.com"]) == 1


def test_prune_seen_urls(db):
    old = (date.today() - timedelta(days=91)).isoformat()
    recent = date.today().isoformat()
    save_seen_url("https://old.com", old, db)
    save_seen_url("https://new.com", recent, db)
    removed = prune_seen_urls(ttl_days=90, db_path=db)
    assert removed == 1
    assert not is_url_seen("https://old.com", db)
    assert is_url_seen("https://new.com", db)


# ── applications ─────────────────────────────────────────────────────────

def test_add_and_get_application(db):
    id_ = add_application(company="Coinbase", title="AML Analyst", db_path=db)
    app = get_application(id_, db)
    assert app["company"] == "Coinbase"
    assert app["title"] == "AML Analyst"
    assert app["status"] == "por aplicar"
    assert app["link_status"] == "no verificado"


def test_add_application_with_url_unique(db):
    add_application(company="Ripple", title="KYC Specialist", url="https://r.com", db_path=db)
    with pytest.raises(Exception):
        add_application(company="Ripple", title="KYC Specialist", url="https://r.com", db_path=db)


def test_add_application_invalid_status(db):
    with pytest.raises(ValueError):
        add_application(company="X", title="Y", status="inventado", db_path=db)


def test_update_application_status(db):
    id_ = add_application(company="X", title="Y", db_path=db)
    update_application(id_, status="aplicada", db_path=db)
    assert get_application(id_, db)["status"] == "aplicada"


def test_update_application_invalid_status(db):
    id_ = add_application(company="X", title="Y", db_path=db)
    with pytest.raises(ValueError):
        update_application(id_, status="fantasma", db_path=db)


def test_list_applications_all(db):
    add_application(company="A", title="T1", db_path=db)
    add_application(company="B", title="T2", status="aplicada", db_path=db)
    apps = list_applications(db_path=db)
    assert len(apps) == 2


def test_list_applications_by_status(db):
    add_application(company="A", title="T1", db_path=db)
    add_application(company="B", title="T2", status="aplicada", db_path=db)
    pending = list_applications(status="por aplicar", db_path=db)
    assert len(pending) == 1
    assert pending[0]["company"] == "A"


def test_is_url_tracked(db):
    add_application(company="X", title="Y", url="https://job.com", db_path=db)
    assert is_url_tracked("https://job.com", db) is True
    assert is_url_tracked("https://other.com", db) is False


def test_get_blocked_companies(db):
    future = (date.today() + timedelta(days=30)).isoformat()
    past = (date.today() - timedelta(days=1)).isoformat()
    add_application(company="Flex", title="T", no_reapply_until=future, db_path=db)
    add_application(company="River", title="T", no_reapply_until=past, db_path=db)
    blocked = get_blocked_companies(db)
    assert "flex" in blocked
    assert "river" not in blocked


def test_get_stale_applications(db):
    old_date = (date.today() - timedelta(days=8)).isoformat()
    recent_date = date.today().isoformat()
    id1 = add_application(company="A", title="T", status="aplicada",
                          date_applied=old_date, db_path=db)
    id2 = add_application(company="B", title="T", status="aplicada",
                          date_applied=recent_date, db_path=db)
    stale = get_stale_applications(days=7, db_path=db)
    ids = [s["id"] for s in stale]
    assert id1 in ids
    assert id2 not in ids
