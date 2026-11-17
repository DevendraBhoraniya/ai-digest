import json

from app.services.digest import render_digest
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


def test_parse_malformed_response_returns_empty_list():
    assert _parse_response({"output_text": "not json"}) == []
    assert _parse_response({}) == []
    assert _parse_response({"steps": None}) == []
    assert _parse_response({"output_text": None}) == []
    assert _parse_response({"output_text": json.dumps({"items": "nope"})}) == []


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
