"""Fetch recent YouTube uploads from a channel's public RSS feed."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
import requests

from app.config import HTTP_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
USER_AGENT = "ai-news-aggregator/0.1 (+https://github.com/)"


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

    @staticmethod
    def _load_feed(channel_id: str):
        """Download and parse a channel feed. Network errors propagate to the caller."""
        response = requests.get(
            FEED_URL.format(channel_id=channel_id),
            timeout=HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        return feedparser.parse(response.content)

    def get_latest_videos(self, channel_id: str, hours: int = 24) -> list[ChannelVideo]:
        """Return the channel's uploads published within ``hours``.

        Raises when the feed cannot be fetched or is malformed with no usable
        entries, so callers can record a channel-level failure instead of
        treating it as "no new videos".
        """
        feed = self._load_feed(channel_id)
        if not feed.entries:
            if getattr(feed, "bozo", False):
                raise ValueError(f"malformed feed for channel {channel_id}")
            logger.info("no entries in feed for channel %s", channel_id)
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        videos = []
        for entry in feed.entries:
            if "/shorts/" in entry.link:
                continue
            published_parsed = getattr(entry, "published_parsed", None)
            if not published_parsed:
                logger.warning(
                    "skipping entry without published_parsed: %s", entry.get("link", "?")
                )
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


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    channel = sys.argv[1] if len(sys.argv) > 1 else "UCn8ujwUInbJkBhffxqAPBVQ"
    for video in YouTubeScraper().get_latest_videos(channel, hours=48):
        print(video.title, "|", video.url, "|", video.published_at.isoformat())
