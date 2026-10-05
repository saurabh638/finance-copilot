"""BalanceCheck model: one record of the ledger being compared with the bank."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BalanceCheck(TimestampMixin, Base):
    """One balance check: what the ledger said, what the bank said, and the gap.

    The figures are recorded as they were at the time of the check, so a check
    can always be explained afterwards even though the credit card, the bank or
    the ledger have moved on since. `adjustment_posting_id` is set only when the
    user chose to write the difference off, and it points at the posting that did
    it - never a silent change to a balance, because there is no stored balance
    to change.
    """

    __tablename__ = "balance_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    # The day the balance was checked, which is also the adjustment's date.
    checked_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    computed_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stated_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Stated minus computed: the amount a write-off has to post, signed.
    difference_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    adjustment_posting_id: Mapped[int | None] = mapped_column(
        ForeignKey("postings.id"), nullable=True, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
