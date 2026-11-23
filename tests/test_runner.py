from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.runner as runner
from app.database.models import Base, RunLog, YouTubeVideo
from app.services.llm import SummarizationError


def _sqlite_sessionmaker():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def db(monkeypatch):
    factory = _sqlite_sessionmaker()
    monkeypatch.setattr(runner, "SessionLocal", factory)
    monkeypatch.setattr(runner, "ensure_schema", lambda: None)
    return factory


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("RESEND_API_KEY", "test-resend")
    monkeypatch.setenv("DIGEST_RECIPIENT_EMAIL", "reader@example.com")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost/db")


def _video(video_id: str, channel_id: str = "chan") -> runner.ChannelVideo:
    return runner.ChannelVideo(
        title=f"Title {video_id}",
        url=f"https://www.youtube.com/watch?v={video_id}",
        video_id=video_id,
        published_at=datetime.now(timezone.utc),
        description="desc",
        channel_id=channel_id,
    )


def _scrape(**overrides):
    result = {
        "videos": [_video("a"), _video("b")],
        "transcripts_fetched": 2,
        "channels_checked": 1,
        "channel_failures": {},
    }
    result.update(overrides)
    return result


def test_run_youtube_scrape_returns_structured_result(db, monkeypatch):
    class FakeScraper:
        def get_latest_videos(self, channel_id, hours=24):
            if channel_id == "bad":
                raise TimeoutError("feed timed out")
            return [_video("a"), _video("b")]

    monkeypatch.setattr(runner, "YouTubeScraper", FakeScraper)
    monkeypatch.setattr(runner, "run_transcript_backfill", lambda: {"processed": 2})

    result = runner.run_youtube_scrape(channels=["good", "bad"])

    assert set(result) == {"videos", "transcripts_fetched", "channels_checked", "channel_failures"}
    assert len(result["videos"]) == 2
    assert result["transcripts_fetched"] == 2
    assert result["channels_checked"] == 2
    assert "bad" in result["channel_failures"]
    with db() as session:
        assert session.query(YouTubeVideo).count() == 2


def test_run_youtube_scrape_does_not_duplicate_videos(db, monkeypatch):
    class FakeScraper:
        def get_latest_videos(self, channel_id, hours=24):
            return [_video("a")]

    monkeypatch.setattr(runner, "YouTubeScraper", FakeScraper)
    monkeypatch.setattr(runner, "run_transcript_backfill", lambda: {"processed": 0})

    runner.run_youtube_scrape(channels=["good"])
    runner.run_youtube_scrape(channels=["good"])

    with db() as session:
        assert session.query(YouTubeVideo).count() == 1


def test_run_cycle_success_records_timestamps_and_email(db, configured, monkeypatch):
    sent = []
    monkeypatch.setattr(runner, "run_youtube_scrape", lambda: _scrape())
    monkeypatch.setattr(runner, "run_digest", lambda hours=24: "<html>digest</html>")
    monkeypatch.setattr(
        runner, "send_digest", lambda html, to: sent.append((html, to)) or {"id": "email-1"}
    )

    result = runner.run_cycle()

    assert result.status == "success"
    assert result.videos_scraped == 2
    assert result.transcripts_fetched == 2
    assert result.channels_failed == 0
    assert result.digest_sent is True
    assert result.error is None
    assert result.started_at.tzinfo is not None
    assert result.finished_at is not None and result.finished_at >= result.started_at
    assert sent == [("<html>digest</html>", "reader@example.com")]
    with db() as session:
        row = session.query(RunLog).one()
        assert row.status == "success"
        assert row.videos_scraped == 2
        assert row.digest_sent is True
        assert row.error is None
        assert row.finished_at is not None


def test_run_cycle_partial_channel_failure_is_not_success(db, configured, monkeypatch):
    monkeypatch.setattr(
        runner,
        "run_youtube_scrape",
        lambda: _scrape(channels_checked=2, channel_failures={"bad": "TimeoutError"}),
    )
    monkeypatch.setattr(runner, "run_digest", lambda hours=24: "<html>")
    monkeypatch.setattr(runner, "send_digest", lambda html, to: {"id": "1"})

    result = runner.run_cycle()

    assert result.status == "partial"
    assert result.channels_failed == 1
    assert result.digest_sent is True
    with db() as session:
        assert session.query(RunLog).one().status == "partial"


def test_run_cycle_failure_does_not_send_email(db, configured, monkeypatch):
    monkeypatch.setattr(runner, "run_youtube_scrape", lambda: _scrape())
    monkeypatch.setattr(
        runner, "run_digest", lambda hours=24: (_ for _ in ()).throw(SummarizationError("bad key"))
    )
    sent = []
    monkeypatch.setattr(runner, "send_digest", lambda html, to: sent.append(html))

    result = runner.run_cycle()

    assert result.status == "failed"
    assert result.digest_sent is False
    assert result.error is not None and "SummarizationError" in result.error
    assert sent == []
    assert result.finished_at is not None
    with db() as session:
        row = session.query(RunLog).one()
        assert row.status == "failed"
        assert row.digest_sent is False
        assert "SummarizationError" in row.error


def test_run_cycle_fails_when_every_channel_fails(db, configured, monkeypatch):
    monkeypatch.setattr(
        runner,
        "run_youtube_scrape",
        lambda: _scrape(channels_checked=2, channel_failures={"a": "x", "b": "y"}),
    )
    called = []
    monkeypatch.setattr(runner, "send_digest", lambda html, to: called.append(html))

    result = runner.run_cycle()

    assert result.status == "failed"
    assert "all channel feeds failed" in result.error
    assert called == []


def test_run_cycle_keeps_original_error_when_logging_fails(db, configured, monkeypatch):
    monkeypatch.setattr(runner, "run_youtube_scrape", lambda: _scrape())
    monkeypatch.setattr(
        runner, "run_digest", lambda hours=24: (_ for _ in ()).throw(SummarizationError("boom"))
    )

    def broken_log(result):
        raise RuntimeError("database down")

    monkeypatch.setattr(runner, "_record_run", broken_log)

    result = runner.run_cycle()

    assert result.status == "failed"
    assert "SummarizationError" in result.error


def test_run_cycle_missing_configuration_is_recorded(db, monkeypatch):
    for name in ("GEMINI_API_KEY", "RESEND_API_KEY", "DIGEST_RECIPIENT_EMAIL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("NEON_DATABASE_URL", raising=False)

    result = runner.run_cycle()

    assert result.status == "failed"
    assert "ConfigError" in result.error
