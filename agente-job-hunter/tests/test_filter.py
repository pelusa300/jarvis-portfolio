# tests/test_filter.py
import pytest
from filters.job_filter import filter_jobs, categorize_job, _has_excluded_title, _title_has_role

def make_job(**kwargs):
    defaults = {
        "title": "Test Job",
        "company": "TestCo",
        "location": "Remote",
        "url": "https://example.com/job/1",
        "description": "AML compliance role in crypto blockchain",
        "source": "remote_ok",
        "date_posted": "2026-03-24",
        "salary_min": None,
        "salary_max": None,
    }
    defaults.update(kwargs)
    return defaults

def test_strict_list_requires_remote_role_and_sector():
    # title must also contain a compliance keyword for STRICT
    job = make_job(title="AML Analyst", location="Remote", description="AML Compliance crypto blockchain")
    result = filter_jobs([job])
    assert job in result["strict"]

def test_strict_rejects_non_remote():
    job = make_job(location="New York", description="AML Compliance crypto blockchain")
    result = filter_jobs([job])
    assert job not in result["strict"]

def test_strict_rejects_missing_role_keyword():
    job = make_job(location="Remote", description="blockchain crypto developer")
    result = filter_jobs([job])
    assert job not in result["strict"]

def test_strict_rejects_missing_sector_keyword():
    job = make_job(location="Remote", description="AML Compliance banking")
    result = filter_jobs([job])
    assert job not in result["strict"]

def test_broad_requires_two_criteria():
    # Solo tiene 'remote' — no pasa
    job = make_job(location="Remote", description="Software engineer Java")
    result = filter_jobs([job])
    assert job not in result["broad"]

def test_broad_passes_with_remote_and_role():
    job = make_job(location="Remote", description="KYC analyst banking")
    result = filter_jobs([job])
    assert job in result["broad"]

def test_broad_passes_with_known_company():
    job = make_job(location="On-site", company="Coinbase", description="AML analyst")
    result = filter_jobs([job])
    assert job in result["broad"]

def test_hybrid_appears_in_broad_not_strict():
    job = make_job(location="Hybrid", description="AML crypto compliance")
    result = filter_jobs([job])
    assert job not in result["strict"]
    assert job in result["broad"]

def test_no_duplicates_between_lists():
    job = make_job(location="Remote", description="AML crypto blockchain compliance")
    result = filter_jobs([job])
    assert result["strict"].count(job) <= 1
    assert result["broad"].count(job) <= 1

def test_discards_irrelevant_jobs():
    job = make_job(location="On-site", description="Software engineer Python Django")
    result = filter_jobs([job])
    assert job not in result["strict"]
    assert job not in result["broad"]


def make_cat_job(title, description=""):
    return {"title": title, "description": description}

def test_categorize_aml():
    assert categorize_job(make_cat_job("AML Analyst")) == "AML"

def test_categorize_kyc():
    assert categorize_job(make_cat_job("KYC Manager")) == "KYC"

def test_categorize_financial_crimes():
    assert categorize_job(make_cat_job("Financial Crimes Investigator")) == "Financial Crimes"

def test_categorize_compliance():
    assert categorize_job(make_cat_job("Compliance Officer")) == "Compliance"

def test_categorize_otras():
    assert categorize_job(make_cat_job("Software Engineer")) == "Otras"

def test_categorize_aml_wins_over_compliance():
    # AML has higher priority than Compliance
    job = make_cat_job("Compliance", description="anti-money laundering program")
    assert categorize_job(job) == "AML"


# --- _has_excluded_title tests ---

def test_excluded_title_brand_designer():
    assert _has_excluded_title({"title": "Brand Designer"}) is True

def test_excluded_title_poker_room_manager():
    assert _has_excluded_title({"title": "Poker Room Manager"}) is True

def test_excluded_title_devops():
    assert _has_excluded_title({"title": "Senior DevOps Engineer"}) is True

def test_excluded_title_hr_manager():
    assert _has_excluded_title({"title": "HR Manager"}) is True

def test_excluded_title_aml_analyst_passes():
    assert _has_excluded_title({"title": "AML Analyst"}) is False

def test_excluded_title_compliance_officer_passes():
    assert _has_excluded_title({"title": "Compliance Officer"}) is False

def test_excluded_title_aml_compliance_engineer_passes():
    # "engineer" alone is NOT in the deny-list; only compound phrases are
    assert _has_excluded_title({"title": "AML Compliance Engineer"}) is False

def test_excluded_title_empty_string():
    assert _has_excluded_title({"title": ""}) is False

def test_excluded_title_none():
    assert _has_excluded_title({"title": None}) is False

def test_excluded_title_missing_key():
    assert _has_excluded_title({}) is False

# --- filter_jobs integration tests for title exclusion ---

def test_filter_rejects_excluded_title_in_strict():
    job = make_job(title="Brand Designer", location="Remote",
                   description="AML compliance crypto blockchain")
    result = filter_jobs([job])
    assert job not in result["strict"]
    assert job not in result["broad"]

def test_filter_passes_aml_compliance_engineer():
    job = make_job(title="AML Compliance Engineer", location="Remote",
                   description="AML compliance crypto blockchain")
    result = filter_jobs([job])
    assert job in result["strict"]


# --- new TITLE_EXCLUDE_KEYWORDS additions ---

def test_excluded_title_ai_trainer():
    assert _has_excluded_title({"title": "AI Trainer"}) is True

def test_excluded_title_data_center_manager():
    assert _has_excluded_title({"title": "Data Center Site Start Up Manager"}) is True

def test_excluded_title_customer_service():
    assert _has_excluded_title({"title": "Customer Service Representative"}) is True

def test_excluded_title_accounting_clerk():
    assert _has_excluded_title({"title": "Accounting Clerk"}) is True

def test_excluded_title_account_executive():
    assert _has_excluded_title({"title": "Account Executive"}) is True

def test_excluded_title_revenue_operations():
    assert _has_excluded_title({"title": "Revenue Operations Manager"}) is True

def test_excluded_title_partnerships_manager():
    assert _has_excluded_title({"title": "Partnerships Manager"}) is True

def test_excluded_title_crypto_trader():
    assert _has_excluded_title({"title": "Crypto Trader"}) is True

def test_excluded_title_crypto_analyst_trader():
    assert _has_excluded_title({"title": "Crypto Analyst Trader"}) is True


# --- _title_has_role tests ---

def test_title_has_role_compliance():
    assert _title_has_role({"title": "Compliance Officer"}) is True

def test_title_has_role_aml():
    assert _title_has_role({"title": "AML Analyst"}) is True

def test_title_has_role_kyc():
    assert _title_has_role({"title": "KYC Manager"}) is True

def test_title_has_role_financial_crimes():
    assert _title_has_role({"title": "Financial Crimes Investigator"}) is True

def test_title_has_role_sanctions():
    assert _title_has_role({"title": "Sanctions Specialist"}) is True

def test_title_has_role_fraud():
    assert _title_has_role({"title": "Fraud Analyst"}) is True

def test_title_has_role_risk():
    assert _title_has_role({"title": "Risk Officer"}) is True

def test_title_has_role_investigator():
    assert _title_has_role({"title": "Financial Investigator"}) is True

def test_title_has_role_examiner():
    assert _title_has_role({"title": "BSA Examiner"}) is True

def test_title_has_role_saas_architect_fails():
    assert _title_has_role({"title": "SaaS Platform Architect"}) is False

def test_title_has_role_data_center_fails():
    assert _title_has_role({"title": "Data Center Manager"}) is False

def test_title_has_role_none():
    assert _title_has_role({"title": None}) is False

def test_title_has_role_missing_key():
    assert _title_has_role({}) is False


# --- STRICT now requires title compliance keyword ---

def test_strict_rejects_job_without_compliance_title():
    # "SaaS Platform Architect" passes description keywords but title has no compliance word
    job = make_job(title="SaaS Platform Architect", location="Remote",
                   description="AML compliance crypto blockchain remote")
    result = filter_jobs([job])
    assert job not in result["strict"]

def test_strict_allows_job_with_compliance_title():
    job = make_job(title="Financial Crimes Analyst", location="Remote",
                   description="AML crypto blockchain remote")
    result = filter_jobs([job])
    assert job in result["strict"]

def test_broad_still_passes_without_compliance_title():
    # BROAD does NOT require title compliance keyword — only STRICT does
    job = make_job(title="SaaS Platform Architect", location="Remote",
                   description="AML compliance crypto blockchain remote")
    result = filter_jobs([job])
    assert job in result["broad"]
