"""RecurringOccurrence model: what happened to one period of a recurring item."""

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import OccurrenceState, enum_values


class RecurringOccurrence(TimestampMixin, Base):
    """One period of one recurring item, and whether it was dealt with.

    A row per period is what makes "already dealt with" an invariant the database
    holds rather than something the screen has to remember: a monthly item has at
    most one occurrence per month, a weekly one at most one per week.

    This is a log, so it is never soft-deleted. A confirmation is a *pointer* at
    the transaction that recorded the money, not a copy of it, which is why the
    transaction can be removed on the Transactions screen and the item simply
    comes back as owed - the money really did stop being recorded. A skip has no
    transaction to point at, and the row itself is the whole record of it.
    """

    __tablename__ = "recurring_occurrences"
    __table_args__ = (
        CheckConstraint(
            "(state = 'confirmed' AND transaction_id IS NOT NULL)"
            " OR (state = 'skipped' AND transaction_id IS NULL)",
            name="ck_recurring_occurrences_transaction",
        ),
        Index("uq_recurring_occurrences_item_due", "item_id", "due_on", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("recurring_items.id"), nullable=False, index=True
    )
    # The day the item was owed, not the day it was confirmed: an item confirmed
    # late is still this period's.
    due_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    state: Mapped[OccurrenceState] = mapped_column(
        SqlEnum(
            OccurrenceState,
            native_enum=False,
            length=20,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True, index=True
    )
