"""Daily scheduling for scrape + digest + email."""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import LOG_FORMAT, validate_config
from app.runner import run_cycle

logger = logging.getLogger(__name__)


def daily_job() -> None:
    """Run one cycle; failures are already logged and recorded by run_cycle."""
    result = run_cycle()
    if result.status == "failed":
        logger.error("daily job failed: %s", result.error)
    elif result.status == "partial":
        logger.warning("daily job finished with %d failed channel(s)", result.channels_failed)
    else:
        logger.info(
            "daily job done: %d video(s), email sent=%s", result.videos_scraped, result.digest_sent
        )


def start_scheduler(hour: int = 8, minute: int = 0) -> None:
    """Validate configuration and run the blocking daily scheduler."""
    validate_config()
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    scheduler = BlockingScheduler()
    scheduler.add_job(daily_job, "cron", hour=hour, minute=minute)
    logger.info("scheduler started: daily at %02d:%02d UTC", hour, minute)
    scheduler.start()
