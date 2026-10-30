"""
Tests para la función deduplicate() de main.py:
- Vacante ya en seen_scrapes → se filtra
- Vacante ya registrada en applications → se filtra
- Empresa con no_reapply_until vigente → se filtra
- Vacante nueva, empresa no bloqueada → pasa
"""
import pytest
from datetime import date, timedelta

from tracker.db import init_db, save_seen_url, add_application


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    init_db(path)
    import tracker.db as _db
    monkeypatch.setattr(_db, "DB_PATH", path)
    import storage.store as _store
    monkeypatch.setattr(_store, "_DB_PATH", path)
    return path


def _make_job(url="https://coinbase.com/job/1", company="Coinbase"):
    return {"url": url, "company": company, "title": "AML Analyst"}


# ── deduplicate ───────────────────────────────────────────────────────────

def test_dedup_passes_new_job(isolated_db):
    from main import deduplicate
    jobs = [_make_job()]
    result = deduplicate(jobs)
    assert len(result) == 1


def test_dedup_filters_seen_url(isolated_db):
    from main import deduplicate
    save_seen_url("https://coinbase.com/job/1", date.today().isoformat())
    jobs = [_make_job("https://coinbase.com/job/1")]
    result = deduplicate(jobs)
    assert len(result) == 0


def test_dedup_filters_url_in_applications(isolated_db):
    from main import deduplicate
    add_application(company="Coinbase", title="AML", url="https://coinbase.com/job/2")
    jobs = [_make_job("https://coinbase.com/job/2")]
    result = deduplicate(jobs)
    assert len(result) == 0


def test_dedup_filters_blocked_company(isolated_db):
    from main import deduplicate
    future = (date.today() + timedelta(days=180)).isoformat()
    add_application(company="Flex", title="Financial Crimes", status="aplicada",
                    no_reapply_until=future)
    jobs = [_make_job(url="https://flex.com/new-job", company="Flex")]
    result = deduplicate(jobs)
    assert len(result) == 0


def test_dedup_passes_expired_no_reapply(isolated_db):
    from main import deduplicate
    past = (date.today() - timedelta(days=1)).isoformat()
    add_application(company="River", title="Compliance", status="rechazada",
                    no_reapply_until=past)
    jobs = [_make_job(url="https://river.com/new-job", company="River")]
    result = deduplicate(jobs)
    assert len(result) == 1


def test_dedup_skips_jobs_without_url(isolated_db):
    from main import deduplicate
    jobs = [{"company": "X", "title": "Y"}]  # sin url
    result = deduplicate(jobs)
    assert len(result) == 0


def test_dedup_company_match_is_case_insensitive(isolated_db):
    from main import deduplicate
    future = (date.today() + timedelta(days=90)).isoformat()
    add_application(company="FLEX", title="T", no_reapply_until=future)
    jobs = [_make_job(url="https://flex.com/job", company="flex")]
    result = deduplicate(jobs)
    assert len(result) == 0
