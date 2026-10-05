"""categories

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-05 17:46:02.713634

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "expense",
                "income",
                "adjustment",
                name="categorykind",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "kind IN ('expense', 'income', 'adjustment')",
            name="ck_categories_kind",
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_categories_parent_id"), "categories", ["parent_id"], unique=False)
    op.create_index(op.f("ix_categories_user_id"), "categories", ["user_id"], unique=False)
    # One live name per parent, and one per top level: NULLS NOT DISTINCT so that
    # two top-level categories cannot share a name either, since their parent is
    # null in both rows and Postgres treats nulls as different by default.
    op.create_index(
        "uq_categories_user_parent_name",
        "categories",
        ["user_id", "parent_id", "name"],
        unique=True,
        postgresql_nulls_not_distinct=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.add_column("postings", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_postings_category_id"), "postings", ["category_id"], unique=False)
    op.create_foreign_key(
        "fk_postings_category_id_categories",
        "postings",
        "categories",
        ["category_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_postings_category_id_categories", "postings", type_="foreignkey")
    op.drop_index(op.f("ix_postings_category_id"), table_name="postings")
    op.drop_column("postings", "category_id")
    op.drop_index(
        "uq_categories_user_parent_name",
        table_name="categories",
        postgresql_nulls_not_distinct=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_categories_user_id"), table_name="categories")
    op.drop_index(op.f("ix_categories_parent_id"), table_name="categories")
    op.drop_table("categories")
