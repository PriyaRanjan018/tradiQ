"""
TradiQ — Sunday Scheduler
Runs the full pipeline every Sunday at 9:00 AM IST.
"""

import logging
import json
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config.settings import (
    SCHEDULE_DAY_OF_WEEK, SCHEDULE_HOUR,
    SCHEDULE_MINUTE, SCHEDULE_TIMEZONE,
)

logger = logging.getLogger(__name__)
REPORTS_DIR = "data/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


def scheduled_job():
    """The actual job that runs every Sunday."""
    from main_pipeline import run_pipeline

    logger.info("⏰ Sunday scheduler triggered — starting pipeline")
    try:
        picks = run_pipeline()
        run_date = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(REPORTS_DIR, f"report_{run_date}.json")
        with open(path, "w") as f:
            json.dump(picks, f, indent=2, default=str)
        logger.info(f"✅ Sunday report saved: {path} ({len(picks)} picks)")
    except Exception as e:
        logger.error(f"❌ Scheduled job failed: {e}", exc_info=True)


def nightly_pool_job():
    """Nightly job that pre-computes the 500 candidate stock pool."""
    from main_pipeline import build_candidate_pool
    logger.info("🌙 Nightly Candidate Pool scheduler triggered (2:00 AM IST)")
    try:
        build_candidate_pool(top_n=500)
        logger.info("✅ Nightly Candidate Pool build completed successfully")
    except Exception as e:
        logger.error(f"❌ Nightly Candidate Pool build failed: {e}", exc_info=True)


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=SCHEDULE_TIMEZONE)
    
    # 1. Sunday weekly report
    scheduler.add_job(
        scheduled_job,
        trigger=CronTrigger(
            day_of_week=SCHEDULE_DAY_OF_WEEK,
            hour=SCHEDULE_HOUR,
            minute=SCHEDULE_MINUTE,
            timezone=SCHEDULE_TIMEZONE,
        ),
        id="sunday_stock_scan",
        name="Sunday Stock Analysis",
        replace_existing=True,
    )
    
    # 2. Nightly 2:00 AM IST Candidate Pool Pre-computation
    scheduler.add_job(
        nightly_pool_job,
        trigger=CronTrigger(
            hour=2,
            minute=0,
            timezone=SCHEDULE_TIMEZONE,
        ),
        id="nightly_candidate_pool",
        name="Nightly Candidate Pool (2:00 AM IST)",
        replace_existing=True,
    )
    
    return scheduler
