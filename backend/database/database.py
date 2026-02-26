"""SQLite database engine and session factory for ontology persistence."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Project root = 3 levels up from this file (database.py → database/ → backend/ → project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DB_DIR = _PROJECT_ROOT / "data"
_DB_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DB_DIR / "ontology.db"

DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(  # pylint: disable=invalid-name
    bind=engine, autoflush=False, expire_on_commit=False,
)


def get_db():
    """Yield a DB session, closing it automatically."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
