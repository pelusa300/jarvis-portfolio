import pytest
from datetime import date, timedelta
from pathlib import Path
from storage.store import is_new_job, mark_as_seen, prune_old_entries
from tracker.db import init_db, is_url_seen


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    init_db(path)
    import tracker.db as _db
    monkeypatch.setattr(_db, "DB_PATH", path)
    import storage.store as _store
    monkeypatch.setattr(_store, "_DB_PATH", path)
    return path


def test_is_new_job_true(db):
    assert is_new_job("https://new.com", db) is True


def test_is_new_job_false_after_seen(db):
    mark_as_seen("https://a.com", db)
    assert is_new_job("https://a.com", db) is False


def test_mark_as_seen_idempotent(db):
    mark_as_seen("https://a.com", db)
    mark_as_seen("https://a.com", db)  # no error
    assert not is_new_job("https://a.com", db)


def test_prune_removes_old(db):
    from tracker.db import save_seen_url
    old = (date.today() - timedelta(days=91)).isoformat()
    save_seen_url("https://old.com", old, db)
    save_seen_url("https://new.com", date.today().isoformat(), db)
    removed = prune_old_entries(ttl_days=90, db_path=db)
    assert removed == 1
    assert is_new_job("https://old.com", db)
    assert not is_new_job("https://new.com", db)
