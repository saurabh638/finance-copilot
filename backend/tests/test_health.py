"""Tests for the health endpoint, against a real Postgres (CODING_STANDARDS section 5)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_session


def test_health_reports_ok_and_reaches_the_database(client: TestClient) -> None:
    """The endpoint returns ok, and database=ok reflects a live query."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_failure_when_the_database_is_unreachable(app: FastAPI) -> None:
    """A failing database must surface as a 500, never a silent success."""

    def broken_session() -> Session:
        raise RuntimeError("database is down")

    app.dependency_overrides[get_session] = broken_session
    try:
        with TestClient(app, raise_server_exceptions=False) as failing_client:
            response = failing_client.get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
