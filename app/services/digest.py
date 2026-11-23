# ruff: noqa: E501
"""Daily digest builder: collect, summarize, render HTML."""

from __future__ import annotations

import html
import logging
from datetime import datetime, timezone

from app.database.repository import get_recent_videos
from app.database.session import SessionLocal
from app.services.llm import summarize_articles

logger = logging.getLogger(__name__)


def collect_articles(hours: int = 24) -> list[dict]:
    """Load recently published videos from the database as article dicts."""
    with SessionLocal() as session:
        rows = get_recent_videos(session, hours=hours)
        return [
            {
                "title": row.title,
                "url": row.url,
                "transcript": row.transcript,
                "description": row.description,
            }
            for row in rows
        ]


def render_digest(items: list[dict]) -> str:
    """Render digest items as the HTML email body."""
    cards = []
    for item in items:
        url = html.escape(item["url"])
        title = html.escape(item["title"])
        snippet = html.escape(item["snippet"])
        cards.append(
            f"""<tr><td style="padding:12px 0;border-bottom:1px solid #eee;">
  <a href="{url}" style="font-size:16px;font-weight:600;color:#111;text-decoration:none;">{title}</a>
  <p style="margin:6px 0;color:#444;font-size:14px;line-height:1.5;">{snippet}</p>
  <a href="{url}" style="font-size:13px;color:#2563eb;">Read more →</a>
</td></tr>"""
        )
    rows = (
        "\n".join(cards)
        if cards
        else '<tr><td style="padding:12px 0;color:#666;">No new articles today.</td></tr>'
    )
    return f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#222;">
  <h1 style="font-size:20px;margin-bottom:4px;">Daily AI News Digest</h1>
  <p style="color:#666;font-size:13px;margin-top:0;">{datetime.now(timezone.utc).date()} · {len(items)} new items</p>
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
    {rows}
  </table>
  <p style="color:#999;font-size:11px;margin-top:24px;">You're receiving this because you subscribed to the AI news aggregator.</p>
</body></html>"""


def run_digest(hours: int = 24) -> str:
    """Collect recent videos, summarize them, and return the email HTML.

    Raises :class:`app.services.llm.SummarizationError` when summarization
    fails, so callers never send a misleading empty digest.
    """
    articles = collect_articles(hours=hours)
    logger.info("digest collected %d article(s) from the last %d hours", len(articles), hours)
    items = summarize_articles(articles)
    return render_digest(items)
