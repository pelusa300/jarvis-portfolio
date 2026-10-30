# tests/test_telegram_bot.py
import pytest
from notifier.telegram_bot import format_job_entry, split_into_messages, format_report

TELEGRAM_LIMIT = 4096

def make_job(title="AML Analyst", company="Kraken", location="Remote",
             url="https://example.com/1", skills_matched=None, gaps=None,
             claude_analysis=None, is_strict=True, en_progreso=None,
             matched_count=None, total_count=None):
    sm = skills_matched or ["KYC", "AML"]
    g = gaps or ["Chainalysis"]
    ep = en_progreso or []
    mc = matched_count if matched_count is not None else len(sm)
    tc = total_count if total_count is not None else len(sm) + len(g) + len(ep)
    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "description": "AML compliance crypto",
        "source": "remote_ok",
        "date_posted": "2026-03-24",
        "salary_min": None,
        "salary_max": None,
        "_is_strict": is_strict,
        "score": 0.8,
        "skills_matched": sm,
        "gaps": g,
        "en_progreso": ep,
        "matched_count": mc,
        "total_count": tc,
        "claude_analysis": claude_analysis,
    }

def test_format_job_contains_title_and_company():
    job = make_job()
    entry = format_job_entry(job, 1)
    assert "AML Analyst" in entry
    assert "Kraken" in entry

def test_format_job_contains_url():
    job = make_job()
    entry = format_job_entry(job, 1)
    assert "https://example.com/1" in entry

def test_format_job_shows_gaps():
    job = make_job(gaps=["Chainalysis", "TRM Labs"])
    entry = format_job_entry(job, 1)
    assert "Chainalysis" in entry

def test_format_job_includes_claude_analysis_when_present():
    job = make_job(claude_analysis="Te falta experiencia práctica con Chainalysis.")
    entry = format_job_entry(job, 1)
    assert "Te falta experiencia" in entry

def test_format_job_hybrid_has_warning():
    job = make_job(location="Hybrid")
    entry = format_job_entry(job, 1)
    assert "⚠️" in entry

def test_split_messages_respects_limit():
    jobs = [make_job(title=f"Job {i}", url=f"https://example.com/{i}") for i in range(20)]
    strict = jobs[:10]
    broad = jobs[10:]
    messages = split_into_messages(strict, broad, [], date_str="24 Mar 2026")
    for msg in messages:
        assert len(msg) <= TELEGRAM_LIMIT

def test_split_never_cuts_mid_entry():
    # Job con análisis Claude muy largo
    long_analysis = "X" * 3000
    job = make_job(claude_analysis=long_analysis)
    messages = split_into_messages([job], [], [], date_str="24 Mar 2026")
    for msg in messages:
        assert len(msg) <= TELEGRAM_LIMIT

def test_format_report_returns_list_of_strings():
    strict = [make_job()]
    broad = [make_job(title="Compliance Officer", url="https://example.com/2", is_strict=False)]
    messages = format_report(strict, broad, [])
    assert isinstance(messages, list)
    assert all(isinstance(m, str) for m in messages)

def test_format_job_shows_salary_both():
    job = make_job()
    job["salary_min"] = 80000
    job["salary_max"] = 120000
    entry = format_job_entry(job, 1)
    assert "💰" in entry
    assert "$80,000" in entry
    assert "$120,000" in entry

def test_format_job_shows_salary_min_only():
    job = make_job()
    job["salary_min"] = 80000
    job["salary_max"] = None
    entry = format_job_entry(job, 1)
    assert "💰" in entry
    assert "desde $80,000" in entry

def test_format_job_shows_salary_max_only():
    job = make_job()
    job["salary_min"] = None
    job["salary_max"] = 120000
    entry = format_job_entry(job, 1)
    assert "💰" in entry
    assert "hasta $120,000" in entry

def test_format_job_no_salary_line_when_absent():
    job = make_job()
    job["salary_min"] = None
    job["salary_max"] = None
    entry = format_job_entry(job, 1)
    assert "💰" not in entry


def test_broad_section_has_category_header():
    aml_job = make_job(title="AML Analyst", url="https://example.com/aml", is_strict=False)
    messages = split_into_messages([], [aml_job], [], date_str="26 Mar 2026")
    full = "\n".join(messages)
    assert "🔵 AML" in full  # verify the category header specifically, not just the job title

def test_empty_category_not_in_output():
    # A KYC job — "Financial Crimes" header should NOT appear
    kyc_job = make_job(title="KYC Manager", url="https://example.com/kyc", is_strict=False)
    messages = split_into_messages([], [kyc_job], [], date_str="26 Mar 2026")
    full = "\n".join(messages)
    assert "Financial Crimes" not in full

def test_summary_block_shows_top3():
    top3 = [
        {**make_job(title="Financial Crimes Analyst", url="https://example.com/1"), "score": 0.85},
        {**make_job(title="AML Investigator", url="https://example.com/2"), "score": 0.72},
        {**make_job(title="KYC Manager", url="https://example.com/3"), "score": 0.60},
    ]
    messages = split_into_messages([], [], top3, date_str="26 Mar 2026")
    full = "\n".join(messages)
    assert "TOP 3" in full
    assert "Financial Crimes Analyst" in full
    assert "KYC Manager" in full

def test_summary_block_absent_when_no_top3():
    messages = split_into_messages([], [], [], date_str="26 Mar 2026")
    full = "\n".join(messages)
    assert "TOP 3" not in full


# --- perfil dinámico: 🔄 y 📊 ---

def test_format_job_shows_en_progreso_cert():
    job = make_job(en_progreso=["CAMS"])
    entry = format_job_entry(job, 1)
    assert "🔄" in entry
    assert "CAMS" in entry


def test_format_job_en_progreso_absent_when_empty():
    job = make_job(en_progreso=[])
    entry = format_job_entry(job, 1)
    assert "🔄" not in entry


def test_format_job_shows_requisitos_count():
    job = make_job(matched_count=2, total_count=5)
    entry = format_job_entry(job, 1)
    assert "📊" in entry
    assert "2/5" in entry


def test_format_job_requisitos_absent_when_total_zero():
    job = make_job(matched_count=0, total_count=0)
    entry = format_job_entry(job, 1)
    assert "📊" not in entry


def test_format_job_requisitos_shows_correct_fraction():
    job = make_job(matched_count=6, total_count=10)
    entry = format_job_entry(job, 1)
    assert "6/10" in entry
