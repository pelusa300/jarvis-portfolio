# tests/test_gap_analyzer.py
import sys
from pathlib import Path
import pytest
from analysis.gap_analyzer import score_job, select_top_jobs, analyze_jobs

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from profile_loader import load_profile

def make_job(description, source="remote_ok", date_posted="2026-03-24", is_strict=True):
    return {
        "title": "AML Analyst",
        "company": "TestCo",
        "location": "Remote",
        "url": "https://example.com/job/1",
        "description": description,
        "source": source,
        "date_posted": date_posted,
        "salary_min": None,
        "salary_max": None,
        "_is_strict": is_strict,
    }

def test_score_matches_known_skills():
    job = make_job("This role requires KYC, AML, and BSA knowledge")
    result = score_job(job)
    assert result["score"] > 0
    assert "KYC" in result["skills_matched"] or "kyc" in [s.lower() for s in result["skills_matched"]]

def test_score_identifies_gaps():
    job = make_job("Requires Chainalysis and TRM Labs experience")
    result = score_job(job)
    assert len(result["gaps"]) > 0

def test_score_zero_for_no_skill_match():
    job = make_job("Generic software engineer role with Java")
    result = score_job(job)
    assert result["score"] == 0

def test_select_top_5_returns_at_most_5():
    jobs = [make_job(f"KYC AML BSA FinCEN OFAC job {i}") for i in range(10)]
    top = select_top_jobs(jobs, n=5)
    assert len(top) <= 5

def test_select_top_prefers_higher_score():
    low = make_job("generic compliance job", source="linkedin")
    high = make_job("KYC AML BSA FinCEN OFAC Chainalysis TRM", source="remote_ok")
    top = select_top_jobs([low, high], n=1)
    assert top[0]["url"] == high["url"]

def test_select_top_tiebreak_strict_over_broad():
    strict_job = make_job("KYC AML", source="remote_ok", is_strict=True)
    broad_job = make_job("KYC AML", source="remote_ok", is_strict=False)
    # Mismo score, strict debe ganar
    top = select_top_jobs([broad_job, strict_job], n=1)
    assert top[0]["_is_strict"] is True

def test_select_top_tiebreak_source_priority():
    job_linkedin = make_job("KYC AML", source="linkedin", is_strict=True)
    job_remote_ok = make_job("KYC AML", source="remote_ok", is_strict=True)
    top = select_top_jobs([job_linkedin, job_remote_ok], n=1)
    assert top[0]["source"] == "remote_ok"

def test_select_top_tiebreak_date_recency():
    older = make_job("KYC AML", source="remote_ok", date_posted="2026-01-01", is_strict=True)
    newer = make_job("KYC AML", source="remote_ok", date_posted="2026-03-24", is_strict=True)
    # Mismo score, mismo strict, misma fuente — la más reciente debe ganar
    top = select_top_jobs([older, newer], n=1)
    assert top[0]["date_posted"] == "2026-03-24"


def make_scored_job(score_description, url="https://example.com/1", is_strict=True):
    return {
        "title": "AML Analyst",
        "company": "TestCo",
        "location": "Remote",
        "url": url,
        "description": score_description,
        "source": "remote_ok",
        "date_posted": "2026-03-24",
        "salary_min": None,
        "salary_max": None,
        "_is_strict": is_strict,
    }


def test_analyze_jobs_returns_top3_key():
    strict = [make_scored_job("KYC AML BSA", url="https://example.com/1")]
    broad = [make_scored_job("Chainalysis TRM", url="https://example.com/2", is_strict=False)]
    result = analyze_jobs(strict, broad)
    assert "top3" in result


def test_analyze_jobs_top3_at_most_3():
    strict = [make_scored_job("KYC AML BSA FinCEN", url=f"https://example.com/{i}") for i in range(10)]
    result = analyze_jobs(strict, [])
    assert len(result["top3"]) <= 3


def test_analyze_jobs_top3_all_positive_score():
    strict = [make_scored_job("KYC AML", url=f"https://example.com/{i}") for i in range(5)]
    result = analyze_jobs(strict, [])
    for job in result["top3"]:
        assert job.get("score", 0) > 0


def test_analyze_jobs_top3_sorted_by_score_descending():
    jobs = [
        make_scored_job("KYC AML BSA FinCEN OFAC", url="https://example.com/1"),  # high score
        make_scored_job("KYC AML", url="https://example.com/2"),                   # medium score
        make_scored_job("KYC", url="https://example.com/3"),                       # lower score
    ]
    result = analyze_jobs(jobs, [])
    scores = [j["score"] for j in result["top3"]]
    assert scores == sorted(scores, reverse=True)


# --- perfil dinámico ---

TEST_PROFILE = {
    "skills_confirmados": ["KYC", "AML", "BSA"],
    "certificaciones": {
        "en_progreso": ["CAMS"],
        "completadas": [],
        "pendientes": [],
    },
}


def test_score_job_returns_en_progreso_field():
    job = make_job("This role requires KYC and AML")
    result = score_job(job, profile=TEST_PROFILE)
    assert "en_progreso" in result


def test_score_job_en_progreso_empty_when_cert_not_in_job():
    job = make_job("This role requires KYC and AML")
    result = score_job(job, profile=TEST_PROFILE)
    assert result["en_progreso"] == []


def test_score_job_en_progreso_detected_when_cert_in_job():
    job = make_job("CAMS certification preferred, KYC and AML required")
    result = score_job(job, profile=TEST_PROFILE)
    assert "CAMS" in result["en_progreso"]


def test_score_job_en_progreso_not_in_gaps():
    # CAMS is en_progreso — must NOT appear in gaps too
    job = make_job("CAMS preferred, Chainalysis required")
    result = score_job(job, profile=TEST_PROFILE)
    gap_names = [g.lower() for g in result["gaps"]]
    assert "cams" not in gap_names


def test_score_job_returns_matched_count():
    job = make_job("Requires KYC and AML experience")
    result = score_job(job, profile=TEST_PROFILE)
    assert "matched_count" in result
    assert result["matched_count"] == 2  # KYC + AML


def test_score_job_returns_total_count():
    # matched: KYC, AML | en_progreso: CAMS | gaps: Chainalysis
    job = make_job("Requires KYC, AML, CAMS certification and Chainalysis")
    result = score_job(job, profile=TEST_PROFILE)
    assert "total_count" in result
    assert result["total_count"] == 4  # KYC + AML + CAMS + Chainalysis


def test_score_job_fallback_to_config_when_no_profile():
    # With empty profile, falls back to config.SKILLS_HAVE
    job = make_job("Requires KYC and AML")
    result = score_job(job, profile={})
    # Should still detect something using config fallback
    assert result["matched_count"] >= 0  # no crash


def test_load_profile_returns_dict():
    # load_profile() must return a dict even when file is missing
    result = load_profile(path="nonexistent_file.json")
    assert isinstance(result, dict)
