"""
TradiQ — Scheduler
All background jobs:
  1. Keep-alive ping        — every 10 minutes (prevents Render free-tier sleep)
  2. Nightly batched scan   — 2:00 AM IST Mon–Sat (builds Top-500 candidate pool)
  3. Saturday deep scan     — 11:00 PM IST Sat (full clean pool refresh)
  4. Sunday weekly report   — 9:00 AM IST Sun (generates weekly pick report)
"""

import logging
import os
import json
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config.settings import (
    SCHEDULE_DAY_OF_WEEK, SCHEDULE_HOUR,
    SCHEDULE_MINUTE, SCHEDULE_TIMEZONE,
)

logger = logging.getLogger("tradiq.scheduler")

REPORTS_DIR = "data/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


# ── Job 1: Keep-alive self-ping ────────────────────────────────────────────────
def keepalive_job():
    """
    Ping our own /api/health endpoint every 10 minutes.
    This prevents Render free-tier from putting the process to sleep.
    """
    import urllib.request
    try:
        # Read the public URL from env var set by Render; fall back to localhost
        host = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")
        url  = f"{host}/api/health"
        with urllib.request.urlopen(url, timeout=10) as resp:
            logger.debug(f"💓 Keep-alive ping OK → {resp.status}")
    except Exception as e:
        # Non-fatal: server is already awake (this runs inside the same process)
        logger.debug(f"💓 Keep-alive ping skipped/failed (OK): {e}")


# ── Job 2: Nightly batched scan (Mon–Sat 2:00 AM IST) ─────────────────────────
def nightly_batched_scan_job():
    """
    Runs every night at 2:00 AM IST (Mon–Sat).
    Scans all 7,200+ stocks in 100-stock batches and builds Top-500 candidate pool.
    Rate-limit safe (3 s delay between batches). Takes ~35–40 minutes.
    """
    from scheduler.batch_scanner import run_batched_scan

    logger.info("🌙 Nightly batched scan triggered — 2:00 AM IST")
    try:
        pool = run_batched_scan(top_n=500)
        logger.info(
            f"✅ Nightly scan done — {pool['total_candidates']} candidates "
            f"(scanned {pool.get('total_scanned', '?')} stocks)"
        )
    except Exception as e:
        logger.error(f"❌ Nightly batched scan failed: {e}", exc_info=True)


# ── Job 3: Saturday deep scan (Sat 11:00 PM IST) ──────────────────────────────
def saturday_deep_scan_job():
    """
    Runs every Saturday at 11:00 PM IST.
    Full clean re-scan — same batched approach but explicitly forced,
    giving a fresh pool for the whole weekend / Monday open.
    """
    from scheduler.batch_scanner import run_batched_scan

    logger.info("🔭 Saturday deep scan triggered — 11:00 PM IST")
    try:
        pool = run_batched_scan(top_n=500)
        logger.info(
            f"✅ Saturday deep scan done — {pool['total_candidates']} candidates "
            f"(scanned {pool.get('total_scanned', '?')} stocks)"
        )
    except Exception as e:
        logger.error(f"❌ Saturday deep scan failed: {e}", exc_info=True)


# ── Job 4: Sunday weekly report (Sun 9:00 AM IST) ─────────────────────────────
def sunday_report_job():
    """
    Runs every Sunday at 9:00 AM IST.
    Generates the curated weekly Top-20 report from the pre-built candidate pool.
    """
    from main_pipeline import run_pipeline

    logger.info("📋 Sunday weekly report triggered — 9:00 AM IST")
    try:
        picks    = run_pipeline()
        run_date = datetime.now().strftime("%Y-%m-%d")
        path     = os.path.join(REPORTS_DIR, f"report_{run_date}.json")
        with open(path, "w") as f:
            json.dump(picks, f, indent=2, default=str)
        logger.info(f"✅ Sunday report saved: {path} ({len(picks)} picks)")
    except Exception as e:
        logger.error(f"❌ Sunday report job failed: {e}", exc_info=True)


# ── Scheduler factory ──────────────────────────────────────────────────────────
def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=SCHEDULE_TIMEZONE)

    # 1. Keep-alive: every 10 minutes
    scheduler.add_job(
        keepalive_job,
        trigger=IntervalTrigger(minutes=10, timezone=SCHEDULE_TIMEZONE),
        id="keepalive_ping",
        name="Keep-Alive Ping (every 10 min)",
        replace_existing=True,
    )

    # 2. Nightly batched scan: 2:00 AM IST, Mon–Sat (day_of_week=0-5)
    scheduler.add_job(
        nightly_batched_scan_job,
        trigger=CronTrigger(
            day_of_week="mon-sat",
            hour=2,
            minute=0,
            timezone=SCHEDULE_TIMEZONE,
        ),
        id="nightly_batched_scan",
        name="Nightly Batched Scan — 2:00 AM IST (Mon–Sat)",
        replace_existing=True,
    )

    # 3. Saturday deep scan: Sat 11:00 PM IST
    scheduler.add_job(
        saturday_deep_scan_job,
        trigger=CronTrigger(
            day_of_week="sat",
            hour=23,
            minute=0,
            timezone=SCHEDULE_TIMEZONE,
        ),
        id="saturday_deep_scan",
        name="Saturday Deep Scan — 11:00 PM IST",
        replace_existing=True,
    )

    # 4. Sunday weekly report: Sun 9:00 AM IST
    scheduler.add_job(
        sunday_report_job,
        trigger=CronTrigger(
            day_of_week=SCHEDULE_DAY_OF_WEEK,
            hour=SCHEDULE_HOUR,
            minute=SCHEDULE_MINUTE,
            timezone=SCHEDULE_TIMEZONE,
        ),
        id="sunday_weekly_report",
        name="Sunday Weekly Report — 9:00 AM IST",
        replace_existing=True,
    )

    return scheduler
