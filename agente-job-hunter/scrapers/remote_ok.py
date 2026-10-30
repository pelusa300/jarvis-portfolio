import logging
import requests
from bs4 import BeautifulSoup
from typing import List

logger = logging.getLogger(__name__)

REMOTE_OK_URL = "https://remoteok.com/api"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobHunterBot/1.0)"}


def fetch_jobs() -> List[dict]:
    """Fetches jobs from Remote OK public API. Returns [] on any failure."""
    try:
        response = requests.get(REMOTE_OK_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()

        # El primer elemento es metadata legal, los demás son jobs
        jobs_raw = [item for item in data if isinstance(item, dict) and item.get("id")]

        jobs = []
        for item in jobs_raw:
            tags = item.get("tags") or []
            tags_text = " ".join(tags)
            raw_desc = item.get("description") or ""
            clean_desc = BeautifulSoup(raw_desc, "html.parser").get_text(separator=" ", strip=True)
            description = clean_desc + " " + tags_text

            jobs.append({
                "title": item.get("position", ""),
                "company": item.get("company", ""),
                "location": "Remote",
                "url": item.get("url", ""),
                "description": description.strip(),
                "source": "remote_ok",
                "date_posted": _parse_date(item.get("date", "")),
                "salary_min": _parse_salary(item.get("salary_min")),
                "salary_max": _parse_salary(item.get("salary_max")),
            })

        logger.info(f"remote_ok: {len(jobs)} jobs fetched")
        return jobs

    except Exception as e:
        logger.error(f"remote_ok scraper failed: {e}")
        return []


def _parse_date(raw: str) -> str:
    """Extrae YYYY-MM-DD de la fecha de Remote OK."""
    if not raw:
        return ""
    return raw[:10]


def _parse_salary(raw) -> "int | None":
    try:
        return int(raw) if raw else None
    except (ValueError, TypeError):
        return None
