"""Recording money movements, and working out what an account holds.

Every amount here is signed paise, and the arithmetic itself lives in
`app.core.ledger`. This module's job is the rules that need the database, the
postings written in one piece, and handing the sums to the ledger.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session as DbSession

from app.core.ledger import (
    DatedAmount,
    balance_paise,
    is_balanced,
    sum_paise,
    transfer_amounts,
)
from app.models import Account, Posting, PostingKind, Transaction, TransactionSource
from app.services.accounts import get_account


class TransactionNotFoundError(LookupError):
    """Raised when a transaction does not exist for the user, or is soft-deleted."""


class InvalidTransactionError(ValueError):
    """Raised when a movement would break a rule that needs the database."""


@dataclass(frozen=True)
class BalanceBreakdown:
    """A balance, and the two figures it was worked out from."""

    account_id: int
    as_of: date | None
    opening_balance_paise: int
    postings_paise: int
    balance_paise: int


def record_expense(
    db: DbSession,
    user_id: int,
    account_id: int,
    amount_paise: int,
    on: date,
    merchant: str | None = None,
    note: str | None = None,
) -> Transaction:
    """Record money leaving an account. Give the amount as a positive number."""
    _require_positive(amount_paise)
    account = get_account(db, user_id, account_id)
    _require_on_or_after_opening(account, on)

    return _record(
        db,
        user_id,
        on,
        [(account.id, -amount_paise, PostingKind.EXPENSE)],
        merchant=merchant,
        note=note,
    )


def record_income(
    db: DbSession,
    user_id: int,
    account_id: int,
    amount_paise: int,
    on: date,
    merchant: str | None = None,
    note: str | None = None,
) -> Transaction:
    """Record money arriving. Give the amount as a positive number."""
    _require_positive(amount_paise)
    account = get_account(db, user_id, account_id)
    _require_on_or_after_opening(account, on)

    return _record(
        db,
        user_id,
        on,
        [(account.id, amount_paise, PostingKind.INCOME)],
        merchant=merchant,
        note=note,
    )


def record_transfer(
    db: DbSession,
    user_id: int,
    from_account_id: int,
    to_account_id: int,
    amount_paise: int,
    on: date,
    note: str | None = None,
) -> Transaction:
    """Move money between two accounts: two postings that sum to zero."""
    _require_positive(amount_paise)
    if from_account_id == to_account_id:
        raise InvalidTransactionError("a transfer needs two different accounts")

    source = get_account(db, user_id, from_account_id)
    destination = get_account(db, user_id, to_account_id)
    _require_on_or_after_opening(source, on)
    _require_on_or_after_opening(destination, on)

    out_of_source, into_destination = transfer_amounts(amount_paise)
    return _record(
        db,
        user_id,
        on,
        [
            (source.id, out_of_source, PostingKind.TRANSFER),
            (destination.id, into_destination, PostingKind.TRANSFER),
        ],
        note=note,
    )


def get_transaction(db: DbSession, user_id: int, transaction_id: int) -> Transaction:
    """Return one live transaction, or raise TransactionNotFoundError."""
    transaction = db.scalars(
        _live_transactions(user_id).where(Transaction.id == transaction_id)
    ).first()
    if transaction is None:
        raise TransactionNotFoundError(transaction_id)
    return transaction


def soft_delete_transaction(db: DbSession, user_id: int, transaction_id: int) -> None:
    """Soft-delete a transaction and its postings, so balances no longer include it."""
    transaction = get_transaction(db, user_id, transaction_id)
    now = datetime.now(UTC)

    transaction.deleted_at = now
    for posting in _postings_of(db, transaction_id):
        posting.deleted_at = now
    db.commit()


def balance(
    db: DbSession,
    user_id: int,
    account_id: int,
    as_of: date | None = None,
) -> BalanceBreakdown:
    """The account's balance: its opening balance plus the postings that apply."""
    account = get_account(db, user_id, account_id)
    postings = [
        DatedAmount(row[0], row[1]) for row in db.execute(_dated_postings(account.id, as_of)).all()
    ]

    return BalanceBreakdown(
        account_id=account.id,
        as_of=as_of,
        opening_balance_paise=account.opening_balance_paise,
        postings_paise=sum_paise(posting.amount_paise for posting in postings),
        balance_paise=balance_paise(
            account.opening_balance_paise,
            account.opening_date,
            postings,
            as_of,
        ),
    )


def _record(
    db: DbSession,
    user_id: int,
    on: date,
    movements: Sequence[tuple[int, int, PostingKind]],
    *,
    merchant: str | None = None,
    note: str | None = None,
) -> Transaction:
    """Write one transaction and its postings, as one piece.

    The postings are checked against the ledger's rule before anything is
    written, so a half-written movement is not possible.
    """
    amounts = [amount_paise for _, amount_paise, _ in movements]
    if not is_balanced(amounts):
        raise InvalidTransactionError(
            f"postings must be one external flow or sum to zero, got {amounts}"
        )

    transaction = Transaction(
        user_id=user_id,
        transaction_date=on,
        merchant=merchant,
        note=note,
        source=TransactionSource.MANUAL,
    )
    db.add(transaction)
    db.flush()

    for account_id, amount_paise, kind in movements:
        db.add(
            Posting(
                transaction_id=transaction.id,
                account_id=account_id,
                amount_paise=amount_paise,
                kind=kind,
            )
        )
    db.commit()
    return transaction


def _live_transactions(user_id: int) -> Select[Transaction]:
    """The user's live transactions. Soft-deleted rows are never returned."""
    return select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.deleted_at.is_(None),
    )


def _postings_of(db: DbSession, transaction_id: int) -> list[Posting]:
    return list(db.scalars(select(Posting).where(Posting.transaction_id == transaction_id)))


def _dated_postings(account_id: int, as_of: date | None) -> Select[date, int]:
    """An account's live postings with the date of the transaction they belong to."""
    statement = (
        select(Transaction.transaction_date, Posting.amount_paise)
        .join(Transaction, Posting.transaction_id == Transaction.id)
        .where(
            Posting.account_id == account_id,
            Posting.deleted_at.is_(None),
            Transaction.deleted_at.is_(None),
        )
        .order_by(Transaction.transaction_date, Posting.id)
    )
    if as_of is not None:
        statement = statement.where(Transaction.transaction_date <= as_of)
    return statement


def _require_positive(amount_paise: int) -> None:
    """Amounts are given as positive numbers; the kind decides the direction."""
    if amount_paise <= 0:
        raise InvalidTransactionError(
            f"give a positive amount and let the kind set the direction, got {amount_paise}"
        )


def _require_on_or_after_opening(account: Account, on: date) -> None:
    """The opening balance already describes the account before it opened."""
    if on < account.opening_date:
        raise InvalidTransactionError(
            f"{account.name} opened on {account.opening_date}, so {on} is too early"
        )
