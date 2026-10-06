"""Recording money movements, and working out what an account holds.

Every amount here is signed paise, and the arithmetic itself lives in
`app.core.ledger`. This module's job is the rules that need the database, the
postings written in one piece, and handing the sums to the ledger.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session as DbSession

from app.core.ledger import (
    DatedAmount,
    balance_paise,
    is_balanced,
    parts_make_whole,
    sum_paise,
    transfer_amounts,
)
from app.core.suggestions import Suggestion, rank_suggestions, streak_days
from app.models import Account, CategoryKind, Posting, PostingKind, Transaction, TransactionSource
from app.schemas.transaction import SplitPartCreate, TransactionUpdate
from app.services.accounts import get_account
from app.services.categories import (
    UNACCOUNTED,
    UNRECORDED_INCOME,
    find_by_name,
    get_category,
    kind_word,
)


class TransactionNotFoundError(LookupError):
    """Raised when a transaction does not exist for the user, or is soft-deleted."""


class InvalidTransactionError(ValueError):
    """Raised when a movement would break a rule that needs the database."""


# How far back a name has to have been used to be worth offering again. Three
# months is long enough to hold a monthly habit and short enough that a name the
# user has dropped stops taking up room in the row.
SUGGESTION_DAYS = 90


@dataclass(frozen=True)
class BalanceBreakdown:
    """A balance, and the two figures it was worked out from."""

    account_id: int
    as_of: date | None
    opening_balance_paise: int
    postings_paise: int
    balance_paise: int


@dataclass(frozen=True)
class Movement:
    """One posting about to be written: which account, how much, and what it is."""

    account_id: int
    amount_paise: int
    kind: PostingKind
    category_id: int | None = None


# Only spending and earning have categories the user chooses. A transfer moves
# money without spending it, and a write-off's filing is chosen for it.
_CATEGORY_KINDS: dict[PostingKind, CategoryKind] = {
    PostingKind.EXPENSE: CategoryKind.EXPENSE,
    PostingKind.INCOME: CategoryKind.INCOME,
    PostingKind.ADJUSTMENT: CategoryKind.ADJUSTMENT,
}


def _file_under(
    db: DbSession, user_id: int, category_id: int | None, kind: PostingKind
) -> int | None:
    """The category a posting goes under, refusing one that means something else."""
    if category_id is None:
        return None

    expected = _CATEGORY_KINDS.get(kind)
    if expected is None:
        raise InvalidTransactionError(f"a {kind.value} is not filed under a category")

    category = get_category(db, user_id, category_id)
    if category.kind is not expected:
        raise InvalidTransactionError(
            f"{category.name} is for {kind_word(category.kind)}, not {kind_word(expected)}"
        )
    return category.id


def _write_off_filing(db: DbSession, user_id: int, amount_paise: int) -> int | None:
    """What a write-off files itself under: the tree's name for its direction.

    Money short is spending that went unrecorded; money found is income that went
    unrecorded. The names are the user's to rename or remove and a check must
    always be recordable, so a name that is gone simply leaves the write-off
    unfiled.
    """
    name = UNRECORDED_INCOME if amount_paise > 0 else UNACCOUNTED
    category = find_by_name(db, user_id, name, kind=CategoryKind.ADJUSTMENT)
    return None if category is None else category.id


# The sign a kind gives the amount the user states as a positive figure.
_DIRECTIONS: dict[PostingKind, int] = {
    PostingKind.EXPENSE: -1,
    PostingKind.INCOME: 1,
}


def _movements(
    db: DbSession,
    user_id: int,
    account_id: int,
    amount_paise: int,
    kind: PostingKind,
    category_id: int | None,
    parts: Sequence[SplitPartCreate] | None,
) -> list[Movement]:
    """The postings one movement becomes: one, or one per part when it was split.

    Both sides of a split sit on the same account, because they are one payment
    out of one place; splitting it across accounts would count the money twice.
    """
    direction = _DIRECTIONS.get(kind)
    if direction is None:
        raise InvalidTransactionError(f"a {kind.value} is not filed under a category")

    if parts is None:
        return [
            Movement(
                account_id,
                direction * amount_paise,
                kind,
                _file_under(db, user_id, category_id, kind),
            )
        ]

    if category_id is not None:
        raise InvalidTransactionError("filed under a category or under parts, not both")

    amounts = [part.amount_paise for part in parts]
    if not parts_make_whole(amount_paise, amounts):
        raise InvalidTransactionError(
            f"the parts must add up to {amount_paise} paise in two parts or more, got {amounts}"
        )

    return [
        Movement(
            account_id,
            direction * part.amount_paise,
            kind,
            _file_under(db, user_id, part.category_id, kind),
        )
        for part in parts
    ]


def record_expense(
    db: DbSession,
    user_id: int,
    account_id: int,
    amount_paise: int,
    on: date,
    merchant: str | None = None,
    note: str | None = None,
    category_id: int | None = None,
    parts: Sequence[SplitPartCreate] | None = None,
) -> Transaction:
    """Record money leaving an account. Give the amount as a positive number.

    One purchase may really be several things, so it can be split into parts
    instead of filed under a single category.
    """
    _require_positive(amount_paise)
    account = get_account(db, user_id, account_id)
    require_on_or_after_opening(account, on)

    return _record(
        db,
        user_id,
        on,
        _movements(db, user_id, account.id, amount_paise, PostingKind.EXPENSE, category_id, parts),
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
    category_id: int | None = None,
    parts: Sequence[SplitPartCreate] | None = None,
) -> Transaction:
    """Record money arriving. Give the amount as a positive number."""
    _require_positive(amount_paise)
    account = get_account(db, user_id, account_id)
    require_on_or_after_opening(account, on)

    return _record(
        db,
        user_id,
        on,
        _movements(db, user_id, account.id, amount_paise, PostingKind.INCOME, category_id, parts),
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
    require_on_or_after_opening(source, on)
    require_on_or_after_opening(destination, on)

    out_of_source, into_destination = transfer_amounts(amount_paise)
    return _record(
        db,
        user_id,
        on,
        [
            Movement(source.id, out_of_source, PostingKind.TRANSFER),
            Movement(destination.id, into_destination, PostingKind.TRANSFER),
        ],
        note=note,
    )


def record_adjustment(
    db: DbSession,
    user_id: int,
    account_id: int,
    amount_paise: int,
    on: date,
    note: str | None = None,
) -> Transaction:
    """Write off the gap between the ledger and the bank.

    The amount is the signed difference, so it may be negative or positive: here
    the sign *is* the answer, which is why this is the one movement that does not
    take a positive amount and let the kind decide. Writing off nothing is not a
    movement, so a zero is refused.
    """
    if amount_paise == 0:
        raise InvalidTransactionError("an adjustment must change the balance")

    account = get_account(db, user_id, account_id)
    require_on_or_after_opening(account, on)

    return _record(
        db,
        user_id,
        on,
        [
            Movement(
                account.id,
                amount_paise,
                PostingKind.ADJUSTMENT,
                _write_off_filing(db, user_id, amount_paise),
            )
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
    movements: Sequence[Movement],
    *,
    merchant: str | None = None,
    note: str | None = None,
) -> Transaction:
    """Write one transaction and its postings, as one piece.

    The postings are checked against the ledger's rule before anything is
    written, so a half-written movement is not possible.
    """
    amounts = [movement.amount_paise for movement in movements]
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

    for movement in movements:
        db.add(
            Posting(
                transaction_id=transaction.id,
                account_id=movement.account_id,
                amount_paise=movement.amount_paise,
                kind=movement.kind,
                category_id=movement.category_id,
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


def require_on_or_after_opening(account: Account, on: date) -> None:
    """The opening balance already describes the account before it opened.

    Public because anything dated - a movement or a balance check - has to obey
    the same rule, and one rule in one place is the point.
    """
    if on < account.opening_date:
        raise InvalidTransactionError(
            f"{account.name} opened on {account.opening_date}, so {on} is too early"
        )


@dataclass(frozen=True)
class TransactionDetail:
    """A transaction with the postings that belong to it."""

    transaction: Transaction
    postings: list[Posting]


def merchant_suggestions(
    db: DbSession,
    user_id: int,
    *,
    on: date,
    within_days: int = SUGGESTION_DAYS,
    limit: int = 8,
) -> list[Suggestion]:
    """The names worth offering for fast entry, most used first.

    History is the merchants the user has recorded: income as well as spending,
    because a name is a name. A write-off has no merchant and a transfer has
    none, so neither is history. What a suggestion remembers is how the name was
    recorded *last*, and a split remembers no single category, because it has
    several: offering one of them would be a guess dressed as a memory.
    """
    rows = db.execute(_live_merchant_history(user_id)).all()

    seen: dict[str, Suggestion] = {}
    for merchant, times_used, last_used, account_id, category_id, amount_paise, postings in rows:
        # The rows arrive newest first, so the first sight of a name is its most
        # recent use, and later rows for the same name are older: keep the first.
        if merchant in seen:
            continue
        seen[merchant] = Suggestion(
            merchant=merchant,
            times_used=times_used,
            last_used=last_used,
            account_id=account_id,
            category_id=category_id if postings == 1 else None,
            amount_paise=abs(amount_paise),
        )

    return rank_suggestions(list(seen.values()), within_days, on)[:limit]


def _live_merchant_history(user_id: int) -> Select[str, int, date, int, int | None, int, int]:
    """One row per live movement that names a merchant, newest first.

    The count is per name across the whole history, and the rest of the row is
    that movement's own: which account, which category (if it has one), how much,
    and how many postings it has.
    """
    counted = (
        select(Transaction.merchant, func.count(Posting.id).label("times_used"))
        .join(Posting, Posting.transaction_id == Transaction.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
            Posting.deleted_at.is_(None),
            Transaction.merchant.is_not(None),
            Posting.kind.in_([PostingKind.EXPENSE, PostingKind.INCOME]),
        )
        .group_by(Transaction.merchant)
        .subquery()
    )

    postings = (
        select(
            Posting.transaction_id,
            func.count(Posting.id).label("postings"),
            func.min(Posting.account_id).label("account_id"),
            func.max(Posting.category_id).label("category_id"),
            func.sum(Posting.amount_paise).label("amount_paise"),
        )
        .where(Posting.deleted_at.is_(None))
        .group_by(Posting.transaction_id)
        .subquery()
    )

    return (
        select(
            Transaction.merchant,
            counted.c.times_used,
            Transaction.transaction_date,
            postings.c.account_id,
            postings.c.category_id,
            postings.c.amount_paise,
            postings.c.postings,
        )
        .join(counted, counted.c.merchant == Transaction.merchant)
        .join(postings, postings.c.transaction_id == Transaction.id)
        .where(Transaction.user_id == user_id, Transaction.deleted_at.is_(None))
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
    )


def streak(db: DbSession, user_id: int, today: date) -> tuple[int, bool]:
    """How many days in a row the user has recorded something, and whether today is one."""
    days = [row[0] for row in db.execute(_recorded_days(user_id)).all()]
    return streak_days(days, today), today in set(days)


def _recorded_days(user_id: int) -> Select[date]:
    """The days on which a live movement was recorded, newest first."""
    return (
        select(Transaction.transaction_date)
        .join(Posting, Posting.transaction_id == Transaction.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
            Posting.deleted_at.is_(None),
        )
        .group_by(Transaction.transaction_date)
        .order_by(Transaction.transaction_date.desc())
    )


def transaction_detail(db: DbSession, user_id: int, transaction_id: int) -> TransactionDetail:
    """Return one live transaction together with its live postings."""
    transaction = get_transaction(db, user_id, transaction_id)
    postings = _live_postings_for(db, [transaction.id])
    return TransactionDetail(transaction, postings.get(transaction.id, []))


def list_transactions(
    db: DbSession,
    user_id: int,
    *,
    account_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    kind: PostingKind | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TransactionDetail]:
    """The user's live transactions, newest first, with their postings.

    The filters combine: an account and a kind together mean a transaction that
    has a posting matching both.
    """
    statement = _live_transactions(user_id).order_by(
        Transaction.transaction_date.desc(),
        Transaction.id.desc(),
    )
    if from_date is not None:
        statement = statement.where(Transaction.transaction_date >= from_date)
    if to_date is not None:
        statement = statement.where(Transaction.transaction_date <= to_date)
    if account_id is not None or kind is not None:
        statement = statement.where(Transaction.id.in_(_matching_transaction_ids(account_id, kind)))

    transactions_found = list(db.scalars(statement.limit(limit).offset(offset)))
    postings = _live_postings_for(db, [found.id for found in transactions_found])
    return [TransactionDetail(found, postings.get(found.id, [])) for found in transactions_found]


def update_transaction(
    db: DbSession,
    user_id: int,
    transaction_id: int,
    changes: TransactionUpdate,
) -> Transaction:
    """Apply the changes given, and nothing else.

    The accounts and the kind are fixed: a movement recorded against the wrong
    account is deleted and recorded again, which keeps the ledger's history
    honest rather than quietly rewriting where money went.
    """
    transaction = get_transaction(db, user_id, transaction_id)
    postings = _postings_of(db, transaction_id)

    if changes.transaction_date is not None:
        for posting in postings:
            account = db.get(Account, posting.account_id)
            if account is not None:
                require_on_or_after_opening(account, changes.transaction_date)
        transaction.transaction_date = changes.transaction_date

    # An omitted field is left alone; an explicit null clears it.
    if "merchant" in changes.model_fields_set:
        transaction.merchant = changes.merchant
    if "note" in changes.model_fields_set:
        transaction.note = changes.note

    if changes.amount_paise is not None:
        if len(postings) != 1:
            raise InvalidTransactionError(
                "an amount can only be changed for a transaction with one posting; "
                "delete it and record it again"
            )
        postings[0].amount_paise = _signed_amount(postings[0].kind, changes.amount_paise)

    # Filing is a property of the posting, so it too needs a single posting to
    # be unambiguous: a transfer's two sides are one movement, not two.
    if "category_id" in changes.model_fields_set:
        if len(postings) != 1:
            raise InvalidTransactionError(
                "a category can only be changed for a transaction with one posting"
            )
        postings[0].category_id = _file_under(db, user_id, changes.category_id, postings[0].kind)

    db.commit()
    return transaction


def _signed_amount(kind: PostingKind, amount_paise: int) -> int:
    """The signed amount a kind implies, so an edit cannot flip a direction."""
    if kind is PostingKind.EXPENSE:
        return -amount_paise
    if kind is PostingKind.INCOME:
        return amount_paise
    raise InvalidTransactionError(f"the amount of a {kind} cannot be changed yet")


def _matching_transaction_ids(
    account_id: int | None,
    kind: PostingKind | None,
) -> Select[int]:
    """The ids of transactions holding a posting with this account and kind."""
    statement = select(Posting.transaction_id).where(Posting.deleted_at.is_(None))
    if account_id is not None:
        statement = statement.where(Posting.account_id == account_id)
    if kind is not None:
        statement = statement.where(Posting.kind == kind)
    return statement


def _live_postings_for(
    db: DbSession,
    transaction_ids: Sequence[int],
) -> dict[int, list[Posting]]:
    """The live postings of several transactions, in one query, keyed by transaction."""
    if not transaction_ids:
        return {}

    rows = db.scalars(
        select(Posting)
        .where(
            Posting.transaction_id.in_(transaction_ids),
            Posting.deleted_at.is_(None),
        )
        .order_by(Posting.id)
    )
    grouped: dict[int, list[Posting]] = {}
    for posting in rows:
        grouped.setdefault(posting.transaction_id, []).append(posting)
    return grouped
