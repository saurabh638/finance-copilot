"""InterestCredit model: one period of interest, worked out and then paid."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class InterestCredit(TimestampMixin, Base):
    """One stretch of constant rate inside one crediting period.

    A row begins life as a *proposal*: the engine has worked out what the period
    earned and nothing has been posted. Confirming it posts one `interest` posting
    and fills in the three confirmation columns.

    Both figures are kept. `computed_paise` is what the ledger's arithmetic said,
    and `credited_paise` is what the bank actually paid: a difference between them
    is the one place the stated day-count convention can be seen to be wrong, and
    overwriting it with the bank's figure would hide exactly that.

    A period that earned nothing gets no row at all. There is nothing to confirm,
    and a zero posting would not balance anything.
    """

    __tablename__ = "interest_credits"
    __table_args__ = (
        CheckConstraint("period_end >= period_start", name="ck_interest_credits_period"),
        CheckConstraint("rate_percent >= 0", name="ck_interest_credits_rate_non_negative"),
        CheckConstraint("computed_paise > 0", name="ck_interest_credits_computed_positive"),
        CheckConstraint(
            "credited_paise IS NULL OR credited_paise > 0",
            name="ck_interest_credits_credited_positive",
        ),
        # A proposal has no confirmation and a confirmed row has all three of its
        # marks: a half-confirmed row would be a posting nobody could explain.
        CheckConstraint(
            "(credited_paise IS NULL AND transaction_id IS NULL AND confirmed_on IS NULL)"
            " OR (credited_paise IS NOT NULL AND transaction_id IS NOT NULL"
            " AND confirmed_on IS NOT NULL)",
            name="ck_interest_credits_confirmation",
        ),
        # One proposal per account per period per rate stretch. Partial, so a
        # proposal that was dropped can be worked out again.
        Index(
            "uq_interest_credits_account_period",
            "account_id",
            "period_start",
            "period_end",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    # The rate in force over this stretch, exactly as the rate record holds it, so
    # the row says what produced its figure without a join.
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    computed_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    credited_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True, index=True
    )
    confirmed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
