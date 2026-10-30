import logging
import re
from typing import List

import requests

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobHunterBot/1.0)"}

GREENHOUSE_COMPANIES = [
    "coinbase",
    "kraken",
    "circlepay",
    "ripple",
    "gemini",
    "bitgo",
]

GREENHOUSE_BASE = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"

# Keywords to keep — compliance-adjacent roles only
RELEVANT_KEYWORDS = {
    "compliance", "aml", "kyc", "sanctions", "bsa",
    "regulatory", "risk", "fraud", "financial crime",
}


def fetch_jobs() -> List[dict]:
    """Fetches compliance-related jobs from Greenhouse boards. Returns [] on any failure."""
    jobs = []

    for company in GREENHOUSE_COMPANIES:
        try:
            url = GREENHOUSE_BASE.format(company=company)
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            data = response.json()

            raw_jobs = data.get("jobs", [])
            for item in raw_jobs:
                try:
                    job = _parse_job(item, company)
                    if job and _is_relevant(job["title"]):
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"greenhouse: error parsing job from {company}: {e}")

        except Exception as e:
            logger.error(f"greenhouse scraper failed for {company}: {e}")

    logger.info(f"greenhouse: {len(jobs)} jobs fetched")
    return jobs


def _parse_job(item: dict, company: str) -> dict:
    """Converts a Greenhouse API job dict to the standard schema."""
    title = item.get("title", "")
    url = item.get("absolute_url", "")
    location = (item.get("location") or {}).get("name", "Remote")
    raw_content = item.get("content", "") or ""
    description = _strip_html(raw_content)
    date_posted = _parse_date(item.get("updated_at", ""))

    return {
        "title": title,
        "company": company.capitalize(),
        "location": location,
        "url": url,
        "description": description,
        "source": "greenhouse",
        "date_posted": date_posted,
        "salary_min": None,
        "salary_max": None,
    }


def _is_relevant(title: str) -> bool:
    """Returns True if the job title contains at least one compliance keyword."""
    lower = title.lower()
    return any(kw in lower for kw in RELEVANT_KEYWORDS)


def _strip_html(text: str) -> str:
    """Removes HTML tags and decodes common HTML entities."""
    no_tags = re.sub(r"<[^>]+>", " ", text)
    entities = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&nbsp;": " ", "&quot;": '"', "&#39;": "'",
    }
    for entity, char in entities.items():
        no_tags = no_tags.replace(entity, char)
    return re.sub(r"\s+", " ", no_tags).strip()


def _parse_date(raw: str) -> str:
    """Returns the first 10 characters of an ISO datetime (YYYY-MM-DD), or ''."""
    if not raw:
        return ""
    return raw[:10]
