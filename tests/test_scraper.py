from datetime import datetime, timezone
from types import SimpleNamespace

import app.scrapers.youtube as scraper_module
from app.scrapers.youtube import YouTubeScraper


class _Entry(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


def test_skips_entries_without_published_parsed(monkeypatch):
    published = datetime.now(timezone.utc).timetuple()
    good = _Entry(
        link="https://www.youtube.com/watch?v=good",
        title="Good",
        summary="ok",
        published_parsed=published,
    )
    missing = _Entry(link="https://www.youtube.com/watch?v=bad", title="Missing")
    empty = _Entry(
        link="https://www.youtube.com/watch?v=empty",
        title="Empty",
        published_parsed=None,
    )
    monkeypatch.setattr(
        scraper_module.feedparser,
        "parse",
        lambda url: SimpleNamespace(entries=[missing, empty, good]),
    )

    videos = YouTubeScraper().get_latest_videos("chan", hours=24)

    assert [v.video_id for v in videos] == ["good"]
