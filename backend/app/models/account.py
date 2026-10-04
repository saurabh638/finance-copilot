"""Account model: the banks, cards, wallets and pots money lives in."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import AccountType, CaptureMode, allowed_values, enum_values


class Account(TimestampMixin, Base):
    """One account. A pot is a child row pointing at a non-pot parent."""

    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(allowed_values("type", AccountType), name="ck_accounts_type"),
        CheckConstraint(
            allowed_values("capture_mode", CaptureMode),
            name="ck_accounts_capture_mode",
        ),
        CheckConstraint(
            "type = 'pot' AND parent_id IS NOT NULL OR type <> 'pot' AND parent_id IS NULL",
            name="ck_accounts_pot_needs_parent",
        ),
        CheckConstraint(
            "statement_day IS NULL OR statement_day BETWEEN 1 AND 31",
            name="ck_accounts_statement_day_range",
        ),
        CheckConstraint(
            "due_day IS NULL OR due_day BETWEEN 1 AND 31",
            name="ck_accounts_due_day_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[AccountType] = mapped_column(
        SqlEnum(
            AccountType,
            native_enum=False,
            length=20,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    purpose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capture_mode: Mapped[CaptureMode] = mapped_column(
        SqlEnum(
            CaptureMode,
            native_enum=False,
            length=20,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    opening_balance_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    opening_date: Mapped[date] = mapped_column(Date, nullable=False)
    statement_day: Mapped[int | None] = mapped_column(nullable=True)
    due_day: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
