"""
SQLite persistence for Reviewer-Lens (users + review jobs).

Replaces the earlier in-memory `JOBS` dict in app.py: jobs now survive a
backend restart and are scoped per faculty account, which is what makes
the dashboard / report-history feature possible. SQLite is deliberately
chosen over a client-server DB — this is a single-process demo/department
deployment, and swapping the SQLALCHEMY_DATABASE_URL below is enough to
move to Postgres later without touching any calling code.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

import config

SQLALCHEMY_DATABASE_URL = f"sqlite:///{config.DB_PATH}"

# check_same_thread=False: FastAPI's background tasks and request handlers
# can run on different threads than the one that created the engine;
# SQLite is fine with this as long as each thread uses its own Session
# (which SessionLocal() gives us) rather than sharing one connection.
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — one session per request, always closed after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables that don't exist yet. Safe to call on every startup."""
    import models_db  # noqa: F401 — import registers the models on Base

    Base.metadata.create_all(bind=engine)
