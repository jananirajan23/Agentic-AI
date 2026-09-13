"""
Shared pytest setup.

- Puts backend/ on sys.path so `import config`, `import agents.x`, etc.
  work the same way they do when uvicorn runs from backend/.
- Forces a throwaway SQLite file (REVIEWERLENS_DB_PATH) instead of the
  real dev database, and forces GROQ_API_KEY empty, BEFORE any
  application module is imported — this keeps the suite fast,
  deterministic, and free of real network/LLM calls, matching the
  project's documented validation approach (README "Validation
  performed": pipeline runs end-to-end with LLM-dependent scores
  returning 0 + an explanatory flag rather than crashing when no key is
  configured). Tests that specifically want to exercise the Groq call
  path do so with mocks (see test_literature_survey_agent.py etc.),
  never real API calls.
"""

import os
import sys
import tempfile

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ["GROQ_API_KEY"] = ""
os.environ["REVIEWERLENS_DB_PATH"] = os.path.join(tempfile.gettempdir(), "reviewerlens_test.db")

# Drop any leftover test DB from a previous run so tests start clean.
try:
    os.remove(os.environ["REVIEWERLENS_DB_PATH"])
except OSError:
    pass

import pytest  # noqa: E402


@pytest.fixture()
def client():
    """A FastAPI TestClient wired to the throwaway test DB, with a fresh
    schema for every test (so tests don't leak state into each other)."""
    import database

    database.Base.metadata.drop_all(bind=database.engine)
    database.init_db()

    from fastapi.testclient import TestClient

    import app as app_module

    with TestClient(app_module.app) as c:
        yield c

    database.Base.metadata.drop_all(bind=database.engine)


@pytest.fixture()
def auth_headers(client):
    """Registers a throwaway faculty account and returns Bearer headers."""
    resp = client.post(
        "/api/auth/register",
        json={"name": "Dr. Reviewer", "email": "reviewer@example.edu", "password": "s3curePass"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
