"""Balance checks: comparing the ledger with the bank, and writing off the gap.

The arithmetic lives in `app.core.ledger`. This module's job is the database
work around it: what is recorded, what is posted, and which figures the caller
is told about.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session as DbSession

from app.core.ledger import difference_paise, is_large_adjustment, share_percent
from app.models import BalanceCheck, Posting, PostingKind, Transaction
from app.services.accounts import get_account
from app.services.transactions import balance, record_adjustment, require_on_or_after_opening

# Until categories arrive in M10, a write-off says in words what it is. The sign
# of the difference decides which of the two it is.
NOTE_UNACCOUNTED = "Unaccounted for spending"
NOTE_FOUND = "Unrecorded income"


@dataclass(frozen=True)
class BalanceCheckRecord:
    """One check as the API reports it."""

    id: int
    account_id: int
    checked_on: date
    computed_balance_paise: int
    stated_balance_paise: int
    difference_paise: int
    adjustment_transaction_id: int | None


@dataclass(frozen=True)
class BalanceCheckOutcome:
    """What a check found, and what was said about it."""

    record: BalanceCheckRecord
    warning: bool
    threshold_paise: int


@dataclass(frozen=True)
class AdjustmentShare:
    """Write-offs against spending for one month, as positive magnitudes."""

    month: date
    spend_paise: int
    adjustments_paise: int
    share_percent: int


def note_for(difference_paise: int) -> str:
    """The wording a write-off carries, which its sign decides."""
    return NOTE_FOUND if difference_paise > 0 else NOTE_UNACCOUNTED


def check_balance(
    db: DbSession,
    user_id: int,
    account_id: int,
    *,
    on: date,
    stated_paise: int,
    adjust: bool,
    warning_threshold_paise: int,
) -> BalanceCheckOutcome:
    """Compare the ledger with the bank, record it, and write off the gap.

    The check is recorded whether or not the difference is written off: what the
    ledger said on the day is worth keeping either way. When the write-off is
    asked for it is the signed difference, so the computed balance plus the
    write-off lands exactly on the stated balance.
    """
    account = get_account(db, user_id, account_id)
    require_on_or_after_opening(account, on)

    computed = balance(db, user_id, account.id, as_of=on).balance_paise
    difference = difference_paise(computed_paise=computed, stated_paise=stated_paise)

    adjustment_transaction_id: int | None = None
    adjustment_posting_id: int | None = None
    if adjust and difference != 0:
        transaction = record_adjustment(
            db,
            user_id,
            account.id,
            difference,
            on,
            note_for(difference),
        )
        adjustment_transaction_id = transaction.id
        adjustment_posting_id = db.scalars(
            select(Posting.id).where(Posting.transaction_id == transaction.id)
        ).one()

    check = BalanceCheck(
        account_id=account.id,
        checked_on=on,
        computed_paise=computed,
        stated_paise=stated_paise,
        difference_paise=difference,
        adjustment_posting_id=adjustment_posting_id,
    )
    db.add(check)
    db.commit()

    return BalanceCheckOutcome(
        record=BalanceCheckRecord(
            id=check.id,
            account_id=check.account_id,
            checked_on=check.checked_on,
            computed_balance_paise=check.computed_paise,
            stated_balance_paise=check.stated_paise,
            difference_paise=check.difference_paise,
            adjustment_transaction_id=adjustment_transaction_id,
        ),
        warning=is_large_adjustment(difference, warning_threshold_paise),
        threshold_paise=warning_threshold_paise,
    )


def list_checks(db: DbSession, user_id: int, account_id: int) -> list[BalanceCheckRecord]:
    """The account's checks, most recent first."""
    account = get_account(db, user_id, account_id)

    statement = (
        select(BalanceCheck, Transaction.id)
        .outerjoin(Posting, BalanceCheck.adjustment_posting_id == Posting.id)
        .outerjoin(Transaction, Posting.transaction_id == Transaction.id)
        .where(
            BalanceCheck.account_id == account.id,
            BalanceCheck.deleted_at.is_(None),
        )
        .order_by(BalanceCheck.checked_on.desc(), BalanceCheck.id.desc())
    )

    return [
        BalanceCheckRecord(
            id=check.id,
            account_id=check.account_id,
            checked_on=check.checked_on,
            computed_balance_paise=check.computed_paise,
            stated_balance_paise=check.stated_paise,
            difference_paise=check.difference_paise,
            adjustment_transaction_id=transaction_id,
        )
        for check, transaction_id in db.execute(statement).all()
    ]


def adjustment_share(db: DbSession, user_id: int, account_id: int, month: date) -> AdjustmentShare:
    """How much of one month's spending was written off.

    Only `expense` postings count as spending: a transfer moves money without
    spending it, and an adjustment is the opposite of spending - it is the part
    the ledger never saw. Both figures come back as magnitudes, because a share
    does not care which way either one went.
    """
    account = get_account(db, user_id, account_id)
    first_of_month = month.replace(day=1)
    first_of_next = (first_of_month + timedelta(days=32)).replace(day=1)

    statement: Select[PostingKind, int] = (
        select(Posting.kind, func.sum(Posting.amount_paise))
        .join(Transaction, Posting.transaction_id == Transaction.id)
        .where(
            Posting.account_id == account.id,
            Posting.deleted_at.is_(None),
            Transaction.deleted_at.is_(None),
            Transaction.transaction_date >= first_of_month,
            Transaction.transaction_date < first_of_next,
            Posting.kind.in_([PostingKind.EXPENSE, PostingKind.ADJUSTMENT]),
        )
        .group_by(Posting.kind)
    )
    totals: dict[PostingKind, int] = dict(db.execute(statement).all())
    spend = abs(totals.get(PostingKind.EXPENSE, 0))
    adjustments = abs(totals.get(PostingKind.ADJUSTMENT, 0))

    return AdjustmentShare(
        month=first_of_month,
        spend_paise=spend,
        adjustments_paise=adjustments,
        share_percent=share_percent(adjustments, spend),
    )
