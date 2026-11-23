import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

load_dotenv()


def _normalize_database_url(url: str) -> str:
    # psycopg2 is the only PostgreSQL driver in our dependencies, so make sure
    # plain "postgresql://" URLs (Neon defaults to those) use it.
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    if url.startswith("postgresql+psycopg://"):
        return "postgresql+psycopg2://" + url[len("postgresql+psycopg://") :]
    return url


_raw_url = os.getenv("NEON_DATABASE_URL") or os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/ainews"
)
DATABASE_URL = _normalize_database_url(_raw_url)

# The digest runs as a short-lived cron process, so there is nothing to pool:
# NullPool avoids keeping a possibly-suspended Neon connection alive between runs.
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    poolclass=NullPool,
    connect_args={"connect_timeout": 10},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
