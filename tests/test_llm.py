import json

import pytest
import requests

from app.services import llm

ITEM = {"title": "T", "snippet": "S", "url": "https://example.com"}


class _Response:
    def __init__(self, payload=None, exc=None):
        self.payload = payload
        self.exc = exc
        self.status_code = 200

    def raise_for_status(self):
        if self.exc:
            raise self.exc

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def _post(monkeypatch, response):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(kwargs)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(llm.requests, "post", fake_post)
    return calls


def test_summarize_articles_returns_items(monkeypatch):
    data = {
        "steps": [
            {
                "type": "model_output",
                "content": [{"type": "text", "text": json.dumps({"items": [ITEM]})}],
            }
        ]
    }
    calls = _post(monkeypatch, _Response(payload=data))

    result = llm.summarize_articles([{"title": "t", "url": "u", "description": "d"}])

    assert result == [ITEM]
    assert len(calls) == 1
    assert calls[0]["timeout"] == (10, 60)


def test_summarize_empty_input_skips_api(monkeypatch):
    calls = _post(monkeypatch, _Response(payload={}))

    assert llm.summarize_articles([]) == []
    assert calls == []


def test_summarize_http_failure_raises(monkeypatch):
    _post(monkeypatch, requests.ConnectionError("no route"))

    with pytest.raises(llm.SummarizationError) as excinfo:
        llm.summarize_articles([{"title": "t", "url": "u", "description": "d"}])

    assert "Gemini request failed" in str(excinfo.value)


def test_summarize_malformed_json_raises(monkeypatch):
    _post(monkeypatch, _Response(payload={"output_text": "not json"}))

    with pytest.raises(llm.SummarizationError):
        llm.summarize_articles([{"title": "t", "url": "u", "description": "d"}])


def test_summarize_unusable_shape_raises(monkeypatch):
    _post(monkeypatch, _Response(payload={"output_text": json.dumps({"items": "nope"})}))

    with pytest.raises(llm.SummarizationError):
        llm.summarize_articles([{"title": "t", "url": "u", "description": "d"}])


def test_summarize_legitimate_empty_items_is_allowed(monkeypatch):
    _post(monkeypatch, _Response(payload={"output_text": json.dumps({"items": []})}))

    assert llm.summarize_articles([{"title": "t", "url": "u", "description": "d"}]) == []


def test_parse_response_handles_fallback_and_bad_input():
    assert llm._parse_response({"output_text": json.dumps({"items": [ITEM]})}) == [ITEM]
    assert llm._parse_response({"steps": []}) is None
    assert llm._parse_response({"output_text": None}) is None


def test_error_message_does_not_leak_api_key(monkeypatch):
    monkeypatch.setattr(llm, "API_KEY", "super-secret-key")
    _post(monkeypatch, requests.ConnectionError("connection to server failed"))

    with pytest.raises(llm.SummarizationError) as excinfo:
        llm.summarize_articles([{"title": "t", "url": "u", "description": "d"}])

    assert "super-secret-key" not in str(excinfo.value)


def test_load_system_prompt_falls_back_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "INTERESTS_PATH", tmp_path / "missing.txt")
    assert "Summarize each article" in llm._load_system_prompt()
