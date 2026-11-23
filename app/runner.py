"""Scrape, summarize, email and record one digest run."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TypedDict

from app.config import (
    DIGEST_HOURS,
    LOOKBACK_HOURS,
    YOUTUBE_CHANNELS,
    validate_config,
)
from app.database.create_tables import ensure_schema
from app.database.models import RunLog, YouTubeVideo
from app.database.repository import get_pending_transcripts, update_transcript, upsert_video
from app.database.session import SessionLocal
from app.scrapers.youtube import ChannelVideo, YouTubeScraper
from app.services.digest import run_digest
from app.services.email import send_digest
from app.services.youtube import get_transcript

logger = logging.getLogger(__name__)


class ScrapeResult(TypedDict):
    videos: list[ChannelVideo]
    transcripts_fetched: int
    channels_checked: int
    channel_failures: dict[str, str]


@dataclass(slots=True)
class CycleResult:
    """Outcome of one scrape -> digest -> email run."""

    started_at: datetime
    finished_at: datetime | None = None
    status: str = "failed"  # "success" | "partial" | "failed"
    videos_scraped: int = 0
    transcripts_fetched: int = 0
    channels_failed: int = 0
    channels_checked: int = 0
    digest_sent: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status in ("success", "partial")


def run_youtube_scrape(channels: list[str] | None = None, hours: int | None = None) -> ScrapeResult:
    """Scrape channels, store new videos, then backfill pending transcripts.

    A failing channel is logged and reported in ``channel_failures`` instead of
    aborting the run; videos already stored for that channel are preserved.
    """
    channels = channels or YOUTUBE_CHANNELS
    hours = hours if hours is not None else LOOKBACK_HOURS
    scraper = YouTubeScraper()
    videos: list[ChannelVideo] = []
    channel_failures: dict[str, str] = {}

    with SessionLocal() as session:
        for channel_id in channels:
            try:
                latest = scraper.get_latest_videos(channel_id, hours=hours)
            except Exception as exc:
                detail = f"{type(exc).__name__}: {exc}"
                logger.warning("channel %s failed: %s", channel_id, detail)
                channel_failures[channel_id] = detail
                continue
            for video in latest:
                video.channel_id = channel_id
                upsert_video(session, video)
                videos.append(video)

    backfill = run_transcript_backfill()
    transcripts = _transcripts_for(videos)
    for video in videos:
        video.transcript = transcripts.get(video.video_id)

    logger.info(
        "scraped %d video(s) from %d channel(s), %d channel failure(s), %d transcript(s)",
        len(videos),
        len(channels),
        len(channel_failures),
        backfill["processed"],
    )
    return {
        "videos": videos,
        "transcripts_fetched": backfill["processed"],
        "channels_checked": len(channels),
        "channel_failures": channel_failures,
    }


def _transcripts_for(videos: list[ChannelVideo]) -> dict[str, str | None]:
    """Load stored transcripts for the scraped videos in one query."""
    if not videos:
        return {}
    with SessionLocal() as session:
        rows = session.query(YouTubeVideo).filter(
            YouTubeVideo.video_id.in_([video.video_id for video in videos])
        )
        return {row.video_id: row.transcript for row in rows}


def run_transcript_backfill(limit: int | None = None) -> dict[str, int]:
    """Fetch transcripts for videos still marked pending."""
    processed = 0
    with SessionLocal() as session:
        for row in get_pending_transcripts(session, limit=limit):
            transcript = get_transcript(row.video_id)
            update_transcript(session, row.video_id, transcript if transcript else None)
            processed += 1
    logger.info("transcript backfill processed %d video(s)", processed)
    return {"processed": processed}


def _record_run(result: CycleResult) -> None:
    """Insert a run_logs row. Raises if the database write fails."""
    with SessionLocal() as session:
        session.add(
            RunLog(
                started_at=result.started_at,
                finished_at=result.finished_at,
                status=result.status,
                videos_scraped=result.videos_scraped,
                transcripts_fetched=result.transcripts_fetched,
                channels_failed=result.channels_failed,
                digest_sent=result.digest_sent,
                error=result.error,
            )
        )
        session.commit()


def run_cycle() -> CycleResult:
    """Execute one full digest cycle and always record the outcome.

    Failures are returned in the result instead of raised, so callers can exit
    non-zero or log without losing the run record. A run-log write failure is
    logged but never replaces the original error.
    """
    result = CycleResult(started_at=datetime.now(timezone.utc))
    logger.info("execution started")
    try:
        validate_config()
        recipient = os.environ["DIGEST_RECIPIENT_EMAIL"].strip()
        ensure_schema()

        scrape = run_youtube_scrape()
        result.videos_scraped = len(scrape["videos"])
        result.transcripts_fetched = scrape["transcripts_fetched"]
        result.channels_failed = len(scrape["channel_failures"])
        result.channels_checked = scrape["channels_checked"]
        if scrape["channels_checked"] and result.channels_failed == scrape["channels_checked"]:
            raise RuntimeError("all channel feeds failed; digest not sent")

        html = run_digest(hours=DIGEST_HOURS)
        send_digest(html, recipient)
        result.digest_sent = True
        result.status = "partial" if result.channels_failed else "success"
    except Exception as exc:
        result.status = "failed"
        result.error = f"{type(exc).__name__}: {exc}"
        logger.exception("cycle failed")
    finally:
        result.finished_at = datetime.now(timezone.utc)
        try:
            _record_run(result)
        except Exception:
            logger.exception("could not write run log")

    duration = 0.0
    if result.finished_at is not None:
        duration = (result.finished_at - result.started_at).total_seconds()
    logger.info(
        "cycle finished status=%s channels_processed=%d videos=%d transcripts=%d "
        "channels_failed=%d digest_sent=%s duration=%.2fs",
        result.status,
        result.channels_checked,
        result.videos_scraped,
        result.transcripts_fetched,
        result.channels_failed,
        result.digest_sent,
        duration,
    )
    return result
