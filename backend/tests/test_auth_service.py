"""Tests for app.services.auth, against the real test database."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import Session as SessionRow
from app.services.auth import (
    EmailAlreadyUsedError,
    authenticate,
    create_session,
    create_user,
    resolve_session,
    revoke_session,
)

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
PASSPHRASE = "s3cret-passphrase"


def test_create_user_stores_a_hash_not_the_password(db: Session) -> None:
    user = create_user(db, " Owner@Example.com ", PASSPHRASE)

    assert user.email == "owner@example.com"
    assert user.password_hash != PASSPHRASE
    assert verify_password(PASSPHRASE, user.password_hash)


def test_create_user_rejects_a_duplicate_email(db: Session) -> None:
    create_user(db, "owner@example.com", PASSPHRASE)

    with pytest.raises(EmailAlreadyUsedError):
        create_user(db, "owner@example.com", "another-passphrase")


def test_authenticate_accepts_the_right_password(db: Session) -> None:
    created = create_user(db, "owner@example.com", PASSPHRASE)

    found = authenticate(db, "owner@example.com", PASSPHRASE)

    assert found is not None
    assert found.id == created.id


def test_authenticate_rejects_a_wrong_password(db: Session) -> None:
    create_user(db, "owner@example.com", PASSPHRASE)

    assert authenticate(db, "owner@example.com", "not-the-passphrase") is None


def test_authenticate_rejects_an_unknown_email(db: Session) -> None:
    assert authenticate(db, "nobody@example.com", PASSPHRASE) is None


def test_create_session_stores_only_the_token_hash(db: Session) -> None:
    user = create_user(db, "owner@example.com", PASSPHRASE)

    raw_token = create_session(db, user, NOW, ttl_days=30)

    assert len(raw_token) > 20
    stored = db.scalar(select(SessionRow))
    assert stored is not None
    assert stored.token_hash != raw_token
    assert stored.expires_at == NOW + timedelta(days=30)


def test_resolve_session_returns_the_user_for_a_valid_token(db: Session) -> None:
    user = create_user(db, "owner@example.com", PASSPHRASE)
    raw_token = create_session(db, user, NOW, ttl_days=30)

    resolved = resolve_session(db, raw_token, NOW + timedelta(days=1))

    assert resolved is not None
    assert resolved.id == user.id


def test_resolve_session_rejects_an_expired_token(db: Session) -> None:
    user = create_user(db, "owner@example.com", PASSPHRASE)
    raw_token = create_session(db, user, NOW, ttl_days=1)

    assert resolve_session(db, raw_token, NOW + timedelta(days=2)) is None


def test_resolve_session_rejects_an_unknown_token(db: Session) -> None:
    assert resolve_session(db, "not-a-real-token", NOW) is None


def test_revoke_session_invalidates_the_token(db: Session) -> None:
    user = create_user(db, "owner@example.com", PASSPHRASE)
    raw_token = create_session(db, user, NOW, ttl_days=30)

    revoke_session(db, raw_token)

    assert resolve_session(db, raw_token, NOW) is None
