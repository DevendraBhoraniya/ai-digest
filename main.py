"""Entry point for the daily YouTube digest."""

from __future__ import annotations

import argparse
import logging
import sys

from app.config import LOG_FORMAT
from app.runner import CycleResult, run_cycle

logger = logging.getLogger(__name__)


def run_once() -> CycleResult:
    """Run one digest cycle and print the number of scraped videos."""
    result = run_cycle()
    if result.status == "failed":
        logger.error("run failed: %s", result.error)
    else:
        print(
            f"scraped {result.videos_scraped} videos, "
            f"transcripts {result.transcripts_fetched}, "
            f"email sent={result.digest_sent}"
        )
    return result


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns a process exit code."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="run scheduler daemon")
    parser.add_argument("--run-once", action="store_true", help="run one cycle and exit (default)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    if args.serve:
        from app.scheduler import start_scheduler

        start_scheduler()
        return 0

    return 0 if run_once().ok else 1


if __name__ == "__main__":
    sys.exit(main())
