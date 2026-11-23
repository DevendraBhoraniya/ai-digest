# AI News Aggregator

Daily digest of new AI YouTube videos. The job scrapes a curated set of
channels, fetches transcripts, summarizes them with Gemini, and emails a
single HTML digest through Resend. It runs unattended once a day through
GitHub Actions, with no paid hosting service.

## Features

- Scrapes roughly twelve YouTube channels from their public RSS feeds.
- Looks back 48 hours so a missed run does not lose videos.
- Fetches transcripts with bounded retries and exponential backoff.
- Summarizes articles with Google Gemini and renders an HTML email.
- Sends one digest email per run through Resend.
- Records every run (start, finish, status, counts, error) in PostgreSQL.
- Reports channel-level failures instead of hiding them as empty results.
- Single process, no queues, no extra infrastructure.

## Architecture

```text
main.py --run-once
  -> app.runner.run_cycle()
       validate config
       ensure_schema()          (creates missing tables only)
       run_youtube_scrape()     (per-channel feeds + transcript backfill)
       run_digest()             (collect last 24h + Gemini summary)
       send_digest()            (Resend)
       _record_run()            (run_logs)
```

- `app/runner.py` is the single orchestration path used by both
  `main.py --run-once` and the local scheduler.
- `app/database/` holds SQLAlchemy models, sessions and repositories.
- `app/scrapers/youtube.py` fetches channel RSS feeds.
- `app/services/` holds transcript, Gemini, digest and email logic.
- `app/config.py` holds channels, timings and startup validation.

## Execution flow

1. Validate required environment variables.
2. Create any missing database tables (idempotent, non-destructive).
3. Scrape each channel. A failing channel is logged and counted; the run
   continues with the remaining channels.
4. Backfill transcripts for videos still marked `pending`.
5. Collect videos published in the last 24 hours and summarize them with Gemini.
6. Send the HTML digest to the configured recipient.
7. Write a `run_logs` row with start time, finish time, status, counts and any
   error.

## Project structure

```text
.
├── app/
│   ├── config.py
│   ├── runner.py
│   ├── scheduler.py
│   ├── database/
│   ├── scrapers/
│   └── services/
├── tests/
├── main.py
├── pyproject.toml
├── uv.lock
├── requirements.txt
└── .github/workflows/
    ├── test.yml
    └── daily-digest.yml
```

## Prerequisites

- Python 3.11 or 3.12
- [uv](https://docs.astral.sh/uv/)
- A PostgreSQL database (Neon recommended)
- A Google Gemini API key
- A Resend API key and a verified sender domain

## Local installation

```bash
git clone <repository-url>
cd ai-news-aggregator
uv sync
cp .env.example .env
# edit .env with your values
```

## uv setup

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Environment variables

Copy `.env.example` to `.env` and fill in the values. Actual variable names
used by the code:

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes* | PostgreSQL connection string |
| `NEON_DATABASE_URL` | yes* | Alternative name; wins if both are set |
| `GEMINI_API_KEY` | yes | Google Gemini API key |
| `RESEND_API_KEY` | yes | Resend API key |
| `DIGEST_RECIPIENT_EMAIL` | yes | Daily digest recipient |
| `RESEND_FROM` | no | Sender address (default `onboarding@resend.dev`) |
| `PROXY_USERNAME` | no | Webshare proxy username for transcript fetching |
| `PROXY_PASSWORD` | no | Webshare proxy password |

\* At least one of `DATABASE_URL` / `NEON_DATABASE_URL` is required.

`YOUTUBE_CHANNELS` is not an environment variable; channels are configured in
`app/config.py`.

## Neon database setup

1. Create a Neon project and database.
2. Copy the connection string.
3. Set it as `DATABASE_URL` or `NEON_DATABASE_URL`.
4. Create tables (idempotent, non-destructive):

```bash
python -m app.database.create_tables
```

`Base.metadata.create_all` only creates missing tables. It does not alter or
migrate existing tables, so changing a model requires a manual SQL migration
in production.

## Gemini API setup

1. Create a Google AI Studio API key.
2. Set `GEMINI_API_KEY`.
3. Keep the key secret; it is never logged.

## Resend setup

1. Create a Resend API key.
2. Verify a sender domain (or use the default `onboarding@resend.dev` for
   testing).
3. Set `RESEND_API_KEY` and optionally `RESEND_FROM`.
4. Set `DIGEST_RECIPIENT_EMAIL`.

## Running locally

Run a single digest cycle and exit:

```bash
python main.py --run-once
```

Exit code is `0` on success or partial success and `1` when a required stage
failed. The number of scraped videos is printed at the end.

Run the blocking daily scheduler (8:00 UTC by default):

```bash
python main.py --serve
```

## Running manually once

```bash
uv run python main.py --run-once
```

## GitHub Actions scheduling

`.github/workflows/daily-digest.yml` runs the digest once a day:

- Schedule: `30 2 * * *` (08:00 IST / 02:30 UTC).
- Manual trigger: `workflow_dispatch`.
- Command: `uv run python main.py --run-once`.
- Timeout: 30 minutes.
- Concurrency group `daily-digest` with `cancel-in-progress: false`.

GitHub Actions scheduling is not guaranteed to start at the exact scheduled
minute; runs may start a few minutes late depending on runner availability.

## Manual workflow execution

1. Open the repository on GitHub.
2. Go to **Actions**.
3. Select **Daily Digest**.
4. Click **Run workflow**.
5. Confirm the run starts and completes.

## GitHub Secrets configuration

Configure secrets at:

GitHub Repository → Settings → Secrets and variables → Actions → New repository secret.

Required secrets:

- `DATABASE_URL` or `NEON_DATABASE_URL`
- `GEMINI_API_KEY`
- `RESEND_API_KEY`
- `DIGEST_RECIPIENT_EMAIL`

Optional secrets:

- `RESEND_FROM`
- `PROXY_USERNAME`
- `PROXY_PASSWORD`

Never commit secrets. Never print secret values in logs.

## CI workflow

`.github/workflows/test.yml` runs on pushes and pull requests to `master`:

1. Install uv.
2. `uv sync --frozen`
3. `uv lock --check`
4. `uv run ruff check .`
5. `uv run ruff format --check .`
6. `uv run python -m compileall -q app main.py`
7. `uv run pytest`

No production secrets are required by CI.

Note: this repository has no configured remote, so the default branch could
not be verified from git metadata. The workflow targets `master`, the branch
present in this checkout. Update the filters if your GitHub default branch
differs.

## Running tests

```bash
uv run pytest
```

Tests use in-memory SQLite and mocked network boundaries. They do not send
real emails or call paid APIs.

## Linting and formatting

```bash
uv run ruff check .
uv run ruff format --check .
```

## Failure handling

Each run writes one row to `run_logs`:

- `started_at`, `finished_at` (timezone-aware UTC)
- `status`: `success`, `partial` or `failed`
- `videos_scraped`, `transcripts_fetched`, `channels_failed`
- `digest_sent`
- `error` (exception type and message; no secrets)

A run is `partial` when some channels failed but the digest was still sent.
A run is `failed` when a required stage (all channels, digest, email) failed;
in that case no misleading "No new articles today" email is sent after a
Gemini failure.

Network timeouts, bounded retries, and PostgreSQL connection errors are
handled per run. Database sessions are closed via context managers. Failed
Gemini requests raise `SummarizationError` and prevent email delivery.

## Troubleshooting

- **ImportError: tenacity / requests**: regenerate dependencies with
  `uv sync --frozen` and reinstall from `requirements.txt`.
- **psycopg not found**: the database URL must resolve to the psycopg2 driver.
  `app/database/session.py` rewrites plain `postgresql://` URLs automatically.
- **No videos scraped**: check the channel IDs in `app/config.py` and network
  access to `youtube.com/feeds`.
- **Empty transcripts**: some videos have no captions; they are marked
  `unavailable` and skipped.
- **Gemini errors**: the run is marked failed and no digest is sent. Check
  `GEMINI_API_KEY` and the Gemini status.
- **Email not sent**: check `RESEND_API_KEY`, `RESEND_FROM` (verified domain)
  and `DIGEST_RECIPIENT_EMAIL`.

## Security notes

- Secrets are never committed. `.env`, `.venv`, caches and generated temp
  files are ignored by `.gitignore`.
- API keys and database credentials come from environment variables only.
- Error messages and logs do not include API keys or database passwords.
- Use a least-privilege database user for the application.
- GitHub Actions uses read-only repository permissions.
