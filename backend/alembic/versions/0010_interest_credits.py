"""Interest credits, and the periods they cover.

One table. A row is a proposal until the user confirms the figure the bank
credited, at which point it points at the posting that recorded it. Both figures
are kept, so a bank that divides by 366 instead of 365 - or rounds differently -
shows up as a difference in the data rather than being silently overwritten by
whichever figure was written last.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "interest_credits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("rate_percent", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("computed_paise", sa.BigInteger(), nullable=False),
        sa.Column("credited_paise", sa.BigInteger(), nullable=True),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column("confirmed_on", sa.Date(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("period_end >= period_start", name="ck_interest_credits_period"),
        sa.CheckConstraint("rate_percent >= 0", name="ck_interest_credits_rate_non_negative"),
        sa.CheckConstraint("computed_paise > 0", name="ck_interest_credits_computed_positive"),
        sa.CheckConstraint(
            "credited_paise IS NULL OR credited_paise > 0",
            name="ck_interest_credits_credited_positive",
        ),
        sa.CheckConstraint(
            "(credited_paise IS NULL AND transaction_id IS NULL AND confirmed_on IS NULL)"
            " OR (credited_paise IS NOT NULL AND transaction_id IS NOT NULL"
            " AND confirmed_on IS NOT NULL)",
            name="ck_interest_credits_confirmation",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], name="fk_interest_credits_account_id_accounts"
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name="fk_interest_credits_transaction_id_transactions",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_interest_credits_account_id"), "interest_credits", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_interest_credits_transaction_id"),
        "interest_credits",
        ["transaction_id"],
        unique=False,
    )
    # One live proposal per account per period per rate stretch; partial, so a
    # proposal that was dropped can be worked out again.
    op.create_index(
        "uq_interest_credits_account_period",
        "interest_credits",
        ["account_id", "period_start", "period_end"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_interest_credits_account_period", table_name="interest_credits")
    op.drop_index(op.f("ix_interest_credits_transaction_id"), table_name="interest_credits")
    op.drop_index(op.f("ix_interest_credits_account_id"), table_name="interest_credits")
    op.drop_table("interest_credits")
