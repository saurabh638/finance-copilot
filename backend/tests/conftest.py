"""Shared pytest fixtures. The suite runs against the dedicated test database."""

import os
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


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
