# ruff: noqa: E501
"""Daily digest builder: collect, summarize, render HTML."""

from __future__ import annotations

import html
import logging
from datetime import datetime, timezone

from app.database.repository import get_recent_videos
from app.database.session import SessionLocal
from app.services.llm import SummarizationError, summarize_articles

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


def _fallback_summary(articles: list[dict]) -> list[dict]:
    """Generate a basic summary without LLM when all providers fail."""
    items = []
    for a in articles:
        content = a.get("transcript") or a.get("description") or ""
        snippet = content[:280].strip()
        if len(content) > 280:
            snippet += "..."
        items.append({"title": a["title"], "snippet": snippet, "url": a["url"]})
    return items


def run_digest(hours: int = 24) -> str:
    """Collect recent videos, summarize them, and return the email HTML.

    Falls back to simple extractive summary if LLM summarization fails.
    """
    articles = collect_articles(hours=hours)
    logger.info("digest collected %d article(s) from the last %d hours", len(articles), hours)
    try:
        items = summarize_articles(articles)
    except SummarizationError as exc:
        logger.warning("LLM summarization failed, using fallback: %s", exc)
        items = _fallback_summary(articles)
    return render_digest(items)


def render_digest(items: list[dict]) -> str:
    """Render digest items as a bulletproof HTML email (works in Outlook, Gmail, Apple Mail)."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    count = len(items)

    cards = []
    for item in items:
        url = html.escape(item["url"])
        title = html.escape(item["title"])
        snippet = html.escape(item["snippet"])
        cards.append(
            f"""<tr>
  <td style="padding:20px 0 20px 0;border-bottom:1px solid #e5e7eb;">
    <a href="{url}" style="color:#111827;text-decoration:none;font-weight:600;font-size:17px;line-height:1.3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">{title}</a>
    <p style="margin:8px 0 12px 0;color:#4b5563;font-size:14px;line-height:1.6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">{snippet}</p>
    <a href="{url}" style="color:#2563eb;text-decoration:none;font-weight:500;font-size:13px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">Read more &rarr;</a>
  </td>
</tr>"""
        )

    rows = (
        "\n".join(cards)
        if cards
        else "<tr><td style=\"padding:40px 0;text-align:center;color:#9ca3af;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:14px;\">No new articles today.</td></tr>"
    )

    # Bulletproof: tables only, inline styles, no gradients, no flexbox, no border-radius, no box-shadow
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="x-apple-disable-message-reformatting">
  <title>Daily AI News Digest</title>
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.5;color:#111827;">
  <!--[if mso | IE]>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color:#f3f4f6;">
  <![endif]-->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f3f4f6;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <!--[if mso | IE]>
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;"><tr><td>
        <![endif]-->
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;background-color:#ffffff;">
          <!-- Header - solid color, no gradient -->
          <tr>
            <td style="padding:28px 32px 20px 32px;background-color:#1e3a8a;">
              <h1 style="margin:0;font-size:24px;font-weight:700;color:#ffffff;line-height:1.2;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">Daily AI News Digest</h1>
              <p style="margin:8px 0 0;font-size:14px;color:#bfdbfe;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">{today} &middot; {count} new item{"" if count == 1 else "s"}</p>
            </td>
          </tr>
          <!-- Content -->
          <tr>
            <td style="padding:24px 32px 32px 32px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
                {rows}
              </table>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:20px 32px;border-top:1px solid #e5e7eb;background-color:#f9fafb;">
              <p style="margin:0;font-size:12px;color:#9ca3af;text-align:center;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">You&rsquo;re receiving this because you subscribed to the AI News Aggregator.</p>
              <p style="margin:8px 0 0;font-size:11px;color:#d1d5db;text-align:center;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">Unsubscribe or adjust preferences in your account settings.</p>
            </td>
          </tr>
        </table>
        <!--[if mso | IE]>
        </td></tr></table>
        <![endif]-->
      </td>
    </tr>
  </table>
  <!--[if mso | IE]>
  </td></tr></table>
  <![endif]-->
</body>
</html>"""
