import json

import app.services.digest as digest
from app.services.digest import render_digest, run_digest
from app.services.llm import _parse_response

ITEM = {"title": "T", "snippet": "S", "url": "https://example.com"}


def test_parse_steps_response():
    data = {
        "steps": [
            {
                "type": "model_output",
                "content": [
                    {"type": "text", "text": json.dumps({"items": [ITEM]})},
                ],
            }
        ]
    }
    assert _parse_response(data) == [ITEM]


def test_parse_output_text_fallback():
    assert _parse_response({"output_text": json.dumps({"items": [ITEM]})}) == [ITEM]


def test_parse_malformed_response_is_none():
    assert _parse_response({"output_text": "not json"}) is None
    assert _parse_response({}) is None
    assert _parse_response({"steps": None}) is None
    assert _parse_response({"output_text": None}) is None
    assert _parse_response({"output_text": json.dumps({"items": "nope"})}) is None


def test_render_escapes_feed_strings():
    rendered = render_digest(
        [
            {
                "title": "<b>AI & Co</b>",
                "snippet": "x < y",
                "url": "https://example.com/?a=1&b=2",
            }
        ]
    )
    assert "<b>" not in rendered
    assert "&lt;b&gt;AI &amp; Co&lt;/b&gt;" in rendered
    assert "x &lt; y" in rendered
    assert "a=1&amp;b=2" in rendered


def test_render_empty_digest():
    rendered = render_digest([])
    assert "No new articles today." in rendered
    assert "0 new items" in rendered


def test_run_digest_with_no_articles(monkeypatch):
    monkeypatch.setattr(digest, "collect_articles", lambda hours=24: [])
    monkeypatch.setattr(digest, "summarize_articles", lambda articles: [])

    rendered = run_digest(hours=24)

    assert "No new articles today." in rendered
