import asyncio
import logging
from datetime import datetime
from pathlib import Path

from telegram import Bot
import config

logger = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096
SHARED_REPORTS_PATH = Path(__file__).parent.parent / "shared_reports"


def split_message(text: str) -> list:
    """Divide texto en chunks de <=4096 chars, preferiblemente en newlines."""
    if len(text) <= TELEGRAM_LIMIT:
        return [text]

    chunks = []
    while text:
        if len(text) <= TELEGRAM_LIMIT:
            chunks.append(text)
            break

        chunk = text[:TELEGRAM_LIMIT]
        # Intentar dividir en el último newline dentro del límite
        last_newline = chunk.rfind("\n")
        if last_newline > TELEGRAM_LIMIT // 2:
            chunk = text[:last_newline]

        chunks.append(chunk)
        text = text[len(chunk):]

    return chunks


def _rotate_history(pattern: str, keep_days: int = 7) -> None:
    """Borra archivos de historial con más de keep_days días."""
    import time
    cutoff = time.time() - (keep_days * 86400)
    for f in SHARED_REPORTS_PATH.glob(pattern):
        if f.stat().st_mtime < cutoff:
            f.unlink()


def save_fallback(report: str) -> None:
    """Guarda reporte en shared_reports/scout_latest.md (siempre, no solo como fallback)."""
    SHARED_REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    path = SHARED_REPORTS_PATH / "scout_latest.md"
    path.write_text(report)
    dated = path.parent / f"scout_{datetime.now().strftime('%Y-%m-%d')}.md"
    dated.write_text(report)
    _rotate_history("scout_2*.md")
    logger.info(f"Report saved to {path}")


def save_deep_brief(brief: str) -> None:
    """Guarda el deep brief en shared_reports/scout_deep_brief_latest.md."""
    SHARED_REPORTS_PATH.mkdir(parents=True, exist_ok=True)
    path = SHARED_REPORTS_PATH / "scout_deep_brief_latest.md"
    path.write_text(brief)
    dated = path.parent / f"scout_deep_{datetime.now().strftime('%Y-%m-%d')}.md"
    dated.write_text(brief)
    _rotate_history("scout_deep_2*.md")
    logger.info(f"Deep brief saved to {path}")


def _msg_kwargs(thread_id: int | None) -> dict:
    """Retorna chat_id y, si aplica, message_thread_id para bot.send_message()."""
    if thread_id is not None:
        return {"chat_id": config.TELEGRAM_GROUP_ID, "message_thread_id": thread_id}
    return {"chat_id": config.TELEGRAM_CHAT_ID}


async def send_report(report: str, thread_id: int | None = None) -> None:
    """Envía reporte por Telegram. Si falla, guarda en scout_latest.md y re-lanza."""
    try:
        bot = Bot(token=config.TELEGRAM_TOKEN)
        chunks = split_message(report)
        dest = _msg_kwargs(thread_id)

        for i, chunk in enumerate(chunks, 1):
            await bot.send_message(**dest, text=chunk, disable_web_page_preview=True)
            logger.info(f"Telegram: mensaje {i}/{len(chunks)} enviado")
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        save_fallback(report)
        raise  # Re-raise so scout_runner can log the correct status


async def send_alert(reason: str, thread_id: int | None = None) -> None:
    """Envía alerta corta de fallo a Telegram. Si Telegram también falla, loguea y no lanza."""
    msg = f"⚠️ Scout falló hoy: {reason}"
    logger.error(f"SCOUT FAILURE: {msg}")
    try:
        bot = Bot(token=config.TELEGRAM_TOKEN)
        dest = _msg_kwargs(thread_id)
        await bot.send_message(**dest, text=msg, disable_web_page_preview=True)
        logger.info("Alert sent via Telegram")
    except Exception as e:
        logger.error(f"Could not send alert — Telegram also down: {e}")


async def send_deep_brief(brief: str, thread_id: int | None = None) -> None:
    """Envía el deep research brief por Telegram y guarda en archivo."""
    save_deep_brief(brief)
    try:
        bot = Bot(token=config.TELEGRAM_TOKEN)
        chunks = split_message(brief)
        dest = _msg_kwargs(thread_id)
        for i, chunk in enumerate(chunks, 1):
            await bot.send_message(**dest, text=chunk, disable_web_page_preview=True)
            logger.info(f"Telegram deep brief: mensaje {i}/{len(chunks)} enviado")
    except Exception as e:
        logger.error(f"send_deep_brief failed: {e}")
        # Silent failure — never raise, never break the main pipeline
