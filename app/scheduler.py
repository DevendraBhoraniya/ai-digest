"""Daily scheduling for scrape + digest + email."""

import os

from apscheduler.schedulers.blocking import BlockingScheduler

from app.runner import run_youtube_scrape
from app.services.digest import run_digest
from app.services.email import send_digest


def daily_job():
    run_youtube_scrape()
    html = run_digest(hours=24)
    to = os.getenv("DIGEST_RECIPIENT_EMAIL")
    if to:
        send_digest(html, to)
    print("daily job done")


def start_scheduler(hour: int = 8, minute: int = 0):
    scheduler = BlockingScheduler()
    scheduler.add_job(daily_job, "cron", hour=hour, minute=minute)
    scheduler.start()