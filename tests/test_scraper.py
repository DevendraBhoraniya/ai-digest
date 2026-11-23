from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
import requests

import app.scrapers.youtube as scraper_module
from app.scrapers.youtube import YouTubeScraper


class _Entry(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


def _feed(monkeypatch, entries, bozo=False):
    monkeypatch.setattr(
        YouTubeScraper,
        "_load_feed",
        staticmethod(lambda channel_id: SimpleNamespace(entries=entries, bozo=bozo)),
    )


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
    _feed(monkeypatch, [missing, empty, good])

    videos = YouTubeScraper().get_latest_videos("chan", hours=24)

    assert [v.video_id for v in videos] == ["good"]


def test_old_videos_are_filtered_out(monkeypatch):
    old = datetime(2020, 1, 1, tzinfo=timezone.utc).timetuple()
    _feed(
        monkeypatch,
        [_Entry(link="https://www.youtube.com/watch?v=old", title="Old", published_parsed=old)],
    )

    assert YouTubeScraper().get_latest_videos("chan", hours=24) == []


def test_malformed_feed_raises_so_failure_is_reported(monkeypatch):
    _feed(monkeypatch, [], bozo=True)

    with pytest.raises(ValueError, match="malformed feed"):
        YouTubeScraper().get_latest_videos("chan")


def test_empty_feed_is_not_a_failure(monkeypatch):
    _feed(monkeypatch, [], bozo=False)

    assert YouTubeScraper().get_latest_videos("chan") == []


def test_feed_network_error_propagates(monkeypatch):
    def failing_load(channel_id):
        raise requests.ConnectionError("feed unreachable")

    monkeypatch.setattr(YouTubeScraper, "_load_feed", staticmethod(failing_load))

    with pytest.raises(requests.ConnectionError):
        YouTubeScraper().get_latest_videos("chan")


def test_extract_video_id_formats():
    assert YouTubeScraper._extract_video_id("https://www.youtube.com/watch?v=abc&t=1") == "abc"
    assert YouTubeScraper._extract_video_id("https://www.youtube.com/shorts/abc?x=1") == "abc"
    assert YouTubeScraper._extract_video_id("https://youtu.be/abc?t=2") == "abc"


def test_module_imports_keep_requests_available():
    # _load_feed depends on requests being a declared dependency.
    assert scraper_module.requests is requests
