from app.config import LOOKBACK_HOURS, YOUTUBE_CHANNELS
from app.database.models import YouTubeVideo
from app.database.repository import get_pending_transcripts, update_transcript, upsert_video
from app.database.models import Base
from app.database.session import SessionLocal, engine
from app.scrapers.youtube import YouTubeScraper
from app.services.youtube import get_transcript


def run_youtube_scrape(channels=None, hours=None) -> list:
    channels = channels or YOUTUBE_CHANNELS
    hours = hours if hours is not None else LOOKBACK_HOURS
    scraper = YouTubeScraper()
    Base.metadata.create_all(engine)
    session = SessionLocal()
    results = []
    for channel_id in channels:
        for video in scraper.get_latest_videos(channel_id, hours=hours):
            video.channel_id = channel_id  # attach for storage
            upsert_video(session, video)
            results.append(video)
    session.close()
    # backfill transcripts and attach to returned videos
    run_transcript_backfill()
    session = SessionLocal()
    for video in results:
        row = session.query(YouTubeVideo).filter_by(video_id=video.video_id).first()
        if row:
            video.transcript = row.transcript
    session.close()
    return results


def run_transcript_backfill(limit=None) -> dict:
    Base.metadata.create_all(engine)
    session = SessionLocal()
    rows = get_pending_transcripts(session, limit=limit)
    processed = 0
    for row in rows:
        t = get_transcript(row.video_id)
        update_transcript(session, row.video_id, t if t else None)
        processed += 1
    session.close()
    return {"processed": processed}


if __name__ == "__main__":
    videos = run_youtube_scrape()
    print(f"scraped {len(videos)} videos")
    info = run_transcript_backfill()
    print(f"transcripts processed: {info['processed']}")