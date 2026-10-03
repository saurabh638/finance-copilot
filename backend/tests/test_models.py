"""The models persist against the real test database."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Session as SessionRow
from app.models import User


def test_user_and_session_round_trip() -> None:
    # A dummy hash, not a real password: this test only checks persistence.
    placeholder_hash = "$argon2id$placeholder"

    with SessionLocal() as db:
        user = User(email="owner@example.com", password_hash=placeholder_hash)
        db.add(user)
        db.flush()

        db.add(
            SessionRow(
                user_id=user.id,
                token_hash="a" * 64,
                expires_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        db.commit()

    with SessionLocal() as db:
        stored_user = db.scalar(select(User).where(User.email == "owner@example.com"))
        assert stored_user is not None
        assert stored_user.id == user.id
        assert stored_user.created_at is not None

        stored_session = db.scalar(select(SessionRow))
        assert stored_session is not None
        assert stored_session.user_id == stored_user.id
        assert stored_session.expires_at == datetime(2026, 1, 1, tzinfo=UTC)
