from types import SimpleNamespace

import pytest

from app.services import email as email_service


def test_send_digest_success_returns_provider_response(monkeypatch):
    sent = []

    def fake_send(params):
        sent.append(params)
        return {"id": "email-1"}

    monkeypatch.setattr(email_service.resend, "api_key", "re_test")
    monkeypatch.setattr(email_service.resend, "Emails", SimpleNamespace(send=fake_send))

    response = email_service.send_digest("<html></html>", "reader@example.com")

    assert response == {"id": "email-1"}
    assert sent == [
        {
            "from": email_service.RESEND_FROM,
            "to": ["reader@example.com"],
            "subject": "Daily AI News Digest",
            "html": "<html></html>",
        }
    ]


def test_send_digest_propagates_provider_failure(monkeypatch):
    def failing_send(params):
        raise RuntimeError("resend unavailable")

    monkeypatch.setattr(email_service.resend, "api_key", "re_test")
    monkeypatch.setattr(email_service.resend, "Emails", SimpleNamespace(send=failing_send))

    with pytest.raises(RuntimeError, match="resend unavailable"):
        email_service.send_digest("<html></html>", "reader@example.com")


def test_send_digest_requires_api_key(monkeypatch):
    monkeypatch.setattr(email_service.resend, "api_key", "")

    with pytest.raises(RuntimeError, match="RESEND_API_KEY"):
        email_service.send_digest("<html></html>", "reader@example.com")


def test_send_digest_requires_recipient(monkeypatch):
    monkeypatch.setattr(email_service.resend, "api_key", "re_test")

    with pytest.raises(RuntimeError, match="DIGEST_RECIPIENT_EMAIL"):
        email_service.send_digest("<html></html>", "")
