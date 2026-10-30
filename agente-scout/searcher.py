import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

QUERIES = [
    # Grupo 1: Claude Code + Anthropic — noticias del día
    {"q": "anthropic announcement site:anthropic.com", "freshness": "pd"},
    {"q": "claude code release site:github.com/anthropics", "freshness": "pd"},
    {"q": "claude code MCP", "freshness": "pd"},
    {"q": "claude code site:reddit.com/r/ClaudeCode", "freshness": "pd"},
    # Grupo 2: MCPs de la comunidad — última semana
    {"q": "model context protocol new MCP server site:github.com", "freshness": "pw"},
    {"q": "awesome-mcp site:github.com", "freshness": "pw"},
    # Grupo 3: Patrones de orquestación multi-agente — último mes
    {"q": "multi-agent LLM orchestration patterns", "freshness": "pm"},
    {"q": "agentic workflow tool use memory LLM", "freshness": "pm"},
    # Grupo 4: Frameworks open-source para construir agentes — último mes
    {"q": "LLM agent framework open source release", "freshness": "pm"},
    {"q": "autonomous AI agent python framework site:github.com", "freshness": "pm"},
]

GITHUB_REPOS = [
    "anthropics/claude-code",
    "anthropics/anthropic-sdk-python",
    "hesreallyhim/awesome-claude-code",
]


def search_query(query: str, api_key: str, freshness: str = "pd") -> Optional[list]:
    """
    Llama Brave Search API para una query.
    Retorna lista de resultados (puede ser vacía), o None si hay error de API.
    """
    try:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        }
        params = {"q": query, "count": 5, "freshness": freshness}
        resp = requests.get(BRAVE_SEARCH_URL, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("web", {}).get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("description", ""),
                "source": query,
            }
            for r in results
        ]
    except Exception as e:
        logger.error(f"search_query failed for '{query}': {e}")
        return None  # None means API error, [] means valid empty response


def fetch_github_releases_fallback() -> list[dict]:
    """Fallback: consulta GitHub API sin autenticación para releases recientes."""
    results = []
    for repo in GITHUB_REPOS:
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo}/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                results.append({
                    "title": f"{repo}: {data.get('name') or data.get('tag_name', 'Release')}",
                    "url": data.get("html_url", ""),
                    "snippet": (data.get("body") or "")[:200],
                    "source": "github_fallback",
                })
        except Exception as e:
            logger.warning(f"GitHub fallback failed for {repo}: {e}")
    return results


def search_all(api_key: str) -> list[dict]:
    """Ejecuta todas las queries. Fallback a GitHub si Brave falla completamente."""
    all_results = []
    brave_responded = False  # True if any Brave call succeeded (even with 0 results)

    for item in QUERIES:
        results = search_query(item["q"], api_key, item["freshness"])
        if results is not None:  # None = error, [] = valid empty
            brave_responded = True
            all_results.extend(results)

    if not brave_responded:
        logger.warning("Brave Search failed for all queries — using GitHub fallback")
        all_results = fetch_github_releases_fallback()

    # Deduplicar por URL
    seen_urls = set()
    unique = []
    for r in all_results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            unique.append(r)

    logger.info(f"search_all: {len(unique)} unique results")
    return unique
