from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser

from app.services.youtube import get_transcript

logger = logging.getLogger(__name__)


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
    @staticmethod
    def _extract_video_id(video_url: str) -> str:
        if "youtube.com/watch?v=" in video_url:
            return video_url.split("v=")[1].split("&")[0]
        if "youtube.com/shorts/" in video_url:
            return video_url.split("shorts/")[1].split("?")[0]
        if "youtu.be/" in video_url:
            return video_url.split("youtu.be/")[1].split("?")[0]
        return video_url

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
            published_parsed = getattr(entry, "published_parsed", None)
            if not published_parsed:
                logger.warning("skipping entry without published_parsed: %s", entry.get("link", "?"))
                continue
            published = datetime(*published_parsed[:6], tzinfo=timezone.utc)
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
            video.transcript = get_transcript(video.video_id) or None
            result.append(video)
        return result


if __name__ == "__main__":
    scraper = YouTubeScraper()
    videos = scraper.scrape_channel("UCn8ujwUInbJkBhffxqAPBVQ", hours=200)
    for v in videos:
        print(v.title, "|", v.url, "|", v.published_at.isoformat())
