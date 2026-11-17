from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, YouTubeVideo
from app.database.repository import upsert_video


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _video(url="https://www.youtube.com/watch?v=abc", title="First", description="desc"):
    return SimpleNamespace(
        channel_id="chan",
        title=title,
        url=url,
        video_id="abc",
        published_at=datetime.now(timezone.utc),
        description=description,
    )


def test_upsert_same_video_twice_keeps_one_row():
    session = _session()
    first = upsert_video(session, _video())
    second = upsert_video(session, _video(title="Updated"))

    assert first.id == second.id
    assert session.scalar(select(func.count()).select_from(YouTubeVideo)) == 1
    assert session.get(YouTubeVideo, first.id).title == "Updated"
    session.close()
