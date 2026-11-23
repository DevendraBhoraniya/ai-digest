"""Static configuration and startup validation for the daily digest job."""

import os

# Channels are public YouTube channel IDs, not secrets.
YOUTUBE_CHANNELS = [
    # original channels
    "UCsBjURrPoezykLs9EqgamOA",  # Fireship
    "UCn8ujwUInbJkBhffxqAPBVQ",  # Dave Ebbelaar
    "UCawZsQWqfGSbCI5yjkdVkTA",  # Matthew Berman
    "UC8wZnXYK_CGKlBcZp-GxYPA",  # NeuralNine
    "UCS261lQDXjMvc8Jck-2CQEg",  # Gyan Therapy
    # AI development and engineering
    "UC8butISFwT-Wl7EV0hUK0BQ",  # freeCodeCamp
    "UCXUPKJO5MZQN11PqgIvyuvQ",  # Andrej Karpathy
    "UCZHmQk67mSJgfCCTn7xBfew",  # Yannic Kilcher
    # AI news and industry
    "UCNJ1Ymd5yFuUPtn21xtRbbw",  # AI Explained
    "UChpleBmo18P08aKCIgti38g",  # Matt Wolfe
    "UCqcbQf6yw5KzRoDDcZ_wBSw",  # Wes Roth
    "UCbfYPyITQ-7l4upoX8nvctg",  # Two Minute Papers
]

LOOKBACK_HOURS = 48
DIGEST_HOURS = 24
HTTP_TIMEOUT_SECONDS = 15
TRANSCRIPT_MAX_ATTEMPTS = 3
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# Either name may hold the database URL; NEON_DATABASE_URL wins when both are set.
DATABASE_URL_VARS = ("NEON_DATABASE_URL", "DATABASE_URL")
REQUIRED_ENV_VARS = ("GEMINI_API_KEY", "RESEND_API_KEY", "DIGEST_RECIPIENT_EMAIL")


class ConfigError(RuntimeError):
    """Raised when required environment configuration is missing."""


def validate_config() -> None:
    """Raise ConfigError listing every missing variable, or return None."""
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name, "").strip()]
    if not any(os.getenv(name, "").strip() for name in DATABASE_URL_VARS):
        missing.append(f"one of {'/'.join(DATABASE_URL_VARS)}")
    if missing:
        raise ConfigError("Missing required environment variable(s): " + ", ".join(missing))
