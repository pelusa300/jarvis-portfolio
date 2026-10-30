import logging
import sys
from pathlib import Path
from typing import List, Optional

import config
import prompts

# Agregar la raíz del repo al sys.path para importar profile_loader
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from profile_loader import load_profile

logger = logging.getLogger(__name__)

SOURCE_PRIORITY = {src: i for i, src in enumerate(config.SOURCE_PRIORITY)}


def _find_skills_in_text(text: str, skills: list) -> list:
    """Devuelve las skills que aparecen en el texto (case-insensitive)."""
    text_lower = text.lower()
    return [s for s in skills if s.lower() in text_lower]


def score_job(job: dict, profile: Optional[dict] = None) -> dict:
    """
    Nivel 1: analiza keywords del job contra el perfil the user.
    - skills_matched: skills confirmadas (perfil o config.SKILLS_HAVE) mencionadas en la oferta
    - en_progreso: certificaciones en progreso (perfil) mencionadas en la oferta
    - gaps: skills por aprender (config.SKILLS_LEARNING) mencionadas en la oferta, excl. en_progreso
    - matched_count / total_count: para mostrar "X/Y requisitos" en Telegram
    - score: skills_matched / total detectadas
    """
    if profile is None:
        profile = load_profile()

    skills_have = profile.get("skills_confirmados") or config.SKILLS_HAVE
    certs_en_progreso = (profile.get("certificaciones") or {}).get("en_progreso") or []

    text = (job.get("description") or "")

    skills_matched = _find_skills_in_text(text, skills_have)
    skills_learning_in_job = _find_skills_in_text(text, config.SKILLS_LEARNING)
    en_progreso = _find_skills_in_text(text, certs_en_progreso)

    # Excluir de gaps cualquier cert que ya esté en en_progreso
    en_progreso_lower = {s.lower() for s in en_progreso}
    gaps = [s for s in skills_learning_in_job if s.lower() not in en_progreso_lower]

    all_detected = skills_matched + gaps + en_progreso
    matched_count = len(skills_matched)
    total_count = len(all_detected)

    if not all_detected or not skills_matched:
        score = 0.0
    else:
        score = matched_count / total_count

    result = {
        **job,
        "score": score,
        "skills_matched": skills_matched,
        "gaps": gaps,
        "en_progreso": en_progreso,
        "matched_count": matched_count,
        "total_count": total_count,
        "claude_analysis": None,
    }

    # Upgrade 2: fit scoring combinado
    try:
        from analysis.fit_scorer import score_fit
        fit_data = score_fit(result)
        result["fit_score"] = fit_data.get("fit_score", 0)
        result["fit_reasons"] = fit_data.get("fit_reasons", [])
        result["why_fits"] = fit_data.get("why_fits", "")
    except Exception as _e:
        logger.warning("fit_scorer failed (non-fatal): %s", _e)
        result["fit_score"] = 0
        result["fit_reasons"] = []
        result["why_fits"] = ""

    return result


def select_top_jobs(jobs: List[dict], n: int = 5) -> List[dict]:
    """
    Selecciona los top N jobs por score.
    Tiebreaker: score DESC → strict > broad → date_posted DESC → source priority ASC.
    """
    def sort_key(j):
        is_strict = 1 if j.get("_is_strict") else 0
        # Convert date to int YYYYMMDD for clean negation (descending sort)
        date_str = (j.get("date_posted") or "0000-00-00").replace("-", "")
        date_int = int(date_str) if date_str.isdigit() else 0
        source_rank = SOURCE_PRIORITY.get(j.get("source", ""), 99)
        return (-j.get("score", 0), -is_strict, -date_int, source_rank)

    return sorted(jobs, key=sort_key)[:n]


def analyze_jobs(strict: List[dict], broad: List[dict]) -> dict:
    """
    Punto de entrada principal. Scores todos los jobs y llama a Claude para el top 5.
    Devuelve {"strict": [...], "broad": [...], "top3": [...]}.
    top3: hasta 3 jobs con score > 0, Claude-enriched, ordenados por score desc.
    """
    # Cargar perfil una vez para todo el batch
    profile = load_profile()

    # Marcar origen para tiebreaking
    strict_scored = [score_job({**j, "_is_strict": True}, profile) for j in strict]
    broad_scored = [score_job({**j, "_is_strict": False}, profile) for j in broad]

    # Deduplicar por URL (un job que aparece en ambas listas cuenta como strict)
    strict_urls = {j["url"] for j in strict_scored}
    all_jobs = strict_scored + [j for j in broad_scored if j["url"] not in strict_urls]
    top5 = select_top_jobs(all_jobs, n=5)

    # Nivel 2: Claude analysis para top 5
    for job in top5:
        job["claude_analysis"] = _get_claude_analysis(job)

    # Top 3 para resumen: solo jobs con score > 0, ya Claude-enriched
    top3 = [j for j in top5 if j.get("score", 0) > 0][:3]

    # Reconstruir listas con análisis añadido
    def enrich(job_list):
        enriched = []
        for j in job_list:
            match = next((t for t in top5 if t["url"] == j["url"]), None)
            enriched.append(match if match else j)
        return enriched

    return {"strict": enrich(strict_scored), "broad": enrich(broad_scored), "top3": top3}


def _get_claude_analysis(job: dict) -> Optional[str]:
    """Nivel 2: llama a Claude para análisis de brechas. Devuelve None si falla."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        prompt = prompts.GAP_ANALYSIS_PROMPT.format(
            job_description=f"{job.get('title', '')} at {job.get('company', '')}\n\n{job.get('description', '')}"
        )
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.warning(f"Claude analysis failed for {job.get('url')}: {e}")
        return None
