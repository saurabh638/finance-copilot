"""ImportBatch model: one statement that was read in, and what it produced.

A batch is a *preview* until it is committed. The parsed rows are stored exactly as
they were read, so the preview can be shown, questioned and committed without the
file being uploaded twice, and so what was committed can still be checked later.

Nothing is written from a batch that does not reconcile: the file's own arithmetic
has to add up, and the ledger has to agree with the closing balance the statement
prints. And a batch is undone whole rather than row by row, which is why every
transaction it writes carries its `import_batch_id`.
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ImportStatus, allowed_values, enum_values


class ImportBatch(TimestampMixin, Base):
    """One statement read from a file, and the movements it is allowed to write.

    The figures are kept as the statement printed them: `opening_paise` and
    `closing_paise` are the bank's own, in this ledger's sign convention, which is
    also what the batch is checked against before anything is written.
    """

    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint(allowed_values("status", ImportStatus), name="ck_import_batches_status"),
        CheckConstraint("period_end >= period_start", name="ck_import_batches_period"),
        CheckConstraint("row_count > 0", name="ck_import_batches_rows_present"),
        # A reversed batch is dated and every other batch is not, so "when was this
        # undone" cannot be a column that is sometimes a lie.
        CheckConstraint(
            "(status = 'reversed') = (reversed_at IS NOT NULL)",
            name="ck_import_batches_reversed_at",
        ),
        Index("ix_import_batches_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    # What was uploaded, and which reader understood it.
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    parser: Mapped[str] = mapped_column(String(40), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    opening_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    closing_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    row_count: Mapped[int] = mapped_column(nullable=False)
    # The rows as they were read: dates as ISO strings, amounts as paise, and the
    # narration as the bank wrote it. Stored rather than re-parsed so the preview
    # and the commit are the same reading.
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    status: Mapped[ImportStatus] = mapped_column(
        SqlEnum(
            ImportStatus,
            native_enum=False,
            length=20,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default=ImportStatus.PREVIEWED.value,
        index=True,
    )
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
