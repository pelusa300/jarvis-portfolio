"""
Upgrade 2 — Fit Scorer
Aplica scoring de 6 criterios sobre cada job listing.
Configurable via fit_config.json sin tocar código.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "fit_config.json"


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text())
    except Exception as e:
        logger.error(f"fit_config.json error: {e}")
        return {"scoring": {}, "min_score_to_include": 5, "keywords": {}}


def score_fit(job: dict) -> dict:
    """Aplica scoring de 6 criterios. Retorna job enriquecido con fit_score, fit_reasons, why_fits."""
    cfg = _load_config()
    weights = cfg.get("scoring", {})
    keywords = cfg.get("keywords", {})

    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    location = (job.get("location") or "").lower()

    fit_score = 0
    fit_reasons = []

    # 1. Posición remota
    if any(w in location for w in ["remote", "remoto", "anywhere"]) or "remote" in text:
        pts = weights.get("remote_position", 2)
        fit_score += pts
        fit_reasons.append(f"Remote +{pts}")

    # 2. Crypto/blockchain/DeFi
    if any(kw in text for kw in keywords.get("crypto", [])):
        pts = weights.get("mentions_crypto_blockchain_defi", 2)
        fit_score += pts
        fit_reasons.append(f"Crypto/blockchain +{pts}")

    # 3. AML/KYC/Compliance
    if any(kw in text for kw in keywords.get("compliance", [])):
        pts = weights.get("mentions_aml_kyc_compliance", 2)
        fit_score += pts
        fit_reasons.append(f"AML/KYC/Compliance +{pts}")

    # 4. CAMS certification
    if any(kw in text for kw in keywords.get("cams", [])):
        pts = weights.get("mentions_cams", 3)
        fit_score += pts
        fit_reasons.append(f"CAMS certification +{pts}")

    # 5. Salario > $60k
    sal_min = job.get("salary_min") or 0
    sal_max = job.get("salary_max") or 0
    salary = sal_max or sal_min
    if salary and salary > 60000:
        pts = weights.get("salary_above_60k", 1)
        fit_score += pts
        fit_reasons.append(f"Salary >${salary // 1000}k +{pts}")

    # 6. Multi-source (campo set externamente si existe)
    if job.get("multi_source"):
        pts = weights.get("multi_source", 1)
        fit_score += pts
        fit_reasons.append(f"Multi-source +{pts}")

    why_fits = _generate_why_fits(job, fit_reasons)

    logger.info(
        "FIT_SCORE %s @ %s → %d pts (%s)",
        job.get("title", "?"), job.get("company", "?"),
        fit_score, ", ".join(fit_reasons)
    )

    return {
        **job,
        "fit_score": fit_score,
        "fit_reasons": fit_reasons,
        "why_fits": why_fits,
    }


def _generate_why_fits(job: dict, reasons: list) -> str:
    if not reasons:
        return ""
    reason_text = ", ".join(r.split(" +")[0] for r in reasons)
    title = job.get("title", "Este rol")
    company = job.get("company", "")
    company_str = f" en {company}" if company else ""
    return f"{title}{company_str}: {reason_text}."
