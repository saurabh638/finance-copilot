"""Tests for app.services.accounts, against the real test database."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.models import Account, AccountType, CaptureMode, User
from app.schemas.account import AccountCreate, AccountUpdate
from app.services.accounts import (
    AccountNotFoundError,
    InvalidAccountError,
    create_account,
    get_account,
    list_accounts,
    soft_delete_account,
    update_account,
)

SAVINGS: dict[str, object] = {
    "name": "SBI",
    "type": AccountType.SAVINGS,
    "capture_mode": CaptureMode.STATEMENT_IMPORT,
    "opening_balance_paise": 1_23_456_78,
    "opening_date": date(2026, 4, 1),
}


def _create(db: Session, user: User, **overrides: object) -> Account:
    payload = {**SAVINGS, **overrides}
    return create_account(db, user.id, AccountCreate.model_validate(payload))


def test_create_account_keeps_the_balance_in_exact_paise(db: Session, user: User) -> None:
    account = _create(db, user)

    assert account.opening_balance_paise == 1_23_456_78
    assert isinstance(account.opening_balance_paise, int)
    assert account.deleted_at is None
    assert account.is_active is True


def test_list_accounts_returns_only_live_accounts_for_the_user(db: Session, user: User) -> None:
    kept = _create(db, user, name="SBI")
    removed = _create(db, user, name="Old")
    soft_delete_account(db, user.id, removed.id)

    accounts = list_accounts(db, user.id, limit=50, offset=0)

    assert [account.id for account in accounts] == [kept.id]


def test_get_account_hides_a_soft_deleted_account(db: Session, user: User) -> None:
    account = _create(db, user)
    soft_delete_account(db, user.id, account.id)

    with pytest.raises(AccountNotFoundError):
        get_account(db, user.id, account.id)


def test_get_account_raises_for_an_unknown_id(db: Session, user: User) -> None:
    with pytest.raises(AccountNotFoundError):
        get_account(db, user.id, 999_999)


def test_update_account_applies_the_given_fields(db: Session, user: User) -> None:
    account = _create(db, user)

    updated = update_account(
        db,
        user.id,
        account.id,
        AccountUpdate(name="SBI Savings", purpose="Emergency fund"),
    )

    assert updated.name == "SBI Savings"
    assert updated.purpose == "Emergency fund"
    assert updated.type is AccountType.SAVINGS


def test_update_account_rejects_card_days_on_a_savings_account(db: Session, user: User) -> None:
    account = _create(db, user)

    with pytest.raises(InvalidAccountError):
        update_account(db, user.id, account.id, AccountUpdate(statement_day=5))


def test_a_pot_needs_an_existing_parent(db: Session, user: User) -> None:
    with pytest.raises(InvalidAccountError):
        _create(
            db,
            user,
            name="Goa",
            type=AccountType.POT,
            capture_mode=CaptureMode.MANUAL_ONLY,
            parent_id=999_999,
        )


def test_a_pot_cannot_hang_under_another_pot(db: Session, user: User) -> None:
    parent = _create(db, user)
    pot = _create(
        db,
        user,
        name="Goa",
        type=AccountType.POT,
        capture_mode=CaptureMode.MANUAL_ONLY,
        parent_id=parent.id,
    )

    with pytest.raises(InvalidAccountError):
        _create(
            db,
            user,
            name="Nested",
            type=AccountType.POT,
            capture_mode=CaptureMode.MANUAL_ONLY,
            parent_id=pot.id,
        )


def test_soft_delete_keeps_the_row(db: Session, user: User) -> None:
    account = _create(db, user)

    soft_delete_account(db, user.id, account.id)

    stored = db.get(Account, account.id)
    assert stored is not None
    assert stored.deleted_at is not None
