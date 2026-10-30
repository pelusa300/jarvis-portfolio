import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://cryptojobslist.com"
SEARCH_URLS = [
    f"{BASE_URL}/compliance",
    f"{BASE_URL}/aml",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"}


def fetch_jobs() -> List[dict]:
    """Scrapes Crypto Jobs List. Returns [] on any failure."""
    jobs = []
    seen_urls = set()

    for url in SEARCH_URLS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Try multiple selectors — site HTML may change
            job_cards = soup.select("article.job-card, div[data-job-id], li.job")
            if not job_cards:
                job_cards = soup.select("a[href*='/jobs/']")

            for card in job_cards:
                try:
                    job = _parse_card(card)
                    if job and job["url"] not in seen_urls:
                        seen_urls.add(job["url"])
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing card: {e}")

        except Exception as e:
            logger.error(f"crypto_jobs_list failed for {url}: {e}")

    logger.info(f"crypto_jobs_list: {len(jobs)} jobs fetched")
    return jobs


def _parse_card(card) -> Optional[dict]:
    """Extrae datos de una card de oferta."""
    link = card.find("a") if card.name != "a" else card
    if not link or not link.get("href"):
        return None

    href = link["href"]
    if not href.startswith("http"):
        href = BASE_URL + href

    title_el = card.find(["h2", "h3", "span"], class_=lambda c: c and "title" in c.lower()) if hasattr(card, 'find') else None
    company_el = card.find(["span", "div"], class_=lambda c: c and "company" in c.lower()) if hasattr(card, 'find') else None
    location_el = card.find(["span", "div"], class_=lambda c: c and "location" in c.lower()) if hasattr(card, 'find') else None

    return {
        "title": title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:80],
        "company": company_el.get_text(strip=True) if company_el else "",
        "location": location_el.get_text(strip=True) if location_el else "Remote",
        "url": href,
        "description": card.get_text(separator=" ", strip=True)[:1000] if hasattr(card, 'get_text') else "",
        "source": "crypto_jobs_list",
        "date_posted": "",
        "salary_min": None,
        "salary_max": None,
    }
