# ruff: noqa: E501
"""Gemini summarization for the daily digest via REST."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

INTERESTS_PATH = Path(__file__).resolve().parent.parent / "prompts" / "interests.txt"
API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = "gemini-3.5-flash"
URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


class SummarizationError(RuntimeError):
    """Raised when Gemini cannot produce a usable summary.

    Callers must treat this as a failed run: sending an empty digest after a
    summarization failure would tell readers there was no news.
    """


def _load_system_prompt() -> str:
    if INTERESTS_PATH.exists():
        return INTERESTS_PATH.read_text(encoding="utf-8")
    return "Summarize each article in 2-3 sentences. Return JSON: {items:[{title,snippet,url}]}."


def summarize_articles(articles: list[dict]) -> list[dict]:
    """Summarize articles with Gemini.

    Returns ``[]`` only when there are genuinely no articles. Transport, HTTP,
    and malformed-response failures raise :class:`SummarizationError`.
    """
    if not articles:
        return []

    payload = "\n\n".join(
        f"Title: {a['title']}\nURL: {a['url']}\nContent: {(a.get('transcript') or a.get('description') or '')[:3000]}"
        for a in articles
    )
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "snippet": {"type": "string"},
                        "url": {"type": "string"},
                    },
                    "required": ["title", "snippet", "url"],
                },
            }
        },
        "required": ["items"],
    }
    body = {
        "model": MODEL,
        "input": [
            {"type": "text", "text": _load_system_prompt()},
            {"type": "text", "text": f"Articles:\n{payload}"},
        ],
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": schema,
        },
    }
    headers = {
        "x-goog-api-key": API_KEY,
        "Content-Type": "application/json",
        "Api-Revision": "2026-05-20",
    }

    try:
        response = requests.post(URL, headers=headers, json=body, timeout=(10, 60))
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        status = getattr(exc.response, "status_code", None)
        detail = f"HTTP {status}" if status else type(exc).__name__
        logger.error("Gemini request failed: %s", detail)
        raise SummarizationError(f"Gemini request failed ({detail})") from exc
    except ValueError as exc:
        logger.error("Gemini returned invalid JSON")
        raise SummarizationError("Gemini returned invalid JSON") from exc

    items = _parse_response(data)
    if items is None:
        logger.error("Gemini returned an unusable response")
        raise SummarizationError("Gemini returned an unusable response")
    logger.info("summarized %d articles into %d digest items", len(articles), len(items))
    return items


def _parse_response(data: dict) -> list[dict] | None:
    """Extract digest items from a Gemini response, or None when unusable."""
    text = ""
    for step in data.get("steps") or []:
        if step.get("type") == "model_output":
            for content in step.get("content", []):
                if content.get("type") == "text":
                    text += content.get("text", "")
    if not text:
        text = data.get("output_text") or ""
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return None
    items = parsed.get("items") if isinstance(parsed, dict) else None
    return items if isinstance(items, list) else None
