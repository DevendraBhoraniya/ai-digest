"""Database access helpers for videos and transcripts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import YouTubeVideo
from app.scrapers.youtube import ChannelVideo


def upsert_video(session: Session, video: ChannelVideo) -> YouTubeVideo:
    """Insert a video or refresh the stored title/description for its URL."""
    existing = session.query(YouTubeVideo).filter_by(url=video.url).first()
    if existing:
        existing.title = video.title
        existing.description = video.description or ""
        session.commit()
        return existing

    row = YouTubeVideo(
        channel_id=video.channel_id,
        title=video.title,
        url=video.url,
        video_id=video.video_id,
        published_at=video.published_at,
        description=video.description or "",
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        # Another run inserted the same URL between our SELECT and INSERT.
        session.rollback()
        existing = session.query(YouTubeVideo).filter_by(url=video.url).one()
        existing.title = video.title
        existing.description = video.description or ""
        session.commit()
        return existing
    return row


def get_pending_transcripts(session: Session, limit: int | None = None) -> list[YouTubeVideo]:
    """Return videos whose transcript has not been resolved yet."""
    q = session.query(YouTubeVideo).filter_by(transcript_status="pending")
    if limit:
        q = q.limit(limit)
    return q.all()


def update_transcript(session: Session, video_id: str, transcript: str | None) -> None:
    """Store a transcript, or mark the video unavailable when none was found."""
    row = session.query(YouTubeVideo).filter_by(video_id=video_id).first()
    if row:
        row.transcript = transcript
        row.transcript_status = "done" if transcript else "unavailable"
        session.commit()


def get_recent_videos(session: Session, hours: int = 24) -> list[YouTubeVideo]:
    """Return videos published within the last ``hours`` hours, newest first."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return (
        session.query(YouTubeVideo)
        .filter(YouTubeVideo.published_at >= cutoff)
        .order_by(YouTubeVideo.published_at.desc())
        .all()
    )
