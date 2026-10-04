"""Tests for app.services.seeding, against the real test database."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.money import InvalidMoneyError
from app.models import Account, AccountType, CaptureMode, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account, list_accounts
from app.services.seeding import (
    DEMO_PURPOSE,
    DEMO_SUFFIX,
    SEED_ACCOUNTS,
    SeedAccount,
    SeedEntry,
    apply,
    demo_entries,
    name_for,
    parse_balance,
    parse_opening_date,
    remove_demo,
)

# Deliberately invented numbers, including zero and a negative card balance.
BALANCES = [10_000_000, 5_000_050, -1_234_567, 250_025, 10_000, 0]
DATES = [
    date(2026, 4, 1),
    date(2026, 4, 1),
    date(2026, 4, 1),
    date(2026, 4, 1),
    date(2026, 4, 1),
    date(2026, 5, 15),
]


def _entries() -> list[SeedEntry]:
    return [
        SeedEntry(account, balance, when)
        for account, balance, when in zip(SEED_ACCOUNTS, BALANCES, DATES, strict=True)
    ]


def _live(db: Session, user: User) -> list[Account]:
    return list_accounts(db, user.id, 50, 0)


def test_the_six_accounts_are_the_ones_the_milestone_lists() -> None:
    expected = [
        ("SBI", AccountType.SAVINGS, CaptureMode.STATEMENT_IMPORT),
        ("Central Bank", AccountType.SAVINGS, CaptureMode.STATEMENT_IMPORT),
        ("SBI Credit Card", AccountType.CREDIT_CARD, CaptureMode.STATEMENT_IMPORT),
        ("slice", AccountType.SAVINGS, CaptureMode.STATEMENT_IMPORT),
        ("Indian Bank", AccountType.SAVINGS, CaptureMode.MANUAL_ONLY),
        ("Cash", AccountType.CASH, CaptureMode.MANUAL_ONLY),
    ]

    assert [(entry.name, entry.type, entry.capture_mode) for entry in SEED_ACCOUNTS] == expected


def test_finding_them_creates_each_one_with_the_numbers_given(db: Session, user: User) -> None:
    result = apply(db, user.id, _entries())

    assert result.skipped == []
    assert result.created == [entry.name for entry in SEED_ACCOUNTS]
    stored = {account.name: account for account in _live(db, user)}
    assert stored["SBI"].opening_balance_paise == 10_000_000
    assert stored["Central Bank"].opening_balance_paise == 5_000_050
    assert stored["SBI Credit Card"].opening_balance_paise == -1_234_567
    assert stored["Cash"].opening_balance_paise == 0
    assert stored["Cash"].opening_date == date(2026, 5, 15)
    assert stored["Indian Bank"].capture_mode is CaptureMode.MANUAL_ONLY


def test_running_it_twice_creates_nothing_the_second_time(db: Session, user: User) -> None:
    apply(db, user.id, _entries())

    second = apply(db, user.id, _entries())

    assert second.created == []
    assert second.skipped == [entry.name for entry in SEED_ACCOUNTS]
    assert len(_live(db, user)) == 6


def test_it_never_overwrites_an_account_that_already_exists(db: Session, user: User) -> None:
    kept = create_account(
        db,
        user.id,
        AccountCreate(
            name="SBI",
            type=AccountType.SAVINGS,
            capture_mode=CaptureMode.MANUAL_ONLY,
            opening_balance_paise=999,
            opening_date=date(2026, 1, 1),
        ),
    )

    result = apply(db, user.id, _entries())

    assert "SBI" in result.skipped
    db.refresh(kept)
    assert kept.opening_balance_paise == 999
    assert kept.opening_date == date(2026, 1, 1)


def test_the_placeholder_run_marks_everything_it_creates(db: Session, user: User) -> None:
    result = apply(db, user.id, demo_entries(), demo=True)

    assert result.created == [f"{account.name}{DEMO_SUFFIX}" for account in SEED_ACCOUNTS]
    stored = _live(db, user)
    assert all(account.name.endswith(DEMO_SUFFIX) for account in stored)
    assert all(account.purpose == DEMO_PURPOSE for account in stored)
    assert name_for(SEED_ACCOUNTS[0], demo=False) == "SBI"


def test_removing_placeholders_leaves_a_real_account_untouched(db: Session, user: User) -> None:
    real = create_account(
        db,
        user.id,
        AccountCreate(
            name="SBI",
            type=AccountType.SAVINGS,
            capture_mode=CaptureMode.STATEMENT_IMPORT,
            opening_balance_paise=1,
            opening_date=date(2026, 1, 1),
        ),
    )
    apply(db, user.id, demo_entries(), demo=True)

    removed = remove_demo(db, user.id)

    assert len(removed) == 6
    live = _live(db, user)
    assert [account.name for account in live] == ["SBI"]
    kept = db.get(Account, real.id)
    assert kept is not None
    assert kept.deleted_at is None


def test_removing_placeholders_twice_removes_nothing_the_second_time(
    db: Session, user: User
) -> None:
    apply(db, user.id, demo_entries(), demo=True)
    remove_demo(db, user.id)

    assert remove_demo(db, user.id) == []
    assert _live(db, user) == []


def test_a_placeholder_account_carries_the_marker_once(db: Session, user: User) -> None:
    apply(db, user.id, demo_entries(), demo=True)

    second = apply(db, user.id, demo_entries(), demo=True)

    assert second.created == []
    assert len(_live(db, user)) == 6


def test_a_typed_balance_is_read_by_the_one_money_parser() -> None:
    assert parse_balance("1,23,456.78") == 12_345_678
    assert parse_balance("₹500") == 50_000
    assert parse_balance("-12,345.67") == -1_234_567
    assert parse_balance("0") == 0

    with pytest.raises(InvalidMoneyError):
        parse_balance("10.005")


def test_a_typed_date_must_be_a_real_date() -> None:
    assert parse_opening_date("2026-04-01") == date(2026, 4, 1)
    assert parse_opening_date(" 2026-04-01 ") == date(2026, 4, 1)

    with pytest.raises(ValueError, match="2026-04-01"):
        parse_opening_date("01/04/2026")


def test_the_seed_list_has_no_duplicate_names() -> None:
    names = [account.name for account in SEED_ACCOUNTS]

    assert len(names) == len(set(names))


def test_a_seed_account_is_named_and_typed() -> None:
    account = SeedAccount("SBI", AccountType.SAVINGS, CaptureMode.STATEMENT_IMPORT)

    assert account.name == "SBI"
    assert account.type is AccountType.SAVINGS
