"""Transaction model: the container that holds one or more postings."""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import TransactionSource, allowed_values, enum_values


class Transaction(TimestampMixin, Base):
    """One movement of money, as the user sees it.

    The postings hang off it and carry the amounts: one posting for an expense or
    an income, two that sum to zero for a transfer. `source` records how it got
    here, so an imported batch can be reversed whole later.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            allowed_values("source", TransactionSource),
            name="ck_transactions_source",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # The bank's own date, when it differs from the day the money moved.
    posted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    merchant: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # The statement's own words, kept for imports and never shown as the merchant.
    raw_narration: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[TransactionSource] = mapped_column(
        SqlEnum(
            TransactionSource,
            native_enum=False,
            length=20,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
