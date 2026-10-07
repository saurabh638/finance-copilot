"""Recurring items: money the user expects to repeat, and dealing with a period.

An item is a plan, not money. It says what repeats, how much, out of which
account, and on what rhythm; the calendar arithmetic that turns a rhythm into a
date lives in `app.core.recurrence`, and the writing of money lives in
`app.services.transactions`. This module is the part in between: what the daily
screen is owed, what confirming writes, and what skipping deliberately does not.

Two words are load-bearing here. An *occurrence* is one period of one item. A
period is *dealt with* when it has a skip, or a confirmation whose movement is
still live - so removing that movement on the Transactions screen brings the
period back, because the money genuinely stopped being recorded.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session as DbSession

from app.core.recurrence import Frequency, Rhythm, due_on
from app.models import (
    OccurrenceState,
    PostingKind,
    RecurringFrequency,
    RecurringItem,
    RecurringOccurrence,
    Transaction,
    TransactionSource,
)
from app.services.accounts import get_account
from app.services.transactions import (
    InvalidTransactionError,
    file_under,
    record_expense,
    record_income,
)

NAME_MAX = 80

# Only spending and earning repeat. A transfer is not a bill, and a write-off is
# not something that happens every month.
REPEATED_KINDS = (PostingKind.EXPENSE, PostingKind.INCOME)

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class RecurringItemNotFoundError(LookupError):
    """Raised when a recurring item does not exist for the user, or was removed."""


class InvalidRecurringItemError(ValueError):
    """Raised when an item would not describe something that can happen."""


class RecurringItemConflictError(ValueError):
    """Raised when the period cannot be dealt with the way it was asked for."""


@dataclass(frozen=True)
class RhythmChange:
    """A new rhythm for an item, given whole because its two halves go together."""

    frequency: RecurringFrequency
    day_of_month: int | None = None
    weekday: int | None = None


@dataclass(frozen=True)
class RecurringItemRecord:
    """One item as the API reports it."""

    id: int
    name: str
    kind: PostingKind
    amount_paise: int
    account_id: int
    category_id: int | None
    frequency: RecurringFrequency
    day_of_month: int | None
    weekday: int | None
    starts_on: date
    ends_on: date | None
    is_active: bool


@dataclass(frozen=True)
class DueItem:
    """One item owed on a day, and the day it is owed for."""

    item: RecurringItemRecord
    due_on: date


@dataclass(frozen=True)
class ConfirmedOccurrence:
    """What confirming a period wrote."""

    item: RecurringItemRecord
    due_on: date
    transaction_id: int


_FREQUENCIES: dict[RecurringFrequency, Frequency] = {
    RecurringFrequency.MONTHLY: Frequency.MONTHLY,
    RecurringFrequency.WEEKLY: Frequency.WEEKLY,
}


def _record(item: RecurringItem) -> RecurringItemRecord:
    """One item as the API reports it, from the row that keeps it."""
    return RecurringItemRecord(
        id=item.id,
        name=item.name,
        kind=item.kind,
        amount_paise=item.amount_paise,
        account_id=item.account_id,
        category_id=item.category_id,
        frequency=item.frequency,
        day_of_month=item.day_of_month,
        weekday=item.weekday,
        starts_on=item.starts_on,
        ends_on=item.ends_on,
        is_active=item.is_active,
    )


def _clean_name(name: str) -> str:
    """A name with the edges taken off, refused if there is nothing left."""
    cleaned = name.strip()
    if not cleaned:
        raise InvalidRecurringItemError("a recurring item needs a name")
    if len(cleaned) > NAME_MAX:
        raise InvalidRecurringItemError(f"a name can be at most {NAME_MAX} characters")
    return cleaned


def _require_repeated_kind(kind: PostingKind) -> None:
    if kind not in REPEATED_KINDS:
        raise InvalidRecurringItemError(
            "only spending and earning repeat; a transfer or a write-off is recorded as it happens"
        )


def _rhythm(
    frequency: RecurringFrequency,
    day_of_month: int | None,
    weekday: int | None,
) -> Rhythm:
    """The calendar rhythm an item describes, refusing one that is half given.

    A monthly item has a day of the month and no weekday, a weekly one the other
    way round. The database holds the same rule; this is where it is said in
    words the user can act on.
    """
    if frequency is RecurringFrequency.MONTHLY:
        if day_of_month is None or not 1 <= day_of_month <= 31:
            raise InvalidRecurringItemError("a monthly item needs a day of the month from 1 to 31")
        if weekday is not None:
            raise InvalidRecurringItemError("a monthly item has a day of the month, not a weekday")
        return Rhythm(Frequency.MONTHLY, day_of_month=day_of_month)

    if weekday is None or not 0 <= weekday <= 6:
        raise InvalidRecurringItemError(
            f"a weekly item needs a weekday: 0 is {WEEKDAYS[0]}, 6 is {WEEKDAYS[6]}"
        )
    if day_of_month is not None:
        raise InvalidRecurringItemError("a weekly item has a weekday, not a day of the month")
    return Rhythm(Frequency.WEEKLY, weekday=weekday)


def _rhythm_of(item: RecurringItem) -> Rhythm:
    """The rhythm a stored item describes."""
    return _rhythm(item.frequency, item.day_of_month, item.weekday)


def _filing(db: DbSession, user_id: int, category_id: int | None, kind: PostingKind) -> int | None:
    """The category an item is filed under, refused if it means something else."""
    try:
        return file_under(db, user_id, category_id, kind)
    except InvalidTransactionError as error:
        raise InvalidRecurringItemError(str(error)) from error


def _live_items(user_id: int) -> Select[RecurringItem]:
    """The user's live items. Soft-deleted rows are never returned."""
    return select(RecurringItem).where(
        RecurringItem.user_id == user_id,
        RecurringItem.deleted_at.is_(None),
    )


def get_item(db: DbSession, user_id: int, item_id: int) -> RecurringItem:
    """One live item, or a not-found error."""
    item = db.scalars(_live_items(user_id).where(RecurringItem.id == item_id)).one_or_none()
    if item is None:
        raise RecurringItemNotFoundError(f"Recurring item {item_id} does not exist")
    return item


def list_items(db: DbSession, user_id: int) -> list[RecurringItemRecord]:
    """Every live item, paused ones included, in a settled order."""
    items = db.scalars(_live_items(user_id).order_by(RecurringItem.name, RecurringItem.id))
    return [_record(item) for item in items]


def create_item(
    db: DbSession,
    user_id: int,
    *,
    name: str,
    kind: PostingKind,
    amount_paise: int,
    account_id: int,
    frequency: RecurringFrequency,
    starts_on: date,
    day_of_month: int | None = None,
    weekday: int | None = None,
    category_id: int | None = None,
    ends_on: date | None = None,
) -> RecurringItemRecord:
    """Plan something that repeats."""
    _require_repeated_kind(kind)
    if amount_paise <= 0:
        raise InvalidRecurringItemError("give an amount greater than zero")
    rhythm = _rhythm(frequency, day_of_month, weekday)
    if ends_on is not None and ends_on < starts_on:
        raise InvalidRecurringItemError("an item cannot end before it starts")

    account = get_account(db, user_id, account_id)
    item = RecurringItem(
        user_id=user_id,
        name=_clean_name(name),
        kind=kind,
        amount_paise=amount_paise,
        account_id=account.id,
        category_id=_filing(db, user_id, category_id, kind),
        frequency=frequency,
        day_of_month=rhythm.day_of_month,
        weekday=rhythm.weekday,
        starts_on=starts_on,
        ends_on=ends_on,
        is_active=True,
    )
    db.add(item)
    db.commit()
    return _record(item)


def update_item(
    db: DbSession,
    user_id: int,
    item_id: int,
    *,
    name: str | None = None,
    amount_paise: int | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
    is_filing: bool = False,
    rhythm: RhythmChange | None = None,
    starts_on: date | None = None,
    ends_on: date | None = None,
) -> RecurringItemRecord:
    """Change an item's plan, never the money it has already recorded.

    The filing is the one field where "leave it alone" and "clear it" look the
    same in a payload, so clearing is asked for by name.
    """
    item = get_item(db, user_id, item_id)

    if name is not None:
        item.name = _clean_name(name)
    if amount_paise is not None:
        if amount_paise <= 0:
            raise InvalidRecurringItemError("give an amount greater than zero")
        item.amount_paise = amount_paise
    if account_id is not None:
        item.account_id = get_account(db, user_id, account_id).id
    if is_filing:
        item.category_id = _filing(db, user_id, category_id, item.kind)
    if rhythm is not None:
        changed = _rhythm(rhythm.frequency, rhythm.day_of_month, rhythm.weekday)
        item.frequency = rhythm.frequency
        item.day_of_month = changed.day_of_month
        item.weekday = changed.weekday
    if starts_on is not None:
        item.starts_on = starts_on
    if ends_on is not None:
        item.ends_on = ends_on

    if item.ends_on is not None and item.ends_on < item.starts_on:
        raise InvalidRecurringItemError("an item cannot end before it starts")

    db.commit()
    return _record(item)


def set_active(
    db: DbSession, user_id: int, item_id: int, *, is_active: bool
) -> RecurringItemRecord:
    """Pause an item, or start it again. Paused money is not owed."""
    item = get_item(db, user_id, item_id)
    item.is_active = is_active
    db.commit()
    return _record(item)


def soft_delete_item(db: DbSession, user_id: int, item_id: int) -> None:
    """Remove an item. The periods it already dealt with keep their record."""
    item = get_item(db, user_id, item_id)
    item.deleted_at = datetime.now(UTC)
    db.commit()


def _dealt_with(db: DbSession, item_ids: list[int]) -> set[tuple[int, date]]:
    """The periods of these items that have been settled, as (item, day) pairs.

    A skip settles its period for good. A confirmation settles it only while the
    movement it points at is still there, so the join to the transaction is an
    inner one on purpose.
    """
    if not item_ids:
        return set()

    confirmed = (
        select(RecurringOccurrence.item_id, RecurringOccurrence.due_on)
        .join(Transaction, RecurringOccurrence.transaction_id == Transaction.id)
        .where(
            RecurringOccurrence.item_id.in_(item_ids),
            RecurringOccurrence.state == OccurrenceState.CONFIRMED,
            Transaction.deleted_at.is_(None),
        )
    )
    skipped = select(RecurringOccurrence.item_id, RecurringOccurrence.due_on).where(
        RecurringOccurrence.item_id.in_(item_ids),
        RecurringOccurrence.state == OccurrenceState.SKIPPED,
    )
    return set(db.execute(confirmed).all()) | set(db.execute(skipped).all())


def due_items(db: DbSession, user_id: int, on: date) -> list[DueItem]:
    """What the user owes on this day: active items, on their day, not yet settled."""
    items = list(
        db.scalars(
            _live_items(user_id)
            .where(RecurringItem.is_active.is_(True))
            .order_by(RecurringItem.name, RecurringItem.id)
        )
    )
    settled = _dealt_with(db, [item.id for item in items])

    owed: list[DueItem] = []
    for item in items:
        day = due_on(_rhythm_of(item), item.starts_on, item.ends_on, on)
        if day is None or (item.id, day) in settled:
            continue
        owed.append(DueItem(_record(item), day))
    return owed


def _occurrence(db: DbSession, item_id: int, day: date) -> RecurringOccurrence | None:
    """The one row a period of an item has, if it has one."""
    return db.scalars(
        select(RecurringOccurrence).where(
            RecurringOccurrence.item_id == item_id,
            RecurringOccurrence.due_on == day,
        )
    ).one_or_none()


def _owed_day(db: DbSession, user_id: int, item_id: int, on: date) -> tuple[RecurringItem, date]:
    """The item and the day it is owed for, or a conflict saying why not."""
    item = get_item(db, user_id, item_id)
    if not item.is_active:
        raise RecurringItemConflictError(f"{item.name} is paused, so nothing is owed")

    day = due_on(_rhythm_of(item), item.starts_on, item.ends_on, on)
    if day is None:
        raise RecurringItemConflictError(f"{item.name} is not owed on {on}")
    return item, day


def _settled_state(db: DbSession, item: RecurringItem, day: date) -> RecurringOccurrence | None:
    """Refuse a period that is already settled, and hand back its row if there is one."""
    occurrence = _occurrence(db, item.id, day)
    if occurrence is None:
        return None

    if occurrence.state is OccurrenceState.SKIPPED:
        raise RecurringItemConflictError(f"{item.name} was skipped for {day}")

    live = db.scalars(
        select(Transaction).where(
            Transaction.id == occurrence.transaction_id,
            Transaction.deleted_at.is_(None),
        )
    ).one_or_none()
    if live is not None:
        raise RecurringItemConflictError(f"{item.name} was already recorded for {day}")
    return occurrence


def confirm(
    db: DbSession,
    user_id: int,
    item_id: int,
    *,
    on: date,
    amount_paise: int | None = None,
) -> ConfirmedOccurrence:
    """Record this period's money, as one ordinary movement dated the day owed.

    The movement is dated the day the item was owed rather than the day the user
    got round to it, because that is when the money moved. Give an amount to
    record a different figure for this period only.
    """
    item, day = _owed_day(db, user_id, item_id, on)
    occurrence = _settled_state(db, item, day)

    amount = item.amount_paise if amount_paise is None else amount_paise
    if amount <= 0:
        raise InvalidRecurringItemError("give an amount greater than zero")

    if item.kind is PostingKind.INCOME:
        transaction = record_income(
            db,
            user_id,
            item.account_id,
            amount,
            day,
            merchant=item.name,
            category_id=item.category_id,
            source=TransactionSource.RECURRING,
        )
    else:
        transaction = record_expense(
            db,
            user_id,
            item.account_id,
            amount,
            day,
            merchant=item.name,
            category_id=item.category_id,
            source=TransactionSource.RECURRING,
        )

    if occurrence is None:
        db.add(
            RecurringOccurrence(
                item_id=item.id,
                due_on=day,
                state=OccurrenceState.CONFIRMED,
                transaction_id=transaction.id,
            )
        )
    else:
        occurrence.transaction_id = transaction.id
    db.commit()

    return ConfirmedOccurrence(_record(item), day, transaction.id)


def skip(db: DbSession, user_id: int, item_id: int, *, on: date) -> DueItem:
    """Say this period is not happening. Nothing is recorded at all."""
    item, day = _owed_day(db, user_id, item_id, on)
    occurrence = _settled_state(db, item, day)

    if occurrence is None:
        db.add(
            RecurringOccurrence(
                item_id=item.id,
                due_on=day,
                state=OccurrenceState.SKIPPED,
                transaction_id=None,
            )
        )
    else:
        occurrence.state = OccurrenceState.SKIPPED
        occurrence.transaction_id = None
    db.commit()

    return DueItem(_record(item), day)
