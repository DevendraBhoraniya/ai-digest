from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig


@dataclass
class Transcript:
    text: str


@dataclass
class ChannelVideo:
    title: str
    url: str
    video_id: str
    published_at: datetime
    description: str = ""
    channel_id: str = ""
    transcript: Optional[str] = None


class YouTubeScraper:
    def __init__(self):
        proxy_config = None
        proxy_username = os.getenv("PROXY_USERNAME")
        proxy_password = os.getenv("PROXY_PASSWORD")
        if proxy_username and proxy_password:
            proxy_config = WebshareProxyConfig(
                proxy_username=proxy_username,
                proxy_password=proxy_password,
            )
        self.transcript_api = YouTubeTranscriptApi(proxy_config=proxy_config)

    @staticmethod
    def _extract_video_id(video_url: str) -> str:
        if "youtube.com/watch?v=" in video_url:
            return video_url.split("v=")[1].split("&")[0]
        if "youtube.com/shorts/" in video_url:
            return video_url.split("shorts/")[1].split("?")[0]
        if "youtu.be/" in video_url:
            return video_url.split("youtu.be/")[1].split("?")[0]
        return video_url

    def get_transcript(self, video_id: str) -> Optional[Transcript]:
        for lang in ("en", "en-US", "a.en"):
            try:
                fetched = self.transcript_api.fetch(video_id, languages=[lang])
                text = " ".join(s.text for s in fetched.snippets)
                if text.strip():
                    return Transcript(text=text)
            except Exception:
                continue
        return None

    def get_latest_videos(self, channel_id: str, hours: int = 24) -> list[ChannelVideo]:
        feed = feedparser.parse(
            f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        )
        if not feed.entries:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        videos = []
        for entry in feed.entries:
            if "/shorts/" in entry.link:
                continue
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published >= cutoff:
                videos.append(
                    ChannelVideo(
                        title=entry.title,
                        url=entry.link,
                        video_id=self._extract_video_id(entry.link),
                        published_at=published,
                        description=entry.get("summary", ""),
                        channel_id=channel_id,
                    )
                )
        return videos

    def scrape_channel(self, channel_id: str, hours: int = 24) -> list[ChannelVideo]:
        videos = self.get_latest_videos(channel_id, hours)
        result = []
        for video in videos:
            transcript = self.get_transcript(video.video_id)
            video.transcript = transcript.text if transcript else None
            result.append(video)
        return result


if __name__ == "__main__":
    scraper = YouTubeScraper()
    videos = scraper.scrape_channel("UCn8ujwUInbJkBhffxqAPBVQ", hours=200)
    for v in videos:
        print(v.title, "|", v.url, "|", v.published_at.isoformat())