"""Canonical YouTube transcript fetching."""

from __future__ import annotations

import logging
import os

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

from app.config import TRANSCRIPT_MAX_ATTEMPTS

logger = logging.getLogger(__name__)


def _new_api() -> YouTubeTranscriptApi:
    username = os.getenv("PROXY_USERNAME")
    password = os.getenv("PROXY_PASSWORD")
    if username and password:
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(proxy_username=username, proxy_password=password)
        )
    return YouTubeTranscriptApi()


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(TRANSCRIPT_MAX_ATTEMPTS),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_with_retry(api: YouTubeTranscriptApi, video_id: str, lang: str) -> str:
    """Fetch one language's transcript, retrying only transient network errors.

    Permanent failures (no transcript, disabled captions, blocked requests) are
    raised immediately so ``get_transcript`` can try the next language.
    """
    fetched = api.fetch(video_id, languages=[lang])
    text = " ".join(snippet.text for snippet in fetched.snippets)
    if not text.strip():
        raise ValueError("empty transcript")
    return text


def get_transcript(video_id: str, languages: list[str] | None = None) -> str:
    """Return the transcript text, or "" when no transcript is available."""
    if not video_id:
        return ""
    api = _new_api()
    for lang in languages or ["en", "en-US", "a.en"]:
        try:
            return _fetch_with_retry(api, video_id, lang)
        except Exception as exc:
            logger.debug(
                "transcript unavailable for %s (%s): %s", video_id, lang, type(exc).__name__
            )
            continue
    logger.info("no transcript found for video %s", video_id)
    return ""


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    print(get_transcript(sys.argv[1] if len(sys.argv) > 1 else ""))
