"""Interest: which periods earned what, and the figure the bank actually paid.

The arithmetic lives in `app.core.interest`, the rate records in
`app.services.interest_rates`, and the writing of money in
`app.services.transactions`. This module is the part in between: working out which
periods have finished, keeping the proposal, and posting the credit once the user
confirms the bank's figure.

A proposal is a *snapshot of a finished period*, not a running figure. It is
worked out from the ledger as it stood when the period ended, and nothing later
rewrites it: a movement recorded afterwards belongs to a later period's balance,
and a credit confirmed afterwards earns interest from the next period onwards.
That is what makes the figures stable enough to compare with a bank statement.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session as DbSession

from app.core.interest import (
    Crediting,
    DatedRate,
    accrued_paise,
    credit_periods,
    rate_periods,
)
from app.core.ledger import DatedAmount
from app.models import (
    InterestCredit,
    InterestRate,
    Posting,
    RateFrequency,
    Transaction,
)
from app.services.accounts import get_account
from app.services.transactions import record_interest


class InterestNotFoundError(LookupError):
    """Raised when a period does not exist for the user's account, or was dropped."""


class InvalidInterestError(ValueError):
    """Raised when interest cannot be worked out as the request asks."""


class InterestConflictError(ValueError):
    """Raised when a period is not in a state where this can be done to it."""


# The three the engine understands. A yearly rate would credit once a year and has
# no period here, so it is refused in words rather than proposing nothing.
CREDITING_BY_FREQUENCY: dict[RateFrequency, Crediting] = {
    RateFrequency.DAILY: Crediting.DAILY,
    RateFrequency.MONTHLY: Crediting.MONTHLY,
    RateFrequency.QUARTERLY: Crediting.QUARTERLY,
}


@dataclass(frozen=True)
class InterestCreditRecord:
    """One period as the API reports it."""

    id: int
    account_id: int
    period_start: date
    period_end: date
    rate_percent: Decimal
    computed_paise: int
    credited_paise: int | None
    transaction_id: int | None
    confirmed_on: date | None


@dataclass(frozen=True)
class AccountInterest:
    """An account's interest: what is credited, and what is waiting to be."""

    credited_paise: int
    uncredited_paise: int
    proposals: list[InterestCreditRecord]
    history: list[InterestCreditRecord]


def _record(row: InterestCredit) -> InterestCreditRecord:
    """One period as the API reports it, from the row that keeps it."""
    return InterestCreditRecord(
        id=row.id,
        account_id=row.account_id,
        period_start=row.period_start,
        period_end=row.period_end,
        rate_percent=row.rate_percent,
        computed_paise=row.computed_paise,
        credited_paise=row.credited_paise,
        transaction_id=row.transaction_id,
        confirmed_on=row.confirmed_on,
    )


def _live_credits(account_id: int) -> Select[InterestCredit]:
    """An account's live interest rows. Soft-deleted proposals are never returned."""
    return select(InterestCredit).where(
        InterestCredit.account_id == account_id,
        InterestCredit.deleted_at.is_(None),
    )


def _rates(db: DbSession, account_id: int) -> list[InterestRate]:
    """The account's live rate records, oldest first. History is never overwritten."""
    return list(
        db.scalars(
            select(InterestRate)
            .where(InterestRate.account_id == account_id, InterestRate.deleted_at.is_(None))
            .order_by(InterestRate.from_date, InterestRate.id)
        )
    )


def _postings(db: DbSession, account_id: int) -> list[DatedAmount]:
    """The account's live postings, dated the day their transaction moved."""
    rows = db.execute(
        select(Transaction.transaction_date, Posting.amount_paise)
        .join(Posting, Posting.transaction_id == Transaction.id)
        .where(
            Posting.account_id == account_id,
            Posting.deleted_at.is_(None),
            Transaction.deleted_at.is_(None),
        )
    ).all()
    return [DatedAmount(on, amount_paise) for on, amount_paise in rows]


def _crediting(rates: list[InterestRate]) -> Crediting:
    """How the account's interest is credited, from the rate in force now.

    The latest record governs, because that is the arrangement the account is on
    today: an earlier record's rhythm describes a period that has already passed.
    """
    frequency = rates[-1].frequency
    crediting = CREDITING_BY_FREQUENCY.get(frequency)
    if crediting is None:
        raise InvalidInterestError(
            f"a {frequency.value} rate has no crediting period here;"
            " set the rate to daily, monthly or quarterly"
        )
    return crediting


def _first_day(db: DbSession, account_id: int, rates: list[InterestRate]) -> date:
    """Where to work out interest from: after the last period, or the first rate."""
    latest = db.scalar(
        select(func.max(InterestCredit.period_end)).where(
            InterestCredit.account_id == account_id,
            InterestCredit.deleted_at.is_(None),
        )
    )
    if latest is not None:
        return latest + timedelta(days=1)
    return rates[0].from_date


def propose(
    db: DbSession,
    user_id: int,
    account_id: int,
    *,
    through: date,
) -> list[InterestCreditRecord]:
    """Work out and keep every crediting period that has finished, up to a day.

    One row per run of days under one rate, so each row names the one rate that
    produced its figure. A period that earned nothing gets no row: there would be
    nothing to confirm, and a zero posting would not move a balance.

    Running this twice proposes nothing new, which is what makes it safe for a
    daily job that may start twice.
    """
    account = get_account(db, user_id, account_id)
    rates = _rates(db, account.id)
    if not rates:
        return []

    crediting = _crediting(rates)
    dated = [DatedRate(row.from_date, row.rate) for row in rates]
    postings = _postings(db, account.id)
    from_day = _first_day(db, account.id, rates)

    made: list[InterestCredit] = []
    for start, end in credit_periods(crediting, first_day=from_day, through=through):
        for stretch_start, stretch_end, percent in rate_periods(dated, start=start, end=end):
            amount = accrued_paise(
                opening_balance_paise=account.opening_balance_paise,
                opening_date=account.opening_date,
                postings=postings,
                rates=dated,
                start=stretch_start,
                end=stretch_end,
            )
            if amount <= 0:
                continue
            row = InterestCredit(
                account_id=account.id,
                period_start=stretch_start,
                period_end=stretch_end,
                rate_percent=percent,
                computed_paise=amount,
            )
            db.add(row)
            made.append(row)

    db.commit()
    return [_record(row) for row in made]


def proposals(db: DbSession, user_id: int, account_id: int) -> list[InterestCreditRecord]:
    """What has been worked out and not yet credited, oldest first."""
    account = get_account(db, user_id, account_id)
    rows = db.scalars(
        _live_credits(account.id)
        .where(InterestCredit.confirmed_on.is_(None))
        .order_by(InterestCredit.period_start, InterestCredit.id)
    )
    return [_record(row) for row in rows]


def history(
    db: DbSession,
    user_id: int,
    account_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[InterestCreditRecord]:
    """What has been credited, newest first."""
    account = get_account(db, user_id, account_id)
    rows = db.scalars(
        _live_credits(account.id)
        .where(InterestCredit.confirmed_on.is_not(None))
        .order_by(InterestCredit.period_end.desc(), InterestCredit.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_record(row) for row in rows]


def credited_total(db: DbSession, user_id: int, account_id: int) -> int:
    """Everything this account has had credited, in whole paise."""
    account = get_account(db, user_id, account_id)
    total = db.scalar(
        select(func.sum(InterestCredit.credited_paise)).where(
            InterestCredit.account_id == account.id,
            InterestCredit.deleted_at.is_(None),
        )
    )
    return int(total or 0)


def summary(db: DbSession, user_id: int, account_id: int) -> AccountInterest:
    """What is credited, what is waiting, and both lists."""
    waiting = proposals(db, user_id, account_id)
    return AccountInterest(
        credited_paise=credited_total(db, user_id, account_id),
        uncredited_paise=sum(row.computed_paise for row in waiting),
        proposals=waiting,
        history=history(db, user_id, account_id),
    )


def get_credit(db: DbSession, user_id: int, account_id: int, credit_id: int) -> InterestCredit:
    """One live period for the user's account, or a not-found error."""
    account = get_account(db, user_id, account_id)
    row = db.scalars(_live_credits(account.id).where(InterestCredit.id == credit_id)).one_or_none()
    if row is None:
        raise InterestNotFoundError(f"Interest period {credit_id} does not exist")
    return row


def confirm(
    db: DbSession,
    user_id: int,
    account_id: int,
    credit_id: int,
    *,
    on: date,
    credited_paise: int | None = None,
) -> InterestCreditRecord:
    """Credit a period, for the figure the bank paid.

    Give the bank's figure when it differs from the ledger's: both are kept, so
    the difference is visible rather than the calculation being quietly rewritten.
    The posting is dated the day the period ended, because that is when the bank
    paid it, and the money is what earns in the next period.
    """
    row = get_credit(db, user_id, account_id, credit_id)
    if row.credited_paise is not None:
        raise InterestConflictError(
            f"interest to {row.period_end} was already credited on {row.confirmed_on}"
        )

    amount = row.computed_paise if credited_paise is None else credited_paise
    if amount <= 0:
        raise InvalidInterestError("an interest credit must be more than zero")

    transaction = record_interest(
        db,
        user_id,
        row.account_id,
        amount,
        row.period_end,
        note=f"Interest {row.period_start} to {row.period_end}",
    )
    row.credited_paise = amount
    row.transaction_id = transaction.id
    row.confirmed_on = on
    db.commit()
    return _record(row)


def drop(db: DbSession, user_id: int, account_id: int, credit_id: int) -> None:
    """Throw a proposal away, because it should never have been worked out.

    Only a proposal can be dropped. A credited period is money on the ledger, and
    the way to undo that is to remove the movement it posted, on the Transactions
    screen, where every other movement is corrected.
    """
    row = get_credit(db, user_id, account_id, credit_id)
    if row.credited_paise is not None:
        raise InterestConflictError(
            f"interest to {row.period_end} is already credited; remove its movement instead"
        )

    row.deleted_at = datetime.now(UTC)
    db.commit()
