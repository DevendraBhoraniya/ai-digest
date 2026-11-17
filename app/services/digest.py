"""Daily digest builder: collect, summarize, render HTML."""

from datetime import datetime, timezone

from app.database.repository import get_recent_videos
from app.database.session import SessionLocal
from app.services.llm import summarize_articles


def collect_articles(hours: int = 24) -> list[dict]:
    session = SessionLocal()
    try:
        rows = get_recent_videos(session, hours=hours)
        return [
            {
                "title": r.title,
                "url": r.url,
                "transcript": r.transcript,
                "description": r.description,
            }
            for r in rows
        ]
    finally:
        session.close()


def render_digest(items: list[dict]) -> str:
    cards = []
    for it in items:
        cards.append(
            f"""<tr><td style="padding:12px 0;border-bottom:1px solid #eee;">
  <a href="{it['url']}" style="font-size:16px;font-weight:600;color:#111;text-decoration:none;">{it['title']}</a>
  <p style="margin:6px 0;color:#444;font-size:14px;line-height:1.5;">{it['snippet']}</p>
  <a href="{it['url']}" style="font-size:13px;color:#2563eb;">Read more →</a>
</td></tr>"""
        )
    rows = "\n".join(cards) if cards else '<tr><td style="padding:12px 0;color:#666;">No new articles today.</td></tr>'
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
    articles = collect_articles(hours=hours)
    items = summarize_articles(articles)
    return render_digest(items)