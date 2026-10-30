# tests/test_store.py
import json
import os
import pytest
from datetime import date, timedelta
from unittest.mock import patch
from storage.store import load_seen_urls, save_seen_urls, is_new_job, mark_as_seen, prune_old_entries

FAKE_PATH = "tests/fixtures/seen_jobs_test.json"

@pytest.fixture(autouse=True)
def cleanup():
    yield
    for f in [FAKE_PATH, FAKE_PATH.replace(".json", ".tmp")]:
        if os.path.exists(f):
            os.remove(f)

def test_load_empty_file(tmp_path):
    p = tmp_path / "seen.json"
    p.write_text("[]")
    assert load_seen_urls(str(p)) == []

def test_load_nonexistent_file(tmp_path):
    p = tmp_path / "notexist.json"
    assert load_seen_urls(str(p)) == []

def test_is_new_job_true():
    seen = [{"url": "https://a.com", "date_seen": "2026-03-01"}]
    assert is_new_job("https://b.com", seen) is True

def test_is_new_job_false():
    seen = [{"url": "https://a.com", "date_seen": "2026-03-01"}]
    assert is_new_job("https://a.com", seen) is False

def test_mark_as_seen_adds_entry():
    seen = []
    today = date.today().isoformat()
    result = mark_as_seen("https://new.com", seen)
    assert len(result) == 1
    assert result[0]["url"] == "https://new.com"
    assert result[0]["date_seen"] == today

def test_prune_removes_old_entries():
    old_date = (date.today() - timedelta(days=91)).isoformat()
    recent_date = date.today().isoformat()
    seen = [
        {"url": "https://old.com", "date_seen": old_date},
        {"url": "https://new.com", "date_seen": recent_date},
    ]
    result = prune_old_entries(seen, ttl_days=90)
    assert len(result) == 1
    assert result[0]["url"] == "https://new.com"

def test_save_is_atomic(tmp_path):
    p = tmp_path / "seen.json"
    seen = [{"url": "https://a.com", "date_seen": "2026-03-24"}]
    save_seen_urls(seen, str(p))
    assert p.exists()
    assert not (tmp_path / "seen.tmp").exists()
    data = json.loads(p.read_text())
    assert data == seen
