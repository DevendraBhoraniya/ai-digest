from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database.models import YouTubeVideo


def upsert_video(session: Session, video) -> YouTubeVideo:
    existing = session.query(YouTubeVideo).filter_by(url=video.url).first()
    if existing:
        return existing
    row = YouTubeVideo(
        channel_id=video.channel_id if hasattr(video, "channel_id") else "",
        title=video.title,
        url=video.url,
        video_id=video.video_id,
        published_at=video.published_at,
        description=video.description or "",
    )
    session.add(row)
    session.commit()
    return row


def get_pending_transcripts(session: Session, limit: int | None = None) -> list[YouTubeVideo]:
    q = session.query(YouTubeVideo).filter_by(transcript_status="pending")
    if limit:
        q = q.limit(limit)
    return q.all()


def update_transcript(session: Session, video_id: str, transcript: str | None) -> None:
    row = session.query(YouTubeVideo).filter_by(video_id=video_id).first()
    if row:
        row.transcript = transcript
        row.transcript_status = "done" if transcript else "unavailable"
        session.commit()


def get_recent_videos(session: Session, hours: int = 24) -> list[YouTubeVideo]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return (
        session.query(YouTubeVideo)
        .filter(YouTubeVideo.published_at >= cutoff)
        .order_by(YouTubeVideo.published_at.desc())
        .all()
    )