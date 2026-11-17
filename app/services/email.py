"""Email delivery via Resend."""

import os

import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY", "")


def send_digest(html: str, to_email: str, subject: str = "Daily AI News Digest") -> dict:
    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEY not set")
    params = {
        "from": "onboarding@resend.dev",
        "to": [to_email],
        "subject": subject,
        "html": html,
    }
    return resend.Emails.send(params)