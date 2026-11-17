import argparse
import os

from dotenv import load_dotenv

load_dotenv()

from app.runner import run_youtube_scrape
from app.services.digest import run_digest
from app.services.email import send_digest


def run_once():
    videos = run_youtube_scrape()
    html = run_digest(hours=24)
    to = os.getenv("DIGEST_RECIPIENT_EMAIL")
    if to:
        send_digest(html, to)
    print(f"done: {len(videos)} videos")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="run scheduler daemon")
    parser.add_argument("--run-once", action="store_true", help="run one cycle and exit")
    args = parser.parse_args()

    if args.serve:
        from app.scheduler import start_scheduler

        start_scheduler()
    else:
        run_once()


if __name__ == "__main__":
    main()