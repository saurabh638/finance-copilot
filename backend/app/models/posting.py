"""Posting model: one account's side of a transaction. Money is signed paise."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import PostingKind, allowed_values, enum_values


class Posting(TimestampMixin, Base):
    """One account's side of one transaction.

    The amount is the signed change to that account's balance: an expense on a
    savings account is negative, a card purchase is negative on the card so its
    outstanding grows, and the two sides of a transfer are equal and opposite.
    `kind` is what analytics reads; the sign is what the balance reads.
    """

    __tablename__ = "postings"
    __table_args__ = (
        CheckConstraint("amount_paise <> 0", name="ck_postings_amount_not_zero"),
        CheckConstraint(allowed_values("kind", PostingKind), name="ck_postings_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[PostingKind] = mapped_column(
        SqlEnum(
            PostingKind,
            native_enum=False,
            length=20,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
