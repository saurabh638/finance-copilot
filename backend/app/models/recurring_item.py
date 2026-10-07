"""RecurringItem model: money the user expects to repeat, waiting to be confirmed."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import PostingKind, RecurringFrequency, enum_values


class RecurringItem(TimestampMixin, Base):
    """One thing that repeats: rent, an EMI, a subscription, a salary.

    This row is a plan, not money. Nothing here touches a balance: confirming an
    item writes an ordinary transaction, and this is only what the daily screen
    offers. The rhythm is stored as a frequency plus the day it lands on, and the
    arithmetic that turns that into a date lives in `app.core.recurrence`.

    Only spending and earning repeat. A transfer between the user's own accounts
    is not a bill, and a write-off is not something that happens every month.
    """

    __tablename__ = "recurring_items"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_recurring_items_amount_positive"),
        CheckConstraint(
            "kind IN ('expense', 'income')",
            name="ck_recurring_items_kind",
        ),
        # A monthly item has a day of the month and no weekday; a weekly one has a
        # weekday and no day of the month. The `IS NOT NULL` halves are what make
        # the constraint bite: a CHECK passes on null, so without them a monthly
        # item with no day would slip through.
        CheckConstraint(
            "(frequency = 'monthly' AND day_of_month IS NOT NULL"
            " AND day_of_month BETWEEN 1 AND 31 AND weekday IS NULL)"
            " OR (frequency = 'weekly' AND weekday IS NOT NULL"
            " AND weekday BETWEEN 0 AND 6 AND day_of_month IS NULL)",
            name="ck_recurring_items_rhythm",
        ),
        CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on",
            name="ck_recurring_items_dates",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # The name is what the user calls it, and what the recorded transaction's
    # merchant becomes, so the ledger reads "Rent" rather than a description.
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[PostingKind] = mapped_column(
        SqlEnum(
            PostingKind,
            native_enum=False,
            length=20,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True, index=True
    )
    frequency: Mapped[RecurringFrequency] = mapped_column(
        SqlEnum(
            RecurringFrequency,
            native_enum=False,
            length=20,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Monday is 0 through Sunday is 6, the way Python counts them.
    weekday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
