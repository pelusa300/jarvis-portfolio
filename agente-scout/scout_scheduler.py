"""
Punto de entrada del agente.
Ejecutar con: python scout_scheduler.py
Background:   nohup python scout_scheduler.py > logs/scheduler.log 2>&1 &
"""
import logging
import os
import sys
from pathlib import Path

LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "scheduler.log"),
    ],
)
logger = logging.getLogger(__name__)

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger


def job_daily():
    from scout_runner import run
    run("daily")


def job_weekly():
    from scout_runner import run
    run("weekly")


def main():
    scheduler = BlockingScheduler(timezone="America/Denver")

    scheduler.add_job(
        job_daily,
        CronTrigger(hour=7, minute=0, timezone="America/Denver"),
        id="daily_scout",
        name="Daily Scout Report — 7AM",
    )

    scheduler.add_job(
        job_weekly,
        CronTrigger(day_of_week="sun", hour=7, minute=0, timezone="America/Denver"),
        id="weekly_scout",
        name="Weekly Scout Report — Sunday 7AM",
    )

    logger.info("=" * 50)
    logger.info("Scout Scheduler started")
    logger.info("Daily:  7:00 AM America/Denver")
    logger.info("Weekly: Sunday 7:00 AM America/Denver")
    logger.info("=" * 50)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")
    except Exception as e:
        logger.exception("Scheduler crashed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
