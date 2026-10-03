"""Authentication: create the user, log in, log out, resolve a session.

Session tokens are random and are stored only as a SHA-256 hash, so a database
dump cannot be replayed as a login. All database access lives here; routers call
these functions rather than touching models.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.security import hash_password, verify_password
from app.models import Session as SessionRow
from app.models import User

_TOKEN_BYTES = 32


class EmailAlreadyUsedError(ValueError):
    """Raised when creating a user whose email is already registered."""


def _hash_token(raw_token: str) -> str:
    """Return the hex SHA-256 of a raw session token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_user(db: DbSession, email: str, password: str) -> User:
    """Create the user with a hashed password; the email is stored lower-cased."""
    normalised = email.strip().lower()
    if db.scalar(select(User).where(User.email == normalised)) is not None:
        raise EmailAlreadyUsedError(normalised)

    user = User(email=normalised, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    return user


def authenticate(db: DbSession, email: str, password: str) -> User | None:
    """Return the user when the email and password match, otherwise None."""
    normalised = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalised))
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: DbSession, user: User, now: datetime, ttl_days: int) -> str:
    """Create a session for the user and return the raw token (shown only once)."""
    raw_token = secrets.token_urlsafe(_TOKEN_BYTES)
    db.add(
        SessionRow(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=now + timedelta(days=ttl_days),
        )
    )
    db.commit()
    return raw_token


def resolve_session(db: DbSession, raw_token: str, now: datetime) -> User | None:
    """Return the user for a valid, unexpired token, otherwise None."""
    row = db.scalar(select(SessionRow).where(SessionRow.token_hash == _hash_token(raw_token)))
    if row is None or row.expires_at <= now:
        return None
    return db.get(User, row.user_id)


def revoke_session(db: DbSession, raw_token: str) -> None:
    """Delete the session for a token, if one exists."""
    row = db.scalar(select(SessionRow).where(SessionRow.token_hash == _hash_token(raw_token)))
    if row is not None:
        db.delete(row)
        db.commit()
