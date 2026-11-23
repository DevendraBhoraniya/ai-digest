"""Create missing tables. Safe to rerun, but it never alters existing tables."""

from app.database.models import Base
from app.database.session import engine


def ensure_schema() -> None:
    """Create any missing tables (idempotent, non-destructive)."""
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    ensure_schema()
    print("tables ready")
