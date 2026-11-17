"""Gemini summarization for daily digest via REST."""

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

INTERESTS_PATH = Path("app/prompts/interests.txt")
API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = "gemini-3.5-flash"
URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _load_system_prompt() -> str:
    if INTERESTS_PATH.exists():
        return INTERESTS_PATH.read_text(encoding="utf-8")
    return "Summarize each article in 2-3 sentences. Return JSON: {items:[{title,snippet,url}]}."


def summarize_articles(articles: list[dict]) -> list[dict]:
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
    r = requests.post(URL, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    data = r.json()
    # extract text from steps
    text = ""
    for step in data.get("steps", []):
        if step.get("type") == "model_output":
            for c in step.get("content", []):
                if c.get("type") == "text":
                    text += c.get("text", "")
    if not text:
        text = data.get("output_text", "")
    try:
        parsed = json.loads(text)
        return parsed.get("items", [])
    except Exception:
        return []