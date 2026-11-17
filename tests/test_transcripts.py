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


def test_scraper_uses_canonical_implementation():
    from app.scrapers.youtube import get_transcript as scraper_get_transcript

    assert scraper_get_transcript is youtube_service.get_transcript
