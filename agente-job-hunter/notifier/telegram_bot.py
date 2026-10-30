import logging
import os
from datetime import date, timedelta
from typing import List
from filters.job_filter import categorize_job, CATEGORY_ORDER

logger = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096
DIVIDER = "━" * 22
JOB_HUNTER_THREAD_ID = int(os.environ.get("TELEGRAM_THREAD_JOB_HUNTER", "0"))


def format_job_entry(job: dict, index: int) -> str:
    """Formatea una oferta como string para Telegram."""
    location = job.get("location", "")
    hybrid_warning = " ⚠️" if any(w in location.lower() for w in ["hybrid", "on-site", "onsite", "presencial"]) else ""

    skills_str = ", ".join(job.get("skills_matched") or []) or "—"
    gaps_str = ", ".join(job.get("gaps") or []) or "Ninguna detectada"

    returning_flag = "[RETURNING COMPANY] " if job.get("returning_company") else ""
    lines = [
        f"{index}. {returning_flag}{job.get('title', '?')} — {job.get('company', '?')}",
        f"   📍 {location}{hybrid_warning} | 🔗 {job.get('url', '')}",
    ]

    # Salary line — only if at least one value is present and non-zero
    sal_min = job.get("salary_min") or 0
    sal_max = job.get("salary_max") or 0
    if sal_min and sal_max:
        lines.append(f"   💰 ${sal_min:,} – ${sal_max:,} / año")
    elif sal_min:
        lines.append(f"   💰 desde ${sal_min:,} / año")
    elif sal_max:
        lines.append(f"   💰 hasta ${sal_max:,} / año")

    lines.append(f"   ✅ Cumples: {skills_str}")
    lines.append(f"   ❌ Te falta: {gaps_str}")

    en_progreso = job.get("en_progreso") or []
    if en_progreso:
        lines.append(f"   🔄 En progreso: {', '.join(en_progreso)}")

    matched_count = job.get("matched_count")
    total_count = job.get("total_count")
    if total_count:
        lines.append(f"   📊 {matched_count}/{total_count} requisitos")

    if job.get("claude_analysis"):
        analysis = job["claude_analysis"]
        lines.append(f"   🤖 {analysis}")

    if job.get("why_fits"):
        lines.append(f"   💡 {job['why_fits']}")

    if job.get("fit_score"):
        lines.append(f"   🎯 Fit: {job['fit_score']}/11 pts")

    return "\n".join(lines)


def _truncate_entry_if_needed(entry: str, max_len: int = TELEGRAM_LIMIT) -> str:
    """Si una entrada individual excede el límite, trunca el análisis Claude."""
    if len(entry) <= max_len:
        return entry
    cut_marker = "   🤖 "
    idx = entry.find(cut_marker)
    if idx != -1:
        truncated = entry[:idx] + cut_marker + "[Análisis omitido por longitud]"
        return truncated[:max_len]
    return entry[:max_len]


# Category icons — matching CATEGORY_ORDER from filters.job_filter
_CATEGORY_ICONS = {
    "AML": "🔵",
    "Financial Crimes": "🟠",
    "KYC": "🟢",
    "Compliance": "🟡",
    "Otras": "⚪",
}


def split_into_messages(
    strict: List[dict],
    broad: List[dict],
    top3: List[dict],
    date_str: str,
) -> List[str]:
    """
    Construye mensajes de Telegram respetando el límite de 4096 chars.
    STRICT: todos juntos. BROAD: agrupados por categoría.
    """
    today = date_str
    next_monday = (date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)).strftime("%d %b %Y")

    header = f"🔍 Job Hunt Report — {today}\n\n"

    # Build summary block
    summary_lines = [f"\n{DIVIDER}", f"📊 Total nuevas: {len(strict) + len(broad)} | 🗓️ Próximo: {next_monday}"]
    if top3:
        summary_lines.append("\n🏆 TOP 3 PARA TU PERFIL")
        for i, job in enumerate(top3, 1):
            pct = int(job.get("score", 0) * 100)
            summary_lines.append(f"{i}. {job.get('title', '?')} — {job.get('company', '?')} ({pct}%)")
    footer = "\n".join(summary_lines)

    messages = []
    current = header

    def flush_section(title: str, jobs: List[dict]):
        nonlocal current
        section_header = f"{DIVIDER}\n{title} ({len(jobs)} ofertas)\n{DIVIDER}\n\n"

        if len(current) + len(section_header) > TELEGRAM_LIMIT:
            messages.append(current.rstrip())
            current = section_header
        else:
            current += section_header

        for i, job in enumerate(jobs, 1):
            entry = _truncate_entry_if_needed(format_job_entry(job, i))
            entry_block = entry + "\n\n"

            if len(current) + len(entry_block) > TELEGRAM_LIMIT:
                messages.append(current.rstrip())
                current = f"(cont.) {title}\n\n" + entry_block
            else:
                current += entry_block

    # STRICT section — all jobs together
    if strict:
        flush_section("🎯 LISTA ESTRICTA", strict)

    # BROAD section — grouped by category
    if broad:
        broad_header = f"{DIVIDER}\n📋 LISTA AMPLIA ({len(broad)} ofertas)\n{DIVIDER}\n\n"
        if len(current) + len(broad_header) > TELEGRAM_LIMIT:
            messages.append(current.rstrip())
            current = broad_header
        else:
            current += broad_header

        # Group by category in display order
        categorized = {cat: [] for cat in CATEGORY_ORDER}
        for job in broad:
            cat = categorize_job(job)
            categorized[cat].append(job)

        for cat in CATEGORY_ORDER:
            jobs_in_cat = categorized[cat]
            if not jobs_in_cat:
                continue
            icon = _CATEGORY_ICONS.get(cat, "⚪")
            oferta_word = "oferta" if len(jobs_in_cat) == 1 else "ofertas"
            cat_header = f"{icon} {cat} ({len(jobs_in_cat)} {oferta_word})\n"
            if len(current) + len(cat_header) > TELEGRAM_LIMIT:
                messages.append(current.rstrip())
                current = cat_header
            else:
                current += cat_header

            for i, job in enumerate(jobs_in_cat, 1):
                entry = _truncate_entry_if_needed(format_job_entry(job, i))
                entry_block = entry + "\n\n"
                if len(current) + len(entry_block) > TELEGRAM_LIMIT:
                    messages.append(current.rstrip())
                    current = f"(cont.) {cat}\n\n" + entry_block
                else:
                    current += entry_block

    # Append footer
    if len(current) + len(footer) > TELEGRAM_LIMIT:
        messages.append(current.rstrip())
        messages.append(footer.strip())
    else:
        current += footer
        messages.append(current.rstrip())

    return messages


def format_report(strict: List[dict], broad: List[dict], top3: List[dict]) -> List[str]:
    """Punto de entrada: genera lista de mensajes de Telegram."""
    date_str = date.today().strftime("%d %b %Y")
    return split_into_messages(strict, broad, top3, date_str)


async def send_report(strict: List[dict], broad: List[dict], top3: List[dict]) -> None:
    """Envía el reporte a Telegram."""
    import config
    from telegram import Bot

    bot = Bot(token=config.TELEGRAM_TOKEN)
    messages = format_report(strict, broad, top3)
    group_id = os.environ.get("TELEGRAM_GROUP_ID")

    sent = 0
    for i, msg in enumerate(messages, 1):
        if group_id:
            try:
                await bot.send_message(
                    chat_id=group_id,
                    text=msg,
                    message_thread_id=JOB_HUNTER_THREAD_ID,
                    disable_web_page_preview=True,
                )
                sent += 1
                continue
            except Exception as e:
                logger.error(
                    f"Envío al grupo falló (chunk {i}/{len(messages)}), "
                    f"usando DM como respaldo: {e}"
                )
                group_id = None
        await bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text=msg,
            disable_web_page_preview=True,
        )
        sent += 1
    logger.info(f"Telegram: {sent}/{len(messages)} mensaje(s) enviado(s)")
    _write_json_report(strict, broad)


def _write_json_report(strict: list, broad: list) -> None:
    import json
    from datetime import datetime, timezone

    def _serialize(jobs: list) -> list:
        out = []
        for j in jobs:
            out.append({
                "title":      j.get("title", ""),
                "company":    j.get("company", ""),
                "url":        j.get("url", ""),
                "location":   j.get("location", ""),
                "fit_score":  j.get("fit_score", 0),
                "salary_min": j.get("salary_min"),
                "salary_max": j.get("salary_max"),
                "source":     j.get("source", ""),
                "why_fits":   j.get("why_fits", ""),
            })
        return out

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "strict":  _serialize(strict),
        "broad":   _serialize(broad),
        "total":   len(strict) + len(broad),
    }

    path = os.path.normpath(os.path.join(
        os.path.dirname(__file__), "..", "..",
        "shared_reports", "job_market_latest.json"
    ))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
