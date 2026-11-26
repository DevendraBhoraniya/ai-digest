"""Email delivery via Resend."""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any

import resend
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

resend.api_key = (os.getenv("RESEND_API_KEY") or "").strip()
RESEND_FROM = (os.getenv("RESEND_FROM") or "").strip() or "onboarding@resend.dev"

# Retry config for transient email send failures (network, 5xx)
EMAIL_MAX_RETRIES = 3
EMAIL_BASE_DELAY = 1.0
EMAIL_MAX_DELAY = 10.0


def _is_retryable_error(exc: Exception) -> bool:
    """Check if an exception from Resend is retryable (network/5xx)."""
    # resend raises generic Exception; check message for common transient errors
    msg = str(exc).lower()
    retryable = (
        "timeout" in msg
        or "connection" in msg
        or "502" in msg
        or "503" in msg
        or "504" in msg
        or "rate limit" in msg
        or "429" in msg
    )
    return retryable


def send_digest(html: str, to_email: str, subject: str = "Daily AI News Digest") -> dict[str, Any]:
    """Send the digest email with retry on transient failures.

    Retries only on clear transient errors (network, 5xx, rate limit) to avoid
    duplicate deliveries on ambiguous timeouts.
    """
    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEY not set")
    if not to_email:
        raise RuntimeError("DIGEST_RECIPIENT_EMAIL not set")

    params = {
        "from": RESEND_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }

    last_exc: Exception | None = None
    for attempt in range(EMAIL_MAX_RETRIES + 1):
        try:
            response = resend.Emails.send(params)
            logger.info("digest email accepted by Resend for %s", to_email)
            return response
        except Exception as exc:
            last_exc = exc
            if _is_retryable_error(exc) and attempt < EMAIL_MAX_RETRIES:
                delay = min(
                    EMAIL_BASE_DELAY * (2**attempt) + random.uniform(0, 0.5),
                    EMAIL_MAX_DELAY,
                )
                logger.warning(
                    "email send failed (%s), retrying in %.1fs (attempt %d/%d)",
                    exc,
                    delay,
                    attempt + 1,
                    EMAIL_MAX_RETRIES,
                )
                time.sleep(delay)
                continue
            logger.error("email send failed permanently: %s", exc)
            raise
    raise RuntimeError(f"email send failed after {EMAIL_MAX_RETRIES} retries") from last_exc
