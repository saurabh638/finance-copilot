"""CLI tests for the create-user command, against the real test database."""

import pytest
from sqlalchemy import func, select

from app import cli
from app.config import get_settings
from app.db import SessionLocal
from app.models import User

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"


def test_create_user_command_creates_the_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_EMAIL", EMAIL)
    monkeypatch.setenv("ADMIN_PASSWORD", PASSPHRASE)
    get_settings.cache_clear()

    try:
        exit_code = cli.main(["create-user"])
    finally:
        get_settings.cache_clear()

    assert exit_code == 0
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == EMAIL))
    assert user is not None


def test_create_user_command_needs_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    get_settings.cache_clear()

    try:
        exit_code = cli.main(["create-user"])
    finally:
        get_settings.cache_clear()

    assert exit_code == 1


def test_create_user_command_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_EMAIL", EMAIL)
    monkeypatch.setenv("ADMIN_PASSWORD", PASSPHRASE)
    get_settings.cache_clear()

    try:
        first = cli.main(["create-user"])
        second = cli.main(["create-user"])
    finally:
        get_settings.cache_clear()

    assert first == 0
    assert second == 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
