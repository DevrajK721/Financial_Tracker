from __future__ import annotations

# This file is the database setup for the whole project.
# It decides where the SQLite database lives and gives other files
# a safe way to open, use, commit, rollback, and close database sessions.

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "processed" / "finances.db"
DATABASE_URL = f"sqlite:///{DB_PATH}" # The database URL for SQLAlchemy to connect to the SQLite database.

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# The engine is the SQLAlchemy connection setup. It says what database to connect to. 
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
) # Creates new SQLAlchemy sessions for interacting with the database. 

# This is the parent class for database models. 
class Base(DeclarativeBase):
    """All database model classes inherit from this."""


def create_tables() -> None:
    """Create all database tables that inherit from Base."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Open a database session, commit on success, rollback on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
