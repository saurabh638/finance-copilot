"""Tests for the database-backed login rate limiter."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import LoginFailure
from app.services.login_attempts import clear_failures, count_recent_failures, record_failure

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
EMAIL = "owner@example.com"
WINDOW_MINUTES = 15


def test_no_failures_initially(db: Session) -> None:
    assert count_recent_failures(db, EMAIL, NOW, WINDOW_MINUTES) == 0


def test_record_failure_is_counted(db: Session) -> None:
    record_failure(db, EMAIL, NOW, WINDOW_MINUTES)

    assert count_recent_failures(db, EMAIL, NOW, WINDOW_MINUTES) == 1


def test_failures_are_counted_per_email(db: Session) -> None:
    record_failure(db, EMAIL, NOW, WINDOW_MINUTES)

    assert count_recent_failures(db, "other@example.com", NOW, WINDOW_MINUTES) == 0


def test_failures_outside_the_window_are_not_counted(db: Session) -> None:
    record_failure(db, EMAIL, NOW, WINDOW_MINUTES)
    later = NOW + timedelta(minutes=WINDOW_MINUTES + 1)

    assert count_recent_failures(db, EMAIL, later, WINDOW_MINUTES) == 0


def test_recording_prunes_expired_rows(db: Session) -> None:
    record_failure(db, EMAIL, NOW, WINDOW_MINUTES)
    later = NOW + timedelta(minutes=WINDOW_MINUTES + 1)

    record_failure(db, EMAIL, later, WINDOW_MINUTES)

    assert count_recent_failures(db, EMAIL, later, WINDOW_MINUTES) == 1
    assert db.scalar(select(func.count()).select_from(LoginFailure)) == 1


def test_clear_failures_removes_them(db: Session) -> None:
    record_failure(db, EMAIL, NOW, WINDOW_MINUTES)

    clear_failures(db, EMAIL)

    assert count_recent_failures(db, EMAIL, NOW, WINDOW_MINUTES) == 0
