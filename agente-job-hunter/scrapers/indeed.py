import logging
import requests
from typing import List

logger = logging.getLogger(__name__)

REMOTIVE_SEARCHES = [
    "compliance",
    "aml",
    "kyc",
]


def fetch_jobs() -> List[dict]:
    """Fetches compliance/AML/KYC jobs from Remotive public API. Returns [] on failure."""
    jobs = []
    seen_urls: set = set()

    for term in REMOTIVE_SEARCHES:
        try:
            resp = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": term, "limit": 20},
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code != 200:
                logger.warning(f"Remotive {term}: HTTP {resp.status_code}")
                continue
            data = resp.json()
            for j in data.get("jobs", []):
                url = j.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                jobs.append({
                    "title":       j.get("title", ""),
                    "company":     j.get("company_name", ""),
                    "url":         url,
                    "location":    j.get("candidate_required_location", "Remote"),
                    "description": j.get("description", "")[:1000],
                    "source":      "remotive",
                    "date_posted": j.get("publication_date", "")[:10],
                    "salary_min":  None,
                    "salary_max":  None,
                })
        except Exception as e:
            logger.error(f"Remotive {term}: {e}")

    logger.info(f"remotive: {len(jobs)} jobs fetched")
    return jobs
