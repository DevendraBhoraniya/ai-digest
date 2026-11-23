from tenacity import wait_none

from app.services import youtube as youtube_service


class _Fetched:
    def __init__(self, *texts):
        self.snippets = [type("Snippet", (), {"text": t})() for t in texts]


class _FakeApi:
    """Returns the mapped fetch result per language; raises when unmapped."""

    def __init__(self, by_language):
        self.by_language = by_language
        self.attempted = []

    def fetch(self, video_id, languages):
        language = languages[0]
        self.attempted.append(language)
        result = self.by_language[language]
        if isinstance(result, Exception):
            raise result
        return result


def _no_wait(monkeypatch):
    monkeypatch.setattr(youtube_service._fetch_with_retry.retry, "wait", wait_none())


def test_falls_back_to_next_language(monkeypatch):
    api = _FakeApi({"en": RuntimeError("no en"), "en-US": _Fetched("hello", "world")})
    monkeypatch.setattr(youtube_service, "_new_api", lambda: api)

    assert youtube_service.get_transcript("vid") == "hello world"
    assert api.attempted == ["en", "en-US"]


def test_returns_empty_string_when_no_transcript(monkeypatch):
    api = _FakeApi({})
    monkeypatch.setattr(youtube_service, "_new_api", lambda: api)

    assert youtube_service.get_transcript("vid") == ""


def test_empty_video_id_returns_empty_string():
    assert youtube_service.get_transcript("") == ""


def test_transient_errors_retry_three_times_per_language(monkeypatch):
    _no_wait(monkeypatch)
    api = _FakeApi({"en": OSError("net"), "en-US": OSError("net"), "a.en": OSError("net")})
    monkeypatch.setattr(youtube_service, "_new_api", lambda: api)

    assert youtube_service.get_transcript("vid") == ""
    assert len(api.attempted) == 9
    assert api.attempted.count("en") == 3


def test_permanent_errors_are_not_retried(monkeypatch):
    _no_wait(monkeypatch)
    api = _FakeApi(
        {
            "en": RuntimeError("disabled"),
            "en-US": RuntimeError("disabled"),
            "a.en": RuntimeError("disabled"),
        }
    )
    monkeypatch.setattr(youtube_service, "_new_api", lambda: api)

    assert youtube_service.get_transcript("vid") == ""
    assert api.attempted == ["en", "en-US", "a.en"]


def test_empty_transcript_falls_through_languages(monkeypatch):
    _no_wait(monkeypatch)
    api = _FakeApi({"en": _Fetched(""), "en-US": _Fetched("  "), "a.en": _Fetched("hello")})
    monkeypatch.setattr(youtube_service, "_new_api", lambda: api)

    assert youtube_service.get_transcript("vid") == "hello"
    assert api.attempted == ["en", "en-US", "a.en"]
