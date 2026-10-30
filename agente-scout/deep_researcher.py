"""
Deep Research module for agente-scout.
Detects high-value findings and generates a deeper research brief via Claude.
"""
import json
import logging
from pathlib import Path
from typing import Optional

import anthropic
import config
import requests

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"
PROFILE_PATH = Path(__file__).parent.parent / "mi_perfil.json"
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

HIGH_KEYWORDS = [
    "XRP", "Ripple", "Flare", "FLR", "FATF", "FinCEN", "OFAC",
    "CAMS", "ACAMS", "sanctions",
]

MEDIUM_KEYWORDS = [
    "DeFi compliance", "crypto regulation", "AML", "crypto exchange",
    "Claude Code", "MCP", "Anthropic",
]

GITHUB_TECHNICAL_KEYWORDS = ["Claude Code", "MCP", "Anthropic"]


def detect_tier(findings: list) -> tuple:
    """
    Scan findings for keywords. Returns (tier, keyword, topic) or (None, None, None).
    HIGH beats MEDIUM if both are present.
    """
    high_match = None
    medium_match = None
    high_topic = None
    medium_topic = None

    for finding in findings:
        text = f"{finding.get('title', '')} {finding.get('snippet', '')}".lower()

        for kw in HIGH_KEYWORDS:
            if kw.lower() in text and high_match is None:
                high_match = kw
                high_topic = finding.get("title", kw)

        for kw in MEDIUM_KEYWORDS:
            if kw.lower() in text and medium_match is None:
                medium_match = kw
                medium_topic = finding.get("title", kw)

    if high_match:
        return "HIGH", high_match, high_topic
    if medium_match:
        return "MEDIUM", medium_match, medium_topic
    return None, None, None


def _search_query(query: str, api_key: str) -> list:
    """Run a single Brave search. Returns list of results (may be empty)."""
    try:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        }
        params = {"q": query, "count": 5, "freshness": "pw"}
        resp = requests.get(BRAVE_SEARCH_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        results = resp.json().get("web", {}).get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("description", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.warning(f"deep_researcher search failed for '{query}': {e}")
        return []


def _fetch_github(keyword: str) -> list:
    """Check GitHub for repos related to the keyword."""
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": keyword, "sort": "updated", "per_page": 3},
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=30,
        )
        if resp.status_code != 200:
            return []
        items = resp.json().get("items", [])
        return [
            {
                "title": f"GitHub: {r.get('full_name', '')}",
                "url": r.get("html_url", ""),
                "snippet": r.get("description", ""),
            }
            for r in items
        ]
    except Exception as e:
        logger.warning(f"GitHub fetch failed for '{keyword}': {e}")
        return []


def _run_extra_searches(keyword: str, topic: str, brave_api_key: str) -> list:
    """Run 3 targeted searches. Also checks GitHub if topic is technical."""
    queries = [
        f"{keyword} crypto compliance 2026",
        f"{keyword} regulation update",
        f"{topic[:60]}",
    ]
    results = []
    for q in queries:
        results.extend(_search_query(q, brave_api_key))

    if any(tk.lower() in keyword.lower() for tk in GITHUB_TECHNICAL_KEYWORDS):
        results.extend(_fetch_github(keyword))

    return results


def _build_brief(
    tier: str,
    keyword: str,
    topic: str,
    original_finding: dict,
    extra_findings: list,
    anthropic_api_key: str,
    profile: dict,
) -> str:
    """Call Claude to generate the deep research brief."""
    prompt_file = PROMPTS_DIR / "deep_research_prompt.md"
    try:
        prompt_template = prompt_file.read_text()
    except Exception as e:
        logger.error(f"Could not read deep_research_prompt.md: {e}")
        return ""

    prompt = prompt_template.format(
        profile=json.dumps(profile, indent=2, ensure_ascii=False),
        tier=tier,
        topic=topic,
        keyword=keyword,
        original_finding=json.dumps(original_finding, indent=2, ensure_ascii=False),
        extra_findings=json.dumps(extra_findings[:10], indent=2, ensure_ascii=False),
    )

    try:
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        message = client.messages.create(
            model=config.MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            timeout=60,
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API failed in deep_researcher: {e}")
        return ""


def analyze_findings(
    findings: list,
    anthropic_api_key: str,
    brave_api_key: str,
    profile: dict,
) -> Optional[str]:
    """
    Main entry point. Returns a formatted brief string or None.
    Never raises — all errors are caught and logged.
    """
    try:
        tier, keyword, topic = detect_tier(findings)
        if tier is None:
            logger.info("deep_researcher: no relevant keywords found — skipping")
            return None

        logger.info(f"deep_researcher: {tier} match on '{keyword}' — researching deeper")

        original_finding = next(
            (f for f in findings if keyword.lower() in
             f"{f.get('title','')} {f.get('snippet','')}".lower()),
            findings[0],
        )

        extra_findings = _run_extra_searches(keyword, topic, brave_api_key)
        logger.info(f"deep_researcher: {len(extra_findings)} extra results gathered")

        brief = _build_brief(
            tier=tier,
            keyword=keyword,
            topic=topic,
            original_finding=original_finding,
            extra_findings=extra_findings,
            anthropic_api_key=anthropic_api_key,
            profile=profile,
        )

        if not brief:
            logger.warning("deep_researcher: empty brief returned — skipping")
            return None

        logger.info(f"deep_researcher: brief generated ({len(brief)} chars)")
        return brief

    except Exception as e:
        logger.error(f"deep_researcher.analyze_findings failed: {e}")
        return None
