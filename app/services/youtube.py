from youtube_transcript_api import YouTubeTranscriptApi


def get_transcript(video_id: str, languages: list[str] | None = None) -> str:
    if not video_id:
        return ""
    langs = languages or ["en", "en-US", "a.en"]
    for lang in langs:
        try:
            fetched = YouTubeTranscriptApi().fetch(video_id, languages=[lang])
            text = " ".join(s.text for s in fetched.snippets)
            if text.strip():
                return text
        except Exception:
            continue
    return ""


if __name__ == "__main__":
    import sys

    print(get_transcript(sys.argv[1] if len(sys.argv) > 1 else ""))