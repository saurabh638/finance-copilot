"""Interest rate model: dated rates per account. History is kept, never overwritten."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import RateFrequency, allowed_values, enum_values


class InterestRate(TimestampMixin, Base):
    """One dated rate for one account.

    A rate change adds a row. Nothing in this table is ever updated in place, so
    the history of what a bank paid, and when, survives. `account_id` is where
    ownership lives: rates are reached through their account.
    """

    __tablename__ = "interest_rates"
    __table_args__ = (
        CheckConstraint("rate >= 0", name="ck_interest_rates_rate_non_negative"),
        CheckConstraint(
            allowed_values("frequency", RateFrequency),
            name="ck_interest_rates_frequency",
        ),
        # One live rate per start date. Partial, so a mistaken record can be
        # soft-deleted and the same date added again.
        Index(
            "uq_interest_rates_account_from_date",
            "account_id",
            "from_date",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    # Per cent per annum, exact: NUMERIC(7, 4) keeps four decimal places and no float.
    rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    frequency: Mapped[RateFrequency] = mapped_column(
        SqlEnum(
            RateFrequency,
            native_enum=False,
            length=20,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
