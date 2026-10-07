"""Recurring items and the periods they come round in.

Two tables. `recurring_items` is the plan: what repeats, how much, on which
account and on what rhythm. `recurring_occurrences` is what happened to each
period, one row per period thanks to a unique index, so "this month's rent was
already dealt with" is something the database cannot forget. The occurrence
points at the transaction that recorded the money rather than copying it, and a
skip points at nothing.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-06 16:47:22.631702

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "recurring_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "expense",
                "income",
                "transfer",
                "adjustment",
                "interest",
                "fee",
                "investment",
                name="postingkind",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column(
            "frequency",
            sa.Enum(
                "monthly",
                "weekly",
                name="recurringfrequency",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("weekday", sa.Integer(), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.CheckConstraint("amount_paise > 0", name="ck_recurring_items_amount_positive"),
        sa.CheckConstraint("kind IN ('expense', 'income')", name="ck_recurring_items_kind"),
        sa.CheckConstraint(
            "(frequency = 'monthly' AND day_of_month IS NOT NULL"
            " AND day_of_month BETWEEN 1 AND 31 AND weekday IS NULL)"
            " OR (frequency = 'weekly' AND weekday IS NOT NULL"
            " AND weekday BETWEEN 0 AND 6 AND day_of_month IS NULL)",
            name="ck_recurring_items_rhythm",
        ),
        sa.CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on",
            name="ck_recurring_items_dates",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], name="fk_recurring_items_account_id_accounts"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name="fk_recurring_items_category_id_categories"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_recurring_items_user_id_users"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_recurring_items_account_id"), "recurring_items", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_recurring_items_category_id"), "recurring_items", ["category_id"], unique=False
    )
    op.create_index(
        op.f("ix_recurring_items_user_id"), "recurring_items", ["user_id"], unique=False
    )
    op.create_table(
        "recurring_occurrences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "confirmed",
                "skipped",
                name="occurrencestate",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
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
        sa.CheckConstraint(
            "(state = 'confirmed' AND transaction_id IS NOT NULL)"
            " OR (state = 'skipped' AND transaction_id IS NULL)",
            name="ck_recurring_occurrences_transaction",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["recurring_items.id"],
            name="fk_recurring_occurrences_item_id_recurring_items",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name="fk_recurring_occurrences_transaction_id_transactions",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_recurring_occurrences_due_on"), "recurring_occurrences", ["due_on"], unique=False
    )
    op.create_index(
        op.f("ix_recurring_occurrences_item_id"),
        "recurring_occurrences",
        ["item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recurring_occurrences_transaction_id"),
        "recurring_occurrences",
        ["transaction_id"],
        unique=False,
    )
    # One period per item, ever: the month a monthly item was confirmed in cannot
    # be confirmed again while that confirmation stands.
    op.create_index(
        "uq_recurring_occurrences_item_due",
        "recurring_occurrences",
        ["item_id", "due_on"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_recurring_occurrences_item_due", table_name="recurring_occurrences")
    op.drop_index(
        op.f("ix_recurring_occurrences_transaction_id"), table_name="recurring_occurrences"
    )
    op.drop_index(op.f("ix_recurring_occurrences_item_id"), table_name="recurring_occurrences")
    op.drop_index(op.f("ix_recurring_occurrences_due_on"), table_name="recurring_occurrences")
    op.drop_table("recurring_occurrences")
    op.drop_index(op.f("ix_recurring_items_user_id"), table_name="recurring_items")
    op.drop_index(op.f("ix_recurring_items_category_id"), table_name="recurring_items")
    op.drop_index(op.f("ix_recurring_items_account_id"), table_name="recurring_items")
    op.drop_table("recurring_items")
