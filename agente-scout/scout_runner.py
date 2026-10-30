"""
Scout Runner — orquestador del pipeline completo.
Uso: from scout_runner import run; run("daily") o run("weekly")
"""
import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

LOGS_DIR = Path(__file__).parent / "logs"

import config
from searcher import search_all
from deduplicator import filter_seen
from analyzer import generate_report, load_profile
from notifier import send_report, send_deep_brief, send_alert
from deep_researcher import analyze_findings


def _setup_logging() -> None:
    """Configura logging solo si el root logger no tiene handlers aún."""
    if logging.getLogger().handlers:
        return
    LOGS_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOGS_DIR / "scout.log"),
        ],
    )


def run(mode: str = "daily") -> None:
    """
    Ejecuta el pipeline completo.
    mode: 'daily' o 'weekly'
    """
    _setup_logging()
    logger.info(f"=== Scout Runner starting — mode: {mode} ===")

    # 1. Buscar hallazgos
    try:
        findings = search_all(config.BRAVE_SEARCH_API_KEY)
        logger.info(f"Search: {len(findings)} results")
    except Exception as e:
        logger.error(f"Search failed: {e}")
        findings = []
        asyncio.run(send_alert(f"búsqueda fallida — {type(e).__name__}", thread_id=config.TOPICS["herramientas"]))

    # 1b. Filtrar URLs ya reportadas en los últimos 14 días
    findings = filter_seen(findings)

    if not findings:
        logger.warning("No findings — skipping report generation")
        return

    # 2. Generar reporte con Claude
    try:
        profile = load_profile()
        report = generate_report(findings, mode, profile)
        logger.info(f"Report generated: {len(report)} chars")
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        asyncio.run(send_alert(f"Claude API falló — {type(e).__name__}", thread_id=config.TOPICS["herramientas"]))
        return

    # 3. Deep research (si hay hallazgos relevantes)
    deep_brief = None
    try:
        deep_brief = analyze_findings(
            findings,
            config.ANTHROPIC_API_KEY,
            config.BRAVE_SEARCH_API_KEY,
            profile,
        )
        if deep_brief:
            logger.info(f"Deep research: brief generated ({len(deep_brief)} chars)")
        else:
            logger.info("Deep research: no relevant findings — skipping")
    except Exception as e:
        logger.error(f"Deep research failed (non-fatal): {e}")

    # 4. Guardar reporte en shared_reports (siempre)
    from notifier import save_fallback
    save_fallback(report)

    # 5. Enviar reporte por Telegram → topic Herramientas Jarvis
    try:
        asyncio.run(send_report(report, thread_id=config.TOPICS["herramientas"]))
        logger.info("Telegram: report sent successfully")
    except Exception as e:
        logger.error(f"Telegram send failed — report saved to shared_reports/scout_latest.md")
        try:
            asyncio.run(send_alert(
                "Telegram caído — reporte guardado en scout_latest.md",
                thread_id=config.TOPICS["herramientas"],
            ))
        except Exception:
            logger.error("ALERT: no se pudo enviar alerta — Telegram completamente caído")

    # 6. Enviar deep brief si existe → topic Deep Research
    if deep_brief:
        try:
            asyncio.run(send_deep_brief(deep_brief, thread_id=config.TOPICS["deep_research"]))
            logger.info("Telegram: deep brief sent successfully")
        except Exception as e:
            logger.error(f"Deep brief send failed (non-fatal): {e}")

    logger.info("=== Scout Runner completed ===")
