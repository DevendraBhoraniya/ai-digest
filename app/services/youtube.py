"""Canonical YouTube transcript fetching."""

import os

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig


def _new_api() -> YouTubeTranscriptApi:
    username = os.getenv("PROXY_USERNAME")
    password = os.getenv("PROXY_PASSWORD")
    if username and password:
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=username, proxy_password=password
            )
        )
    return YouTubeTranscriptApi()


def get_transcript(video_id: str, languages: list[str] | None = None) -> str:
    """Return the transcript text, or "" when no transcript is available."""
    if not video_id:
        return ""
    api = _new_api()
    for lang in languages or ["en", "en-US", "a.en"]:
        try:
            fetched = api.fetch(video_id, languages=[lang])
            text = " ".join(s.text for s in fetched.snippets)
            if text.strip():
                return text
        except Exception:
            continue
    return ""


if __name__ == "__main__":
    import sys

    print(get_transcript(sys.argv[1] if len(sys.argv) > 1 else ""))
