#!/usr/bin/env python3
"""
Resumen semanal de aplicaciones. Ejecutado los viernes vía LaunchAgent.
1. Auto-marca como 'sin respuesta' aplicaciones con ≥7 días desde date_applied.
2. Escribe shared_reports/applications_latest.md.
3. Envía resumen a Telegram.
"""
import asyncio
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

_SHARED_REPORTS = Path(__file__).parent.parent.parent / "shared_reports"
_REPORT_PATH = _SHARED_REPORTS / "applications_latest.md"
WEEKLY_GOAL = 5
JOB_HUNTER_THREAD_ID = 19


def check_follow_ups(db_path=None) -> List[dict]:
    from tracker.db import get_stale_applications, update_application
    stale = get_stale_applications(days=7, db_path=db_path)
    for app in stale:
        update_application(app["id"], status="sin respuesta", db_path=db_path)
        logger.info("Auto-marcada sin_respuesta: #%d %s", app["id"], app["company"])
    return stale


def write_applications_report(db_path=None) -> None:
    from tracker.db import list_applications
    apps = list_applications(db_path=db_path)
    today = date.today().isoformat()

    by_status: dict = {}
    for a in apps:
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1

    lines = [
        f"# Applications Tracker — {today}",
        "",
        "<!-- _metadata",
        f"generated: {today}",
        "owner: agente-job-hunter",
        "status: OK",
        "-->",
        "",
        "## Resumen",
        f"- Total aplicaciones: {len(apps)}",
        f"- Por aplicar: {by_status.get('por aplicar', 0)}",
        f"- Aplicadas: {by_status.get('aplicada', 0)}",
        f"- En entrevista: {by_status.get('entrevista', 0)}",
        f"- Sin respuesta: {by_status.get('sin respuesta', 0)}",
        f"- Rechazadas: {by_status.get('rechazada', 0)}",
        f"- Cerradas: {by_status.get('cerrada', 0)}",
        "",
        "## Aplicaciones",
        "",
        "| ID | Empresa | Puesto | Estado | Aplicada | Seguimiento |",
        "|----|---------|--------|--------|----------|-------------|",
    ]
    for a in apps:
        lines.append(
            f"| {a['id']} | {a['company']} | {a['title']} | "
            f"{a['status']} | {a.get('date_applied') or '—'} | "
            f"{a.get('follow_up_date') or '—'} |"
        )

    _SHARED_REPORTS.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    logger.info("applications_latest.md escrito: %d entradas", len(apps))


def _week_start() -> str:
    today = date.today()
    return (today - timedelta(days=today.weekday())).isoformat()


def build_telegram_summary(db_path=None) -> str:
    from tracker.db import list_applications
    apps = list_applications(db_path=db_path)
    today = date.today().isoformat()
    week_start = _week_start()

    applied_week = [
        a for a in apps
        if a["status"] in ("aplicada", "entrevista", "oferta")
        and (a.get("date_applied") or "9999") >= week_start
    ]
    pending = [a for a in apps if a["status"] == "por aplicar"]
    sin_resp = [a for a in apps if a["status"] == "sin respuesta"]

    lines = [
        f"📋 Resumen semanal — {today}",
        "",
        f"🎯 Meta: {len(applied_week)}/{WEEKLY_GOAL} aplicaciones esta semana",
        "",
    ]

    if applied_week:
        lines.append("✅ Aplicadas esta semana:")
        for a in applied_week:
            lines.append(f"  • {a['title']} — {a['company']}")
        lines.append("")

    if pending:
        lines.append(f"⏳ Pendientes ({len(pending)}):")
        for a in pending[:5]:
            lines.append(f"  • {a['title']} — {a['company']}")
        if len(pending) > 5:
            lines.append(f"  ...y {len(pending) - 5} más")
        lines.append("")

    if sin_resp:
        lines.append("🔔 Sin respuesta — considera hacer follow-up:")
        for a in sin_resp[:3]:
            lines.append(
                f"  • {a['title']} — {a['company']} "
                f"(aplicada {a.get('date_applied', '?')})"
            )
        lines.append("")

    falta = WEEKLY_GOAL - len(applied_week)
    if falta > 0:
        lines.append(f"💡 Te faltan {falta} para la meta semanal.")

    return "\n".join(lines)


async def _send_telegram(text: str) -> None:
    import config
    from telegram import Bot

    bot = Bot(token=config.TELEGRAM_TOKEN)
    group_id = os.environ.get("TELEGRAM_GROUP_ID")
    if group_id:
        try:
            await bot.send_message(
                chat_id=group_id,
                text=text,
                message_thread_id=JOB_HUNTER_THREAD_ID,
                disable_web_page_preview=True,
            )
            return
        except Exception as exc:
            logger.error("Grupo falló, usando DM: %s", exc)
    await bot.send_message(
        chat_id=config.TELEGRAM_CHAT_ID,
        text=text,
        disable_web_page_preview=True,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(
                Path(__file__).parent.parent / "logs" / "weekly_report.log"
            ),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger.info("=== Weekly Applications Report starting ===")

    from tracker.db import init_db
    init_db()

    check_follow_ups()
    write_applications_report()
    summary = build_telegram_summary()
    asyncio.run(_send_telegram(summary))

    logger.info("=== Weekly Applications Report done ===")
