"""Tests for app.services.interest_rates, against the real test database."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models import Account, AccountType, CaptureMode, InterestRate, RateFrequency, User
from app.schemas.account import AccountCreate
from app.schemas.interest_rate import InterestRateCreate
from app.services.accounts import AccountNotFoundError, create_account, soft_delete_account
from app.services.auth import create_user
from app.services.interest_rates import (
    DuplicateRateError,
    RateNotFoundError,
    create_rate,
    get_rate,
    list_rates,
    soft_delete_rate,
)

SAVINGS: dict[str, object] = {
    "name": "SBI",
    "type": AccountType.SAVINGS,
    "capture_mode": CaptureMode.STATEMENT_IMPORT,
    "opening_balance_paise": 1_23_456_78,
    "opening_date": date(2026, 4, 1),
}

FIRST_RATE: dict[str, object] = {
    "rate": Decimal("7.1"),
    "from_date": date(2026, 4, 1),
    "frequency": RateFrequency.QUARTERLY,
    "note": "before the repo cut",
}


def _account(db: Session, user: User, **overrides: object) -> Account:
    return create_account(db, user.id, AccountCreate.model_validate({**SAVINGS, **overrides}))


def _rate(db: Session, user: User, account: Account, **overrides: object) -> InterestRate:
    payload = InterestRateCreate.model_validate({**FIRST_RATE, **overrides})
    return create_rate(db, user.id, account.id, payload)


def test_create_keeps_the_rate_exact_and_never_a_float(db: Session, user: User) -> None:
    account = _account(db, user)

    rate = _rate(db, user, account)

    assert rate.rate == Decimal("7.1000")
    assert isinstance(rate.rate, Decimal)
    assert rate.deleted_at is None
    assert rate.note == "before the repo cut"


def test_a_new_rate_leaves_the_earlier_record_untouched(db: Session, user: User) -> None:
    account = _account(db, user)
    earlier = _rate(db, user, account)

    later = _rate(db, user, account, rate=Decimal("6.5"), from_date=date(2026, 7, 1))

    db.refresh(earlier)
    assert earlier.rate == Decimal("7.1000")
    assert earlier.from_date == date(2026, 4, 1)
    assert earlier.id != later.id
    assert len(list_rates(db, user.id, account.id, 50, 0)) == 2


def test_history_is_newest_first(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account)
    _rate(db, user, account, rate=Decimal("6.5"), from_date=date(2026, 7, 1))

    from_dates = [rate.from_date for rate in list_rates(db, user.id, account.id, 50, 0)]

    assert from_dates == [date(2026, 7, 1), date(2026, 4, 1)]


def test_the_same_start_date_twice_is_rejected(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account)

    with pytest.raises(DuplicateRateError):
        _rate(db, user, account, rate=Decimal("6.5"))


def test_the_same_date_can_be_used_again_after_a_soft_delete(db: Session, user: User) -> None:
    account = _account(db, user)
    mistaken = _rate(db, user, account)
    soft_delete_rate(db, user.id, account.id, mistaken.id)

    corrected = _rate(db, user, account, rate=Decimal("6.5"))

    assert corrected.rate == Decimal("6.5000")
    assert [rate.rate for rate in list_rates(db, user.id, account.id, 50, 0)] == [Decimal("6.5000")]


def test_soft_delete_hides_the_rate_but_keeps_the_row(db: Session, user: User) -> None:
    account = _account(db, user)
    rate = _rate(db, user, account)

    soft_delete_rate(db, user.id, account.id, rate.id)

    assert list_rates(db, user.id, account.id, 50, 0) == []
    kept = db.get(InterestRate, rate.id)
    assert kept is not None
    assert kept.deleted_at is not None
    assert kept.rate == Decimal("7.1000")


def test_rates_are_scoped_to_their_own_account(db: Session, user: User) -> None:
    first = _account(db, user, name="SBI")
    second = _account(db, user, name="HDFC")
    _rate(db, user, first)
    _rate(db, user, second, rate=Decimal("3"))

    assert [rate.rate for rate in list_rates(db, user.id, first.id, 50, 0)] == [Decimal("7.1000")]
    assert [rate.rate for rate in list_rates(db, user.id, second.id, 50, 0)] == [Decimal("3.0000")]


def test_a_rate_id_from_another_account_is_not_found(db: Session, user: User) -> None:
    first = _account(db, user, name="SBI")
    second = _account(db, user, name="HDFC")
    rate = _rate(db, user, first)

    with pytest.raises(RateNotFoundError):
        get_rate(db, user.id, second.id, rate.id)


def test_a_rate_on_an_unknown_account_is_rejected(db: Session, user: User) -> None:
    with pytest.raises(AccountNotFoundError):
        create_rate(db, user.id, 999, InterestRateCreate.model_validate(FIRST_RATE))


def test_a_rate_on_a_soft_deleted_account_is_rejected(db: Session, user: User) -> None:
    account = _account(db, user)
    soft_delete_account(db, user.id, account.id)

    with pytest.raises(AccountNotFoundError):
        _rate(db, user, account)


def test_another_users_account_is_not_found(db: Session, user: User) -> None:
    account = _account(db, user)
    rate = _rate(db, user, account)
    other = create_user(db, "other@example.com", "s3cret-passphrase")

    with pytest.raises(AccountNotFoundError):
        get_rate(db, other.id, account.id, rate.id)


def test_an_unknown_rate_id_is_not_found(db: Session, user: User) -> None:
    account = _account(db, user)

    with pytest.raises(RateNotFoundError):
        get_rate(db, user.id, account.id, 999)
    with pytest.raises(RateNotFoundError):
        soft_delete_rate(db, user.id, account.id, 999)


def test_a_pot_can_carry_its_own_rate(db: Session, user: User) -> None:
    parent = _account(db, user, name="SBI")
    pot = _account(db, user, name="Goa trip", type=AccountType.POT, parent_id=parent.id)

    rate = _rate(db, user, pot, rate=Decimal("6"), frequency=RateFrequency.DAILY)

    assert rate.account_id == pot.id
    assert rate.frequency is RateFrequency.DAILY
