"""Interest-rate business logic and database access.

A rate change appends a record; nothing here updates a rate in place, so the
history of what a provider paid, and from when, is never rewritten. Ownership
is the account's: every function starts by resolving the account through
`get_account`, so another user's account is simply not found.
"""

from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session as DbSession

from app.models import InterestRate
from app.schemas.interest_rate import InterestRateCreate
from app.services.accounts import get_account


class RateNotFoundError(LookupError):
    """Raised when a rate does not exist for the account, or is soft-deleted."""


class DuplicateRateError(ValueError):
    """Raised when the account already has a live rate starting on that date."""


def _live_rates(account_id: int) -> Select[InterestRate]:
    """The one shared filter: soft-deleted rates are never returned."""
    return select(InterestRate).where(
        InterestRate.account_id == account_id,
        InterestRate.deleted_at.is_(None),
    )


def list_rates(
    db: DbSession,
    user_id: int,
    account_id: int,
    limit: int,
    offset: int,
) -> list[InterestRate]:
    """Return the account's live rates, newest first, paginated."""
    get_account(db, user_id, account_id)
    statement = (
        _live_rates(account_id)
        .order_by(InterestRate.from_date.desc(), InterestRate.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement))


def get_rate(db: DbSession, user_id: int, account_id: int, rate_id: int) -> InterestRate:
    """Return one live rate of this account, or raise RateNotFoundError."""
    get_account(db, user_id, account_id)
    rate = db.scalars(_live_rates(account_id).where(InterestRate.id == rate_id)).first()
    if rate is None:
        raise RateNotFoundError(rate_id)
    return rate


def create_rate(
    db: DbSession,
    user_id: int,
    account_id: int,
    data: InterestRateCreate,
) -> InterestRate:
    """Record a new rate. The older records are left exactly as they were."""
    get_account(db, user_id, account_id)
    _reject_duplicate_start_date(db, account_id, data)

    rate = InterestRate(
        account_id=account_id,
        rate=data.rate,
        from_date=data.from_date,
        frequency=data.frequency,
        note=data.note,
    )
    db.add(rate)
    db.commit()
    return rate


def soft_delete_rate(db: DbSession, user_id: int, account_id: int, rate_id: int) -> None:
    """Soft-delete a rate; the row and its history are kept."""
    rate = get_rate(db, user_id, account_id, rate_id)
    rate.deleted_at = datetime.now(UTC)
    db.commit()


def _reject_duplicate_start_date(
    db: DbSession,
    account_id: int,
    data: InterestRateCreate,
) -> None:
    """One live rate per start date; a mistaken record is deleted, not overwritten."""
    existing = db.scalars(
        _live_rates(account_id).where(InterestRate.from_date == data.from_date)
    ).first()
    if existing is not None:
        raise DuplicateRateError(f"a rate from {data.from_date} already exists")
