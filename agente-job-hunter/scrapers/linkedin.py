import logging
from typing import List, Optional
import config

logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    "AML Compliance Crypto Remote",
    "KYC Analyst Blockchain Remote",
]

def fetch_jobs() -> List[dict]:
    """
    Scrapes LinkedIn via Playwright headless.
    ADVERTENCIA: Viola los ToS de LinkedIn. Usar con cuenta secundaria.
    Returns [] si no hay credenciales o si LinkedIn bloquea el acceso.
    """
    if not config.LINKEDIN_EMAIL or not config.LINKEDIN_PASSWORD:
        logger.warning("LinkedIn: credenciales no configuradas — fuente omitida")
        return []

    try:
        from playwright.sync_api import sync_playwright
        return _scrape_with_playwright()
    except ImportError:
        logger.error("LinkedIn: playwright no instalado — ejecuta 'playwright install chromium'")
        return []
    except Exception as e:
        logger.error(f"LinkedIn scraper failed: {e}")
        return []


def _scrape_with_playwright() -> List[dict]:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    jobs = []
    seen_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        # Login
        try:
            page.goto("https://www.linkedin.com/login", timeout=15000)
            page.fill("#username", config.LINKEDIN_EMAIL)
            page.fill("#password", config.LINKEDIN_PASSWORD)
            page.click("button[type=submit]")
            page.wait_for_url("**/feed/**", timeout=15000)
        except PlaywrightTimeout:
            logger.warning("LinkedIn: login timeout o CAPTCHA detectado — fuente omitida")
            browser.close()
            return []

        # Verificar si llegamos al feed
        if "checkpoint" in page.url or "challenge" in page.url:
            logger.warning("LinkedIn: desafío de seguridad detectado — fuente omitida")
            browser.close()
            return []

        # Búsquedas
        for query in SEARCH_QUERIES:
            try:
                search_url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}&f_WT=2"
                page.goto(search_url, timeout=15000)
                page.wait_for_selector(".jobs-search__results-list, .scaffold-layout__list", timeout=10000)

                cards = page.query_selector_all(".job-card-container, .base-card")
                for card in cards[:25]:
                    try:
                        job = _parse_linkedin_card(card)
                        if job and job["url"] not in seen_urls:
                            seen_urls.add(job["url"])
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"LinkedIn card parse error: {e}")

            except PlaywrightTimeout:
                logger.warning(f"LinkedIn: timeout en query '{query}'")
            except Exception as e:
                logger.error(f"LinkedIn search failed for '{query}': {e}")

        browser.close()

    logger.info(f"linkedin: {len(jobs)} jobs fetched")
    return jobs


def _parse_linkedin_card(card) -> Optional[dict]:
    title_el = card.query_selector(".job-card-list__title, .base-search-card__title")
    company_el = card.query_selector(".job-card-container__company-name, .base-search-card__subtitle")
    location_el = card.query_selector(".job-card-container__metadata-item, .job-search-card__location")
    link_el = card.query_selector("a[href*='/jobs/view/']")

    if not link_el:
        return None

    url = link_el.get_attribute("href") or ""
    if "?" in url:
        url = url.split("?")[0]

    return {
        "title": title_el.inner_text().strip() if title_el else "",
        "company": company_el.inner_text().strip() if company_el else "",
        "location": location_el.inner_text().strip() if location_el else "",
        "url": url,
        "description": card.inner_text().strip()[:500],
        "source": "linkedin",
        "date_posted": "",
        "salary_min": None,
        "salary_max": None,
    }
