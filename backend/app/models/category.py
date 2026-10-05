"""Category model: a two-level tree of names that money can be filed under."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import CategoryKind, allowed_values, enum_values


class Category(TimestampMixin, Base):
    """One name money is filed under, at most two levels deep.

    A top-level category carries the kind, and a child always carries its
    parent's, so a name can never mean spending in one place and income in
    another. Nothing is hard-deleted: a removed category stops being offered,
    and the postings that pointed at it keep pointing at it.
    """

    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint(allowed_values("kind", CategoryKind), name="ck_categories_kind"),
        # One live category per name under a parent. Partial, so a name can be
        # used again after one is removed; NULLS NOT DISTINCT, because two
        # top-level categories are two rows whose parent is null, and Postgres
        # treats nulls as different from each other unless told otherwise.
        Index(
            "uq_categories_user_parent_name",
            "user_id",
            "parent_id",
            "name",
            unique=True,
            postgresql_nulls_not_distinct=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True, index=True
    )
    kind: Mapped[CategoryKind] = mapped_column(
        SqlEnum(
            CategoryKind,
            native_enum=False,
            length=20,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
