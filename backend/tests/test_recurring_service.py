"""Tests for app.services.recurring, against the real test database.

The promises being checked are the ones that involve money and dates: an item is
owed on the right day, confirming it writes exactly one movement dated that day,
confirming twice is refused, and a skip writes nothing at all.
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.recurrence import Frequency
from app.models import (
    Account,
    AccountType,
    CaptureMode,
    CategoryKind,
    Posting,
    PostingKind,
    RecurringFrequency,
    RecurringItem,
    RecurringOccurrence,
    Transaction,
    TransactionSource,
    User,
)
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.auth import create_user
from app.services.categories import create_category
from app.services.recurring import (
    InvalidRecurringItemError,
    RecurringItemConflictError,
    RecurringItemNotFoundError,
    RecurringItemRecord,
    RhythmChange,
    confirm,
    create_item,
    due_items,
    list_items,
    set_active,
    skip,
    soft_delete_item,
    update_item,
)
from app.services.transactions import balance, soft_delete_transaction

OPENED = date(2026, 4, 1)
TODAY = date(2026, 10, 6)
RENT_PAISE = 1_800_000  # ₹18,000.00
SALARY_PAISE = 5_00_000_00  # ₹5,00,000.00


def _account(db: Session, user: User, name: str = "SBI") -> Account:
    return create_account(
        db,
        user.id,
        AccountCreate.model_validate(
            {
                "name": name,
                "type": AccountType.SAVINGS,
                "capture_mode": CaptureMode.STATEMENT_IMPORT,
                "opening_balance_paise": 0,
                "opening_date": OPENED,
            }
        ),
    )


def _category(db: Session, user: User, name: str, kind: CategoryKind) -> int:
    return create_category(db, user.id, name, kind=kind).id


def _rent(db: Session, user: User, account: Account, **overrides: object) -> RecurringItemRecord:
    """A monthly rent due on the 1st, unless the test says otherwise."""
    payload: dict[str, object] = {
        "name": "Rent",
        "kind": PostingKind.EXPENSE,
        "amount_paise": RENT_PAISE,
        "account_id": account.id,
        "frequency": RecurringFrequency.MONTHLY,
        "starts_on": OPENED,
        "day_of_month": 1,
        **overrides,
    }
    return create_item(db, user.id, **payload)  # type: ignore[arg-type]


def _transactions(db: Session) -> list[Transaction]:
    return list(db.scalars(select(Transaction)))


def test_a_monthly_item_is_owed_on_its_own_day(db: Session, user: User) -> None:
    _rent(db, user, _account(db, user))

    owed = due_items(db, user.id, TODAY)

    assert [(row.item.name, row.due_on) for row in owed] == [("Rent", date(2026, 10, 1))]


def test_nothing_is_owed_before_the_day_arrives(db: Session, user: User) -> None:
    account = _account(db, user)
    _rent(db, user, account, day_of_month=31)

    assert due_items(db, user.id, date(2026, 10, 30)) == []
    assert [row.due_on for row in due_items(db, user.id, date(2026, 10, 31))] == [
        date(2026, 10, 31)
    ]


def test_an_item_that_has_not_started_is_not_owed(db: Session, user: User) -> None:
    account = _account(db, user)
    _rent(db, user, account, starts_on=date(2026, 11, 1))

    assert due_items(db, user.id, TODAY) == []


def test_an_item_that_has_ended_is_not_owed(db: Session, user: User) -> None:
    account = _account(db, user)
    _rent(db, user, account, ends_on=date(2026, 9, 30))

    assert due_items(db, user.id, TODAY) == []


def test_a_paused_item_is_not_owed(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)
    set_active(db, user.id, item.id, is_active=False)

    assert due_items(db, user.id, TODAY) == []


def test_a_removed_item_is_not_owed_and_is_not_listed(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)
    soft_delete_item(db, user.id, item.id)

    assert due_items(db, user.id, TODAY) == []
    assert list_items(db, user.id) == []
    # Soft, because an occurrence still points at it and money is never hard-deleted.
    assert db.get(RecurringItem, item.id) is not None


def test_a_weekly_item_comes_round_again_the_week_after(db: Session, user: User) -> None:
    account = _account(db, user)
    _rent(
        db,
        user,
        account,
        name="Household help",
        frequency=RecurringFrequency.WEEKLY,
        day_of_month=None,
        weekday=0,
    )

    assert [row.due_on for row in due_items(db, user.id, date(2026, 10, 8))] == [date(2026, 10, 5)]
    assert [row.due_on for row in due_items(db, user.id, date(2026, 10, 15))] == [
        date(2026, 10, 12)
    ]


def test_confirming_writes_one_movement_dated_the_day_it_was_owed(db: Session, user: User) -> None:
    account = _account(db, user)
    groceries = _category(db, user, "Groceries", CategoryKind.EXPENSE)
    item = _rent(db, user, account, category_id=groceries)

    confirmed = confirm(db, user.id, item.id, on=date(2026, 10, 28))

    assert confirmed.due_on == date(2026, 10, 1)

    (transaction,) = _transactions(db)
    assert transaction.id == confirmed.transaction_id
    assert transaction.transaction_date == date(2026, 10, 1)
    assert transaction.merchant == "Rent"
    assert transaction.source is TransactionSource.RECURRING

    (posting,) = db.scalars(select(Posting).where(Posting.transaction_id == transaction.id))
    assert posting.amount_paise == -RENT_PAISE
    assert posting.kind is PostingKind.EXPENSE
    assert posting.category_id == groceries

    assert balance(db, user.id, account.id).balance_paise == -RENT_PAISE


def test_confirming_an_income_item_records_money_arriving(db: Session, user: User) -> None:
    account = _account(db, user)
    salary = _category(db, user, "Salary", CategoryKind.INCOME)
    item = _rent(
        db,
        user,
        account,
        name="Salary",
        kind=PostingKind.INCOME,
        amount_paise=SALARY_PAISE,
        category_id=salary,
    )

    confirm(db, user.id, item.id, on=TODAY)

    assert balance(db, user.id, account.id).balance_paise == SALARY_PAISE


def test_a_movement_recorded_late_still_belongs_to_its_period(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)

    confirm(db, user.id, item.id, on=date(2026, 10, 28))

    assert due_items(db, user.id, date(2026, 10, 31)) == []


def test_confirming_the_same_period_twice_is_refused_and_writes_nothing(
    db: Session, user: User
) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)
    confirm(db, user.id, item.id, on=TODAY)

    with pytest.raises(RecurringItemConflictError):
        confirm(db, user.id, item.id, on=date(2026, 10, 20))

    assert len(_transactions(db)) == 1


def test_a_different_amount_can_be_confirmed_for_the_period(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)

    confirm(db, user.id, item.id, on=TODAY, amount_paise=2_000_000)

    assert balance(db, user.id, account.id).balance_paise == -2_000_000
    # The plan keeps its own figure: one odd month does not rewrite the rent.
    assert list_items(db, user.id)[0].amount_paise == RENT_PAISE


def test_confirming_something_that_is_not_due_is_refused(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account, day_of_month=31)

    with pytest.raises(RecurringItemConflictError):
        confirm(db, user.id, item.id, on=date(2026, 10, 30))

    assert _transactions(db) == []


def test_confirming_a_paused_item_is_refused(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)
    set_active(db, user.id, item.id, is_active=False)

    with pytest.raises(RecurringItemConflictError):
        confirm(db, user.id, item.id, on=TODAY)

    assert _transactions(db) == []


def test_a_skipped_period_is_not_owed_and_writes_nothing(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)

    skipped = skip(db, user.id, item.id, on=TODAY)

    assert skipped.due_on == date(2026, 10, 1)
    assert due_items(db, user.id, TODAY) == []
    assert _transactions(db) == []
    assert db.scalars(select(Posting)).all() == []
    assert db.scalars(select(RecurringOccurrence)).one().state.value == "skipped"


def test_skipping_twice_is_refused(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)
    skip(db, user.id, item.id, on=TODAY)

    with pytest.raises(RecurringItemConflictError):
        skip(db, user.id, item.id, on=TODAY)


def test_a_skipped_period_cannot_then_be_confirmed(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)
    skip(db, user.id, item.id, on=TODAY)

    with pytest.raises(RecurringItemConflictError):
        confirm(db, user.id, item.id, on=TODAY)


def test_removing_the_movement_makes_the_period_owed_again(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)
    confirmed = confirm(db, user.id, item.id, on=TODAY)

    soft_delete_transaction(db, user.id, confirmed.transaction_id)

    assert [row.due_on for row in due_items(db, user.id, TODAY)] == [date(2026, 10, 1)]


def test_a_period_can_be_confirmed_again_once_its_movement_is_removed(
    db: Session, user: User
) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)
    first = confirm(db, user.id, item.id, on=TODAY)
    soft_delete_transaction(db, user.id, first.transaction_id)

    second = confirm(db, user.id, item.id, on=TODAY)

    assert second.transaction_id != first.transaction_id
    assert balance(db, user.id, account.id).balance_paise == -RENT_PAISE


def test_february_is_this_months_day_for_an_item_due_on_the_31st(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account, day_of_month=31)

    confirmed = confirm(db, user.id, item.id, on=date(2027, 2, 28))

    assert confirmed.due_on == date(2027, 2, 28)
    assert due_items(db, user.id, date(2027, 2, 28)) == []
    assert [row.due_on for row in due_items(db, user.id, date(2027, 3, 31))] == [date(2027, 3, 31)]


def test_a_rhythm_change_moves_the_item_but_not_the_money_already_recorded(
    db: Session, user: User
) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)
    confirm(db, user.id, item.id, on=TODAY)

    update_item(
        db,
        user.id,
        item.id,
        rhythm=RhythmChange(RecurringFrequency.MONTHLY, day_of_month=5),
    )

    assert [row.due_on for row in due_items(db, user.id, date(2026, 10, 6))] == [date(2026, 10, 5)]
    assert db.scalars(select(Transaction)).one().transaction_date == date(2026, 10, 1)


def test_a_filing_can_be_added_and_taken_away(db: Session, user: User) -> None:
    account = _account(db, user)
    utilities = _category(db, user, "Electricity", CategoryKind.EXPENSE)
    item = _rent(db, user, account)

    updated = update_item(db, user.id, item.id, category_id=utilities, is_filing=True)
    assert updated.category_id == utilities

    cleared = update_item(db, user.id, item.id, category_id=None, is_filing=True)
    assert cleared.category_id is None


def test_a_category_of_the_wrong_kind_is_refused(db: Session, user: User) -> None:
    account = _account(db, user)
    salary = _category(db, user, "Salary", CategoryKind.INCOME)

    with pytest.raises(InvalidRecurringItemError):
        _rent(db, user, account, category_id=salary)


def test_only_spending_and_earning_can_repeat(db: Session, user: User) -> None:
    account = _account(db, user)

    with pytest.raises(InvalidRecurringItemError):
        _rent(db, user, account, kind=PostingKind.TRANSFER)


@pytest.mark.parametrize(
    "overrides",
    [
        {"day_of_month": None},
        {"day_of_month": None, "weekday": 3},
        {"day_of_month": 32},
        {"frequency": RecurringFrequency.WEEKLY, "day_of_month": 1},
    ],
)
def test_a_rhythm_has_to_be_whole(db: Session, user: User, overrides: dict[str, object]) -> None:
    account = _account(db, user)

    with pytest.raises(InvalidRecurringItemError):
        _rent(db, user, account, **overrides)


def test_an_amount_that_is_not_positive_is_refused(db: Session, user: User) -> None:
    account = _account(db, user)

    with pytest.raises(InvalidRecurringItemError):
        _rent(db, user, account, amount_paise=0)


def test_a_blank_name_is_refused(db: Session, user: User) -> None:
    account = _account(db, user)

    with pytest.raises(InvalidRecurringItemError):
        _rent(db, user, account, name="   ")


def test_an_end_before_the_start_is_refused(db: Session, user: User) -> None:
    account = _account(db, user)

    with pytest.raises(InvalidRecurringItemError):
        _rent(db, user, account, ends_on=date(2026, 3, 1))


def test_listing_returns_every_live_item_paused_ones_included(db: Session, user: User) -> None:
    account = _account(db, user)
    _rent(db, user, account)
    paused = _rent(db, user, account, name="Broadband", day_of_month=7)
    set_active(db, user.id, paused.id, is_active=False)

    # Ordered by name, so the list does not reshuffle as periods are dealt with.
    assert [row.name for row in list_items(db, user.id)] == ["Broadband", "Rent"]


def test_another_users_item_is_invisible(db: Session, user: User) -> None:
    account = _account(db, user)
    item = _rent(db, user, account)
    other = create_user(db, "someone@example.com", "another-passphrase")

    assert due_items(db, other.id, TODAY) == []
    assert list_items(db, other.id) == []

    with pytest.raises(RecurringItemNotFoundError):
        confirm(db, other.id, item.id, on=TODAY)

    with pytest.raises(RecurringItemNotFoundError):
        skip(db, other.id, item.id, on=TODAY)

    with pytest.raises(RecurringItemNotFoundError):
        soft_delete_item(db, other.id, item.id)


def test_the_stored_frequency_words_are_the_calendar_ones() -> None:
    assert {row.value for row in RecurringFrequency} == {row.value for row in Frequency}
