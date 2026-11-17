# AI News Aggregator — Plan (current)

## Structure
```
app/
  config.py
  runner.py
  scheduler.py
  database/ (models, session, repository, create_tables)
  scrapers/youtube.py (YouTubeScraper)
  services/ (youtube transcripts, llm, digest, email)
  prompts/interests.txt
docker/docker-compose.yml
main.py
.env / .env.example
```

## Done
- Phase 1: DB (Neon Postgres) + SQLAlchemy models + repository + create_tables.
- Phase 2: YouTube scraper (RSS, 24h filter, transcripts, OOP) + runner (scrape → persist → backfill).
- Phase 3: Digest (collect, Gemini summarize, HTML render).
- Phase 4: Email via Resend.
- Phase 5.1: Scheduler + main.py flags.

## Next
- 5.2: render.yaml for Render cron.
- Blog scraper (OpenAI/Anthropic).
- Unified articles table (optional).