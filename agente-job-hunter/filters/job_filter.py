import logging
import re
from typing import List, Dict
import config

logger = logging.getLogger(__name__)

ROLE_KEYWORDS = ["aml", "anti-money laundering", "compliance", "kyc", "mlro"]
SECTOR_KEYWORDS = ["crypto", "blockchain", "web3", "defi", "exchange"]
REMOTE_KEYWORDS = ["remote", "100% remote"]
HYBRID_KEYWORDS = ["hybrid"]
TITLE_EXCLUDE_KEYWORDS = [
    "designer", "design", "creative",
    "software engineer", "backend engineer", "frontend engineer",
    "data engineer", "devops", "sre", "infrastructure",
    "software developer", "web developer", "mobile developer",
    "marketing", "sales", "growth",
    "data scientist", "machine learning", "ml engineer",
    "poker", "casino", "game developer", "game designer",
    "recruiter", "hr manager", "hr director", "hr business partner",
    "product manager", "scrum",
    "ai trainer", "data center",
    "customer service",
    "accounting clerk", "account executive",
    "revenue operations", "partnerships manager",
    "crypto trader", "crypto analyst trader",
]

# Keywords that must appear in the title for a job to pass the STRICT filter.
# Prevents jobs like "SaaS Platform Architect" (AML in description only) from
# being classified as strict compliance roles.
TITLE_STRICT_ROLE_KEYWORDS = [
    "compliance", "aml", "kyc", "financial crimes", "sanctions",
    "fraud", "risk", "analyst", "officer", "investigator", "examiner",
]

BROAD_TITLE_KEYWORDS = [
    "compliance", "aml", "kyc", "risk", "analyst", "investigator", "officer",
    "sanctions", "financial crime", "fraud", "onboarding", "due diligence", "cams",
]


def _text(job: dict) -> str:
    """Texto combinado para búsqueda de keywords."""
    return (
        (job.get("location") or "") + " " +
        (job.get("description") or "") + " " +
        (job.get("title") or "")
    ).lower()


def _has_keyword(text: str, keywords: list) -> bool:
    return any(kw.lower() in text for kw in keywords)


def _is_remote(text: str) -> bool:
    return _has_keyword(text, REMOTE_KEYWORDS)


def _is_hybrid(text: str) -> bool:
    return _has_keyword(text, HYBRID_KEYWORDS)


def _has_role(text: str) -> bool:
    return _has_keyword(text, ROLE_KEYWORDS)


def _has_sector(text: str) -> bool:
    return _has_keyword(text, SECTOR_KEYWORDS)


def _has_excluded_title(job: dict) -> bool:
    """Returns True if the job title matches any excluded role keyword (word-boundary).

    Uses word-boundary regex (not plain substring) to avoid false positives:
    e.g. 'design' should not reject 'Compliance by Design', and 'sales'
    should not reject 'Presales KYC Analyst'. Positive filters (_has_role etc.)
    use plain substring because false negatives there are cheaper than false positives here.
    """
    title = (job.get("title") or "").lower()
    return any(re.search(r"\b" + re.escape(kw) + r"\b", title) for kw in TITLE_EXCLUDE_KEYWORDS)


def _title_has_role(job: dict) -> bool:
    """Returns True if the job title contains at least one compliance/role keyword.

    Used by _passes_strict to prevent jobs whose titles are unrelated to compliance
    (e.g. 'SaaS Platform Architect') from passing just because their description
    mentions AML or DeFi. BROAD does not apply this check.
    """
    title = (job.get("title") or "").lower()
    return any(kw in title for kw in TITLE_STRICT_ROLE_KEYWORDS)


def _is_known_company(job: dict) -> bool:
    company = (job.get("company") or "").lower()
    return any(c.lower() in company for c in config.KNOWN_CRYPTO_COMPANIES)


def _passes_strict(job: dict) -> bool:
    if _has_excluded_title(job):
        return False
    if not _title_has_role(job):
        return False
    text = _text(job)
    return _is_remote(text) and _has_role(text) and _has_sector(text)


def _passes_broad(job: dict) -> bool:
    if _has_excluded_title(job):
        return False
    title = (job.get("title") or "").lower()
    if not any(kw in title for kw in BROAD_TITLE_KEYWORDS):
        logger.info(f"BLOCKED_TITLE: {job.get('title')} — {job.get('company')}")
        return False
    text = _text(job)
    criteria = [
        _is_remote(text) or _is_hybrid(text),
        _has_role(text),
        _has_sector(text),
        _is_known_company(job),
    ]
    return sum(criteria) >= 2


def filter_jobs(jobs: List[dict]) -> Dict[str, List[dict]]:
    """
    Recibe lista de jobs, devuelve {"strict": [...], "broad": [...]}.
    strict: cumple TODOS (remote + rol + sector)
    broad: cumple AL MENOS 2 de 4 criterios
    """
    strict = [j for j in jobs if _passes_strict(j)]
    broad = [j for j in jobs if _passes_broad(j)]
    return {"strict": strict, "broad": broad}


# Category classification — ordered by priority (highest first)
_CATEGORY_RULES = [
    ("AML",             ["anti-money laundering", "aml", "money laundering"]),
    ("Financial Crimes", ["financial crimes", "financial crime", "financial intelligence"]),
    ("KYC",             ["kyc", "know your customer", "cdd", "customer due diligence"]),
    ("Compliance",      ["compliance"]),
]
CATEGORY_ORDER = ["AML", "Financial Crimes", "KYC", "Compliance", "Otras"]


def categorize_job(job: dict) -> str:
    """
    Classifica un job en una categoría basada en título + descripción.
    Prioridad: AML > Financial Crimes > KYC > Compliance > Otras
    """
    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    for category, keywords in _CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return "Otras"
