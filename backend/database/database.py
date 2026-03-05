"""SQLite database engine and session factory for ontology persistence."""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    _PROJECT_ROOT = Path(__file__).resolve().parents[2]
    _DB_DIR = _PROJECT_ROOT / "data"
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    _DB_PATH = _DB_DIR / "ontology.db"
    DATABASE_URL = f"sqlite:///{_DB_PATH}"

_engine_kwargs = {"echo": False}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)

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
