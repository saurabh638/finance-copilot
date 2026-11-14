"""Statements read from a file: the batch, and the rows it wrote.

One table for the batch, and two columns on `transactions` so an imported
movement can say which file wrote it and what row it came from.

The fingerprint carries the account, the date, the amount and the normalised
narration, so it identifies a row rather than its text. The unique index on it is
partial and live-only: a reversed batch soft-deletes its movements, which
releases exactly those fingerprints so the same statement can be read again.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("parser", sa.String(length=40), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("opening_paise", sa.BigInteger(), nullable=False),
        sa.Column("closing_paise", sa.BigInteger(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("rows", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="previewed", nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_import_batches_user_id"),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], name="fk_import_batches_account_id"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('previewed', 'committed', 'reversed')",
            name="ck_import_batches_status",
        ),
        sa.CheckConstraint("period_end >= period_start", name="ck_import_batches_period"),
        sa.CheckConstraint("row_count > 0", name="ck_import_batches_rows_present"),
        sa.CheckConstraint(
            "(status = 'reversed') = (reversed_at IS NOT NULL)",
            name="ck_import_batches_reversed_at",
        ),
    )
    op.create_index("ix_import_batches_user_id", "import_batches", ["user_id"])
    op.create_index("ix_import_batches_account_id", "import_batches", ["account_id"])
    op.create_index("ix_import_batches_status", "import_batches", ["status"])
    op.create_index("ix_import_batches_user_created", "import_batches", ["user_id", "created_at"])

    op.add_column("transactions", sa.Column("import_batch_id", sa.Integer(), nullable=True))
    op.add_column("transactions", sa.Column("fingerprint", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_transactions_import_batch_id",
        "transactions",
        "import_batches",
        ["import_batch_id"],
        ["id"],
    )
    op.create_index("ix_transactions_import_batch_id", "transactions", ["import_batch_id"])
    op.create_index(
        "uq_transactions_fingerprint",
        "transactions",
        ["fingerprint"],
        unique=True,
        postgresql_where=sa.text("fingerprint IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_transactions_fingerprint", table_name="transactions")
    op.drop_index("ix_transactions_import_batch_id", table_name="transactions")
    op.drop_constraint("fk_transactions_import_batch_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "fingerprint")
    op.drop_column("transactions", "import_batch_id")

    op.drop_index("ix_import_batches_user_created", table_name="import_batches")
    op.drop_index("ix_import_batches_status", table_name="import_batches")
    op.drop_index("ix_import_batches_account_id", table_name="import_batches")
    op.drop_index("ix_import_batches_user_id", table_name="import_batches")
    op.drop_table("import_batches")
