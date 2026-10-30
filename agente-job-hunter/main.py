#!/usr/bin/env python3
"""
Job Hunter — Orquestador principal.
Ejecuta el pipeline completo: scraping → dedup → filter → analysis → Telegram.
"""
import asyncio
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from storage.store import is_new_job, mark_as_seen, prune_old_entries
from filters.job_filter import filter_jobs
from analysis.gap_analyzer import analyze_jobs
from notifier.telegram_bot import send_report
from tracker.db import init_db, get_blocked_companies, is_url_tracked

# Garantizar que logs/ existe antes de inicializar el FileHandler
os.makedirs("logs", exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/job_hunter.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def run_scrapers() -> list:
    """Ejecuta todos los scrapers en paralelo. LinkedIn en su propio hilo."""
    from scrapers import remote_ok, web3_career, linkedin, indeed, greenhouse

    scraper_fns = [
        remote_ok.fetch_jobs,
        web3_career.fetch_jobs,
        linkedin.fetch_jobs,
        indeed.fetch_jobs,
        greenhouse.fetch_jobs,
    ]

    all_jobs = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fn): fn.__module__ for fn in scraper_fns}
        for future in as_completed(futures):
            module = futures[future]
            try:
                jobs = future.result()
                logger.info(f"{module}: {len(jobs)} jobs returned")
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"{module} raised exception: {e}")

    return all_jobs


def deduplicate(jobs: list) -> list:
    """Filtra jobs ya vistos en seen_scrapes, ya registrados en applications, o de empresa bloqueada."""
    blocked = get_blocked_companies()
    new_jobs = []
    for j in jobs:
        url = j.get("url", "")
        company = (j.get("company") or "").lower()
        if not url:
            continue
        if not is_new_job(url):
            continue
        if is_url_tracked(url):
            continue
        if company in blocked:
            logger.info(f"Empresa bloqueada (no_reapply_until activo): {j.get('company')}")
            continue
        new_jobs.append(j)
    logger.info(f"Dedup: {len(jobs)} total → {len(new_jobs)} new")
    return new_jobs


_DROPLET = "root@142.93.203.22"
_DROPLET_PATH = "/opt/jarvis/shared_reports/"
_LOCAL_REPORT = Path(__file__).parent.parent / "shared_reports" / "job_market_latest.md"


def _write_local_report(strict: list, broad: list, top3: list) -> None:
    from datetime import datetime as _dt
    today = date.today().isoformat()
    lines = [
        f"# Job Market Report — {today}",
        "",
        "## Resumen ejecutivo",
        f"- Total de empleos encontrados: {len(strict) + len(broad)}",
        f"- Empleos en tier estricto (strict): {len(strict)}",
        f"- Empleos en tier amplio (broad): {len(broad)}",
        "",
        "## Top 3 empleos destacados",
        "",
    ]
    for i, job in enumerate(top3[:3], 1):
        lines += [
            f"### {i}. {job.get('title', '?')} — {job.get('company', '?')}",
            f"- **URL:** {job.get('url', '')}",
            f"- **Por qué encaja:** {job.get('why_fits') or job.get('claude_analysis') or '—'}",
            "",
        ]
    lines += [
        "## Todos los empleos (strict + broad)",
        "",
        "| # | Título | Empresa | URL |",
        "|---|--------|---------|-----|",
    ]
    for i, job in enumerate(strict + broad, 1):
        lines.append(f"| {i} | {job.get('title', '?')} | {job.get('company', '?')} | {job.get('url', '')} |")
    lines += [
        "",
        "## Metadatos",
        f"- Generado: {_dt.now().strftime('%Y-%m-%d %H:%M')}",
        "- Agente: agente-job-hunter",
    ]
    _LOCAL_REPORT.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"job_market_latest.md escrito: {len(strict)} strict, {len(broad)} broad")


def _sync_report_to_droplet() -> None:
    if not _LOCAL_REPORT.exists():
        logger.warning("job_market_latest.md not found — skipping rsync")
        return
    key = Path.home() / ".ssh" / "jarvis_do"
    result = subprocess.run(
        ["rsync", "-az", "-e", f"ssh -i {key}", str(_LOCAL_REPORT), f"{_DROPLET}:{_DROPLET_PATH}"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        logger.info("Synced job_market_latest.md to Droplet")
    else:
        logger.warning(f"rsync to Droplet failed: {result.stderr.strip()}")


def main():
    logger.info("=== Job Hunter starting ===")
    logger.info(f"Date: {date.today().isoformat()}")

    # 0. Init DB + auto-flag aplicaciones sin respuesta (≥7 días)
    from tracker.weekly_report import check_follow_ups, write_applications_report
    init_db()
    stale = check_follow_ups()
    if stale:
        logger.info(f"Auto-marcadas como sin_respuesta: {[a['company'] for a in stale]}")

    # 1. Prunear seen_scrapes
    pruned = prune_old_entries(ttl_days=90)
    logger.info(f"Pruned {pruned} seen_scrapes entries (>90 días)")

    # 2. Scraping
    all_jobs = run_scrapers()
    logger.info(f"Total scraped: {len(all_jobs)} jobs")

    # 3. Deduplicación (seen_scrapes + applications + empresas bloqueadas)
    new_jobs = deduplicate(all_jobs)
    if not new_jobs:
        logger.info("No new jobs this week. Skipping Telegram.")
        return

    # 4. Filtrado
    filtered = filter_jobs(new_jobs)
    strict = filtered["strict"]
    broad = filtered["broad"]
    logger.info(f"Filtered: {len(strict)} strict, {len(broad)} broad")

    if not strict and not broad:
        logger.info("No jobs passed filters. Skipping Telegram.")
        return

    # 5. Gap analysis
    analyzed = analyze_jobs(strict, broad)

    # 5b. Filtrar por fit_score mínimo (min_score_to_include en fit_config.json)
    try:
        import json as _json
        fit_cfg = _json.loads((Path(__file__).parent / "fit_config.json").read_text())
        min_score = fit_cfg.get("min_score_to_include", 0)
        if min_score > 0:
            strict_ok = [j for j in analyzed["strict"] if j.get("fit_score", 0) >= min_score]
            broad_ok  = [j for j in analyzed["broad"]  if j.get("fit_score", 0) >= min_score]
            if strict_ok or broad_ok:
                analyzed["strict"] = strict_ok
                analyzed["broad"]  = broad_ok
                logger.info(f"Fit filter (>={min_score} pts): {len(strict_ok)} strict, {len(broad_ok)} broad pasan")
            else:
                logger.warning("Fit filter dejaría todo vacío — omitiendo filtro (fallback)")
    except Exception as e:
        logger.warning(f"fit_config.json no legible — omitiendo fit filter: {e}")

    # 6. Telegram
    try:
        asyncio.run(send_report(analyzed["strict"], analyzed["broad"], analyzed["top3"]))
        # Marcar como vistos TODOS los jobs nuevos scrapeados (no solo los filtrados),
        # para evitar reprocesar jobs descartados la próxima semana.
        all_new_urls = [j["url"] for j in new_jobs if j.get("url")]
        for url in all_new_urls:
            mark_as_seen(url)
        logger.info(f"seen_scrapes updated with {len(all_new_urls)} new entries")
        _write_local_report(analyzed["strict"], analyzed["broad"], analyzed["top3"])
        write_applications_report()
    except Exception as e:
        logger.error(f"Telegram send failed — seen_scrapes NOT updated: {e}")
        sys.exit(1)

    # Sync report to Droplet so P-LU can read it
    _sync_report_to_droplet()
    logger.info("=== Job Hunter completed successfully ===")


if __name__ == "__main__":
    main()
