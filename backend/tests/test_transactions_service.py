"""Tests for app.services.transactions, against the real test database."""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    AccountType,
    CaptureMode,
    Posting,
    PostingKind,
    Transaction,
    TransactionSource,
    User,
)
from app.schemas.account import AccountCreate
from app.services.accounts import AccountNotFoundError, create_account, soft_delete_account
from app.services.auth import create_user
from app.services.transactions import (
    InvalidTransactionError,
    TransactionNotFoundError,
    balance,
    record_expense,
    record_income,
    record_transfer,
    soft_delete_transaction,
)

OPENED = date(2026, 4, 1)
LATER = date(2026, 4, 15)
OPENING_PAISE = 1_00_000_00  # ₹1,00,000.00


def _account(
    db: Session,
    user: User,
    name: str = "SBI",
    opening_paise: int = OPENING_PAISE,
    **overrides: object,
) -> Account:
    payload: dict[str, object] = {
        "name": name,
        "type": AccountType.SAVINGS,
        "capture_mode": CaptureMode.STATEMENT_IMPORT,
        "opening_balance_paise": opening_paise,
        "opening_date": OPENED,
        **overrides,
    }
    return create_account(db, user.id, AccountCreate.model_validate(payload))


def _postings(db: Session, transaction: Transaction) -> list[Posting]:
    return list(db.scalars(select(Posting).where(Posting.transaction_id == transaction.id)))


def test_an_expense_leaves_the_account_and_records_one_posting(db: Session, user: User) -> None:
    account = _account(db, user)

    transaction = record_expense(db, user.id, account.id, 500_00, LATER, merchant="Blinkit")

    postings = _postings(db, transaction)
    assert len(postings) == 1
    assert postings[0].amount_paise == -500_00
    assert postings[0].kind is PostingKind.EXPENSE
    assert postings[0].account_id == account.id
    assert transaction.source is TransactionSource.MANUAL
    assert transaction.transaction_date == LATER
    assert transaction.merchant == "Blinkit"
    assert balance(db, user.id, account.id).balance_paise == OPENING_PAISE - 500_00


def test_income_increases_the_balance(db: Session, user: User) -> None:
    account = _account(db, user)

    transaction = record_income(db, user.id, account.id, 75_000_00, LATER, note="salary")

    assert _postings(db, transaction)[0].amount_paise == 75_000_00
    assert balance(db, user.id, account.id).balance_paise == OPENING_PAISE + 75_000_00


def test_a_transfer_moves_money_between_two_accounts(db: Session, user: User) -> None:
    savings = _account(db, user, name="SBI")
    current = _account(db, user, name="Central Bank", opening_paise=0)

    transaction = record_transfer(db, user.id, savings.id, current.id, 40_000_00, LATER)

    postings = _postings(db, transaction)
    assert len(postings) == 2
    assert sum(posting.amount_paise for posting in postings) == 0
    assert {posting.kind for posting in postings} == {PostingKind.TRANSFER}
    assert balance(db, user.id, savings.id).balance_paise == OPENING_PAISE - 40_000_00
    assert balance(db, user.id, current.id).balance_paise == 40_000_00


def test_a_transfer_does_not_change_the_total_held(db: Session, user: User) -> None:
    savings = _account(db, user, name="SBI")
    current = _account(db, user, name="Central Bank", opening_paise=25_000_00)

    record_transfer(db, user.id, savings.id, current.id, 40_000_00, LATER)

    total = (
        balance(db, user.id, savings.id).balance_paise
        + balance(db, user.id, current.id).balance_paise
    )
    assert total == OPENING_PAISE + 25_000_00


def test_a_transfer_to_the_same_account_is_refused(db: Session, user: User) -> None:
    account = _account(db, user)

    with pytest.raises(InvalidTransactionError):
        record_transfer(db, user.id, account.id, account.id, 100_00, LATER)

    assert db.scalar(select(Transaction)) is None
    assert db.scalar(select(Posting)) is None


@pytest.mark.parametrize("amount_paise", [0, -1])
def test_an_amount_that_is_not_positive_is_refused(
    db: Session, user: User, amount_paise: int
) -> None:
    account = _account(db, user)

    with pytest.raises(InvalidTransactionError):
        record_expense(db, user.id, account.id, amount_paise, LATER)
    with pytest.raises(InvalidTransactionError):
        record_income(db, user.id, account.id, amount_paise, LATER)


def test_a_posting_before_the_account_opened_is_refused(db: Session, user: User) -> None:
    account = _account(db, user)

    with pytest.raises(InvalidTransactionError):
        record_expense(db, user.id, account.id, 500_00, date(2026, 3, 31))

    assert db.scalar(select(Posting)) is None


def test_a_rate_from_the_future_is_allowed_but_balance_as_of_ignores_it(
    db: Session, user: User
) -> None:
    account = _account(db, user)
    record_expense(db, user.id, account.id, 500_00, LATER)

    assert balance(db, user.id, account.id, as_of=date(2026, 4, 14)).balance_paise == OPENING_PAISE
    assert balance(db, user.id, account.id, as_of=LATER).balance_paise == OPENING_PAISE - 500_00


def test_a_card_purchase_makes_the_outstanding_grow(db: Session, user: User) -> None:
    card = _account(
        db,
        user,
        name="SBI Credit Card",
        opening_paise=-25_000_00,
        type=AccountType.CREDIT_CARD,
    )

    record_expense(db, user.id, card.id, 1_000_00, LATER, merchant="Amazon")

    assert balance(db, user.id, card.id).balance_paise == -26_000_00


def test_balance_reports_the_parts_it_was_worked_out_from(db: Session, user: User) -> None:
    account = _account(db, user)
    record_expense(db, user.id, account.id, 500_00, LATER)
    record_income(db, user.id, account.id, 200_00, LATER)

    result = balance(db, user.id, account.id)

    assert result.opening_balance_paise == OPENING_PAISE
    assert result.postings_paise == -300_00
    assert result.balance_paise == OPENING_PAISE - 300_00
    assert result.account_id == account.id


def test_soft_deleting_a_transaction_reverses_its_effect(db: Session, user: User) -> None:
    account = _account(db, user)
    transaction = record_expense(db, user.id, account.id, 500_00, LATER)

    soft_delete_transaction(db, user.id, transaction.id)

    assert balance(db, user.id, account.id).balance_paise == OPENING_PAISE
    kept = db.get(Transaction, transaction.id)
    assert kept is not None
    assert kept.deleted_at is not None
    assert all(posting.deleted_at is not None for posting in _postings(db, kept))


def test_a_deleted_transaction_cannot_be_deleted_again(db: Session, user: User) -> None:
    account = _account(db, user)
    transaction = record_expense(db, user.id, account.id, 500_00, LATER)
    soft_delete_transaction(db, user.id, transaction.id)

    with pytest.raises(TransactionNotFoundError):
        soft_delete_transaction(db, user.id, transaction.id)


def test_an_unknown_transaction_is_not_found(db: Session, user: User) -> None:
    with pytest.raises(TransactionNotFoundError):
        soft_delete_transaction(db, user.id, 999)


def test_another_users_account_is_not_found(db: Session, user: User) -> None:
    account = _account(db, user)
    other = create_user(db, "other@example.com", "s3cret-passphrase")

    with pytest.raises(AccountNotFoundError):
        record_expense(db, other.id, account.id, 500_00, LATER)


def test_money_cannot_be_recorded_against_a_soft_deleted_account(db: Session, user: User) -> None:
    account = _account(db, user)
    soft_delete_account(db, user.id, account.id)

    with pytest.raises(AccountNotFoundError):
        record_expense(db, user.id, account.id, 500_00, LATER)


def test_every_amount_recorded_is_whole_paise(db: Session, user: User) -> None:
    account = _account(db, user)

    transaction = record_expense(db, user.id, account.id, 12_34_567_89, LATER)

    amount = _postings(db, transaction)[0].amount_paise
    assert isinstance(amount, int)
    assert amount == -12_34_567_89
    assert balance(db, user.id, account.id).balance_paise == OPENING_PAISE - 12_34_567_89
