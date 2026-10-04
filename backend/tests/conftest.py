"""Shared pytest fixtures. The suite runs against the dedicated test database."""

import os
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models import User


def pytest_configure() -> None:
    """Point the app at the test database before any app module is imported."""
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]


@pytest.fixture
def app() -> FastAPI:
    """The FastAPI application, bound to the test database."""
    from app.main import app as application

    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A test client for the application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db() -> Iterator[Session]:
    """A database session bound to the test database."""
    from app.db import SessionLocal

    with SessionLocal() as session:
        yield session


@pytest.fixture
def user(db: Session) -> "User":
    """A persisted user, for tests that need an owner."""
    from app.services.auth import create_user

    return create_user(db, "owner@example.com", "s3cret-passphrase")


@pytest.fixture(scope="session", autouse=True)
def _test_database_schema() -> None:
    """Bring the test database schema to head once, before the suite runs."""
    from alembic.config import Config

    from alembic import command

    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def _empty_tables() -> None:
    """Start every test with the non-financial tables empty."""
    from sqlalchemy import text

    from app.db import engine

    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE sessions, users, login_failures, accounts RESTART IDENTITY CASCADE"
            )
        )
