"""A short alias an account answers to.

One optional column, so `hdfc` can mean the credit card in a typed line without
renaming the account. A word means one account: a partial functional unique index
compares aliases without case and only among live rows, so a soft-deleted account
releases its word. The clash with another account's *name* is a service rule
rather than an index, because names are deliberately free to repeat.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("accounts", sa.Column("alias", sa.String(length=40), nullable=True))
    op.create_check_constraint(
        "ck_accounts_alias_trimmed",
        "accounts",
        "alias IS NULL OR (alias = btrim(alias) AND alias <> '')",
    )
    op.create_index(
        "uq_accounts_alias",
        "accounts",
        ["user_id", sa.text("lower(alias)")],
        unique=True,
        postgresql_where=sa.text("alias IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_accounts_alias", table_name="accounts")
    op.drop_constraint("ck_accounts_alias_trimmed", "accounts", type_="check")
    op.drop_column("accounts", "alias")
