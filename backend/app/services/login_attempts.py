"""Login rate limiting, backed by the database.

Failed attempts are recorded per email. Once too many land inside the window the
login endpoint answers 429 until the window passes. Rows older than the window
are deleted as new failures arrive, so the table stays small. Keeping this in
Postgres avoids process-global state and survives restarts and extra workers.
"""

from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DbSession

from app.models import LoginFailure


def _normalise(email: str) -> str:
    """Match the lower-cased email used everywhere else."""
    return email.strip().lower()


def count_recent_failures(
    db: DbSession,
    email: str,
    now: datetime,
    window_minutes: int,
) -> int:
    """Return how many failures for this email fall inside the window."""
    cutoff = now - timedelta(minutes=window_minutes)
    statement = (
        select(func.count())
        .select_from(LoginFailure)
        .where(LoginFailure.email == _normalise(email), LoginFailure.attempted_at >= cutoff)
    )
    return db.scalar(statement) or 0


def record_failure(db: DbSession, email: str, now: datetime, window_minutes: int) -> None:
    """Record a failed attempt, pruning this email's expired rows."""
    normalised = _normalise(email)
    cutoff = now - timedelta(minutes=window_minutes)
    db.execute(
        delete(LoginFailure).where(
            LoginFailure.email == normalised,
            LoginFailure.attempted_at < cutoff,
        )
    )
    db.add(LoginFailure(email=normalised, attempted_at=now))
    db.commit()


def clear_failures(db: DbSession, email: str) -> None:
    """Drop this email's failures, e.g. after a successful login."""
    db.execute(delete(LoginFailure).where(LoginFailure.email == _normalise(email)))
    db.commit()
