"""Email delivery via Resend."""

from __future__ import annotations

import logging
import os

import resend
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

resend.api_key = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "onboarding@resend.dev")


def send_digest(html: str, to_email: str, subject: str = "Daily AI News Digest") -> dict:
    """Send the digest email and return the provider response.

    There are deliberately no retries here: a timed-out send may already have
    been delivered, and retrying could email the reader twice. Callers record
    ``digest_sent`` only after this function returns.
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
    response = resend.Emails.send(params)
    logger.info("digest email accepted by Resend for %s", to_email)
    return response
