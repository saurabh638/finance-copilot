"""Categories: the two-level tree of names money is filed under.

The tree is deliberately shallow. Two levels are enough to answer "what did I
spend on?" without turning into a filing system nobody maintains, and a fixed
depth is a rule the database and the service can both state plainly.

Seeding is skip-not-update: it creates what is missing and never renames,
re-parents or resurrects anything. A category the user edited or removed is a
decision, not a gap to be filled in again.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session as DbSession

from app.core.ledger import roll_up
from app.core.money import add_paise
from app.models import Category, CategoryKind, Posting, PostingKind, Transaction

NAME_MAX = 80

# The write-off names M9 promised would arrive with categories. Their kind is
# `adjustment`, so they can be offered where a write-off is posted without ever
# counting as spending or income.
UNACCOUNTED = "Unaccounted for spending"
UNRECORDED_INCOME = "Unrecorded income"


class CategoryNotFoundError(LookupError):
    """Raised when a category does not exist for the user, or is soft-deleted."""


class InvalidCategoryError(ValueError):
    """Raised when a category would break the shape of the tree."""


class CategoryInUseError(ValueError):
    """Raised when something still points at a category that cannot be removed."""


KIND_WORDS: dict[CategoryKind, str] = {
    CategoryKind.EXPENSE: "spending",
    CategoryKind.INCOME: "earning",
    CategoryKind.ADJUSTMENT: "write-offs",
}


def kind_word(kind: CategoryKind) -> str:
    """How a category's kind reads in a sentence."""
    return KIND_WORDS[kind]


@dataclass(frozen=True)
class CategorySpend:
    """One row of the spend report: what a category holds, and all of its own.

    `id` and the fields beside it are the category as the API returns it, so a
    client can draw the same tree it already has and read the figures off it.
    """

    id: int
    name: str
    parent_id: int | None
    kind: CategoryKind
    direct_paise: int
    total_paise: int


@dataclass(frozen=True)
class DefaultGroup:
    """One top-level category and the names under it, which may be none."""

    name: str
    kind: CategoryKind
    children: tuple[str, ...]


# A recognisable starting set for an Indian household: the shape matters more
# than the names, because every part of it can be renamed, moved or removed.
DEFAULT_TREE: tuple[DefaultGroup, ...] = (
    DefaultGroup(
        "Food & groceries",
        CategoryKind.EXPENSE,
        ("Groceries", "Eating out", "Food delivery"),
    ),
    DefaultGroup(
        "Transport",
        CategoryKind.EXPENSE,
        ("Fuel", "Cab & auto", "Public transport", "Vehicle upkeep"),
    ),
    DefaultGroup(
        "Home",
        CategoryKind.EXPENSE,
        (
            "Rent",
            "Electricity",
            "Water & gas",
            "Internet & phone",
            "Repairs",
            "Household help",
        ),
    ),
    DefaultGroup(
        "Health",
        CategoryKind.EXPENSE,
        ("Medicines", "Doctor & hospital", "Insurance premium"),
    ),
    DefaultGroup(
        "Education",
        CategoryKind.EXPENSE,
        ("School fees", "Books & supplies", "Courses"),
    ),
    DefaultGroup("Family & giving", CategoryKind.EXPENSE, ("Gifts", "Donations", "Festivals")),
    DefaultGroup("Shopping", CategoryKind.EXPENSE, ("Clothes", "Electronics", "Home supplies")),
    DefaultGroup(
        "Lifestyle",
        CategoryKind.EXPENSE,
        ("Subscriptions", "Entertainment", "Travel", "Personal care"),
    ),
    DefaultGroup(
        "Financial",
        CategoryKind.EXPENSE,
        ("Investments", "Loan EMI", "Card interest & fees", "Bank charges"),
    ),
    DefaultGroup("Salary", CategoryKind.INCOME, ()),
    DefaultGroup("Freelance", CategoryKind.INCOME, ()),
    DefaultGroup("Interest", CategoryKind.INCOME, ()),
    DefaultGroup("Dividends", CategoryKind.INCOME, ()),
    DefaultGroup("Refunds & cashback", CategoryKind.INCOME, ()),
    DefaultGroup("Rental income", CategoryKind.INCOME, ()),
    DefaultGroup("Gifts received", CategoryKind.INCOME, ()),
    DefaultGroup(UNACCOUNTED, CategoryKind.ADJUSTMENT, ()),
    DefaultGroup(UNRECORDED_INCOME, CategoryKind.ADJUSTMENT, ()),
)


def _live_categories(user_id: int) -> Select[Category]:
    """The user's live categories. Soft-deleted rows are never offered."""
    return select(Category).where(
        Category.user_id == user_id,
        Category.deleted_at.is_(None),
    )


def list_categories(db: DbSession, user_id: int) -> list[Category]:
    """The user's categories: each branch, then the names filed under it."""
    rows = list(db.scalars(_live_categories(user_id).order_by(Category.name, Category.id)))
    branches = [row for row in rows if row.parent_id is None]

    children: dict[int, list[Category]] = {}
    for row in rows:
        if row.parent_id is not None:
            children.setdefault(row.parent_id, []).append(row)

    ordered: list[Category] = []
    for branch in branches:
        ordered.append(branch)
        ordered.extend(children.pop(branch.id, []))

    # A name whose branch was removed is still live, so it is listed rather than
    # hidden: money filed under it must stay readable.
    for leftover in children.values():
        ordered.extend(leftover)
    return ordered


def spend_by_category(
    db: DbSession,
    user_id: int,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[CategorySpend]:
    """What was spent under each expense category in a period, children rolled in.

    Spending is the expense postings filed under a category: income is not
    spending, a transfer spends nothing, and a write-off has its own report. The
    figures come from the postings rather than from any stored total, so a
    correction to a movement shows up here the moment it is made. Spending filed
    under no category is counted nowhere, because there is no row for it.
    """
    rows = db.execute(_live_spending(user_id, from_date, to_date))
    direct: dict[int, int] = {}
    for category_id, amount_paise in rows:
        # The query already excludes filings with no category; saying so again
        # keeps that a fact the types can read as well.
        if category_id is not None:
            # Postings of an expense are negative; the report speaks in magnitudes.
            direct[category_id] = add_paise(direct.get(category_id, 0), -amount_paise)

    categories = [row for row in list_categories(db, user_id) if row.kind is CategoryKind.EXPENSE]
    totals = roll_up({row.id: row.parent_id for row in categories}, direct)

    return [
        CategorySpend(
            id=row.id,
            name=row.name,
            parent_id=row.parent_id,
            kind=row.kind,
            direct_paise=direct.get(row.id, 0),
            total_paise=totals.get(row.id, 0),
        )
        for row in categories
    ]


def _live_spending(
    user_id: int, from_date: date | None, to_date: date | None
) -> Select[int | None, int]:
    """One row per live expense posting filed under a category: that category, and
    the amount as it was recorded."""
    statement = (
        select(Posting.category_id, Posting.amount_paise)
        .join(Transaction, Posting.transaction_id == Transaction.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
            Posting.deleted_at.is_(None),
            Posting.kind == PostingKind.EXPENSE,
            Posting.category_id.is_not(None),
        )
    )
    if from_date is not None:
        statement = statement.where(Transaction.transaction_date >= from_date)
    if to_date is not None:
        statement = statement.where(Transaction.transaction_date <= to_date)
    return statement


def seed_defaults(db: DbSession, user_id: int) -> list[Category]:
    """Create the default set for a user whose tree is empty.

    This runs once, on an empty tree. A tree that already has anything in it is
    the user's own work - renamed, re-parented, removed - and filling in the gaps
    would undo decisions rather than help. Running it twice therefore does
    nothing the second time.
    """
    anything = db.scalars(select(Category.id).where(Category.user_id == user_id)).first()
    if anything is not None:
        return []

    created: list[Category] = []
    for group in DEFAULT_TREE:
        branch = Category(
            user_id=user_id,
            name=group.name,
            parent_id=None,
            kind=group.kind,
        )
        db.add(branch)
        db.flush()
        created.append(branch)

        for child in group.children:
            made = Category(
                user_id=user_id,
                name=child,
                parent_id=branch.id,
                kind=group.kind,
            )
            db.add(made)
            created.append(made)

    db.commit()
    return created


def get_category(db: DbSession, user_id: int, category_id: int) -> Category:
    """Return one live category, or raise CategoryNotFoundError."""
    found = db.scalars(_live_categories(user_id).where(Category.id == category_id)).first()
    if found is None:
        raise CategoryNotFoundError(category_id)
    return found


def find_by_name(db: DbSession, user_id: int, name: str, kind: CategoryKind) -> Category | None:
    """A live category with this exact name and kind, or None.

    For names that are a convention rather than a requirement, such as the
    balance check's write-off names: those are the user's to rename or remove,
    so a missing one is an answer here rather than an error. A top-level name
    wins, because that is where the tree puts its own.
    """
    statement = _live_categories(user_id).where(Category.name == name, Category.kind == kind)
    top_level = db.scalars(statement.where(Category.parent_id.is_(None))).first()
    if top_level is not None:
        return top_level
    return db.scalars(statement.order_by(Category.id)).first()


def _clean_name(name: str) -> str:
    """The one place a name is trimmed and checked."""
    cleaned = name.strip()
    if cleaned == "":
        raise InvalidCategoryError("a category needs a name")
    if len(cleaned) > NAME_MAX:
        raise InvalidCategoryError(f"keep the name under {NAME_MAX} characters")
    return cleaned


def _require_free_name(
    db: DbSession,
    user_id: int,
    name: str,
    parent_id: int | None,
    ignoring_id: int | None = None,
) -> None:
    """A name has to be free among its live siblings, at the top level included."""
    statement = select(Category.id).where(
        Category.user_id == user_id,
        Category.name == name,
        Category.deleted_at.is_(None),
    )
    statement = (
        statement.where(Category.parent_id.is_(None))
        if parent_id is None
        else statement.where(Category.parent_id == parent_id)
    )
    if ignoring_id is not None:
        statement = statement.where(Category.id != ignoring_id)
    if db.scalars(statement).first() is not None:
        raise InvalidCategoryError(f"{name} is already used here")


def create_category(
    db: DbSession,
    user_id: int,
    name: str,
    *,
    kind: CategoryKind | None,
    parent_id: int | None = None,
) -> Category:
    """Add a name to the tree: a branch of its own, or a child of one.

    A top-level category says what it is for; a child never does, because it
    carries its parent's kind, so a name cannot mean spending in one place and
    income in another.
    """
    cleaned = _clean_name(name)

    if parent_id is None:
        if kind is None:
            raise InvalidCategoryError("a top-level category needs a kind")
        parent = None
    else:
        parent = get_category(db, user_id, parent_id)
        if parent.parent_id is not None:
            raise InvalidCategoryError("categories go two levels deep, no further")
        if kind is not None and kind is not parent.kind:
            raise InvalidCategoryError(f"a child of {parent.name} carries its parent's kind")
        kind = parent.kind

    _require_free_name(db, user_id, cleaned, parent.id if parent is not None else None)

    made = Category(
        user_id=user_id, name=cleaned, parent_id=parent.id if parent else None, kind=kind
    )
    db.add(made)
    db.commit()
    return made


def update_category(
    db: DbSession,
    user_id: int,
    category_id: int,
    *,
    name: str | None = None,
    move_to_parent_id: int | None = None,
    is_moving: bool = False,
) -> Category:
    """Rename a category, move it in the tree, or both.

    Moving is asked for explicitly, so that "no parent given" can mean the top
    level rather than "leave it where it is". A category may only move if it is a
    leaf: a branch with children underneath would create a third level, and that
    is the one shape this tree will not take.
    """
    category = get_category(db, user_id, category_id)

    if name is not None:
        cleaned = _clean_name(name)
        _require_free_name(db, user_id, cleaned, category.parent_id, ignoring_id=category.id)
        category.name = cleaned

    if is_moving:
        if move_to_parent_id == category.id:
            raise InvalidCategoryError("a category cannot sit under itself")

        has_children = db.scalars(
            select(Category.id).where(
                Category.parent_id == category.id, Category.deleted_at.is_(None)
            )
        ).first()
        if has_children is not None and move_to_parent_id is not None:
            raise InvalidCategoryError(f"{category.name} has categories under it; move those first")

        if move_to_parent_id is None:
            category.parent_id = None
        else:
            parent = get_category(db, user_id, move_to_parent_id)
            if parent.parent_id is not None:
                raise InvalidCategoryError("categories go two levels deep, no further")
            _require_free_name(db, user_id, category.name, parent.id, ignoring_id=category.id)
            category.parent_id = parent.id
            # The kind follows the tree, so a name never changes meaning.
            category.kind = parent.kind

    db.commit()
    return category


def remove_category(db: DbSession, user_id: int, category_id: int) -> None:
    """Soft-delete a category that is not holding anything.

    A branch with live children, or a category with movements filed under it, is
    refused: removing it would leave either orphans or money with no name. The
    fix is the user's - move the children, or re-categorise the movements.
    """
    category = get_category(db, user_id, category_id)

    child = db.scalars(
        select(Category).where(Category.parent_id == category.id, Category.deleted_at.is_(None))
    ).first()
    if child is not None:
        raise CategoryInUseError(f"{child.name} is filed under {category.name}")

    filed = db.scalars(
        select(func.count())
        .select_from(Posting)
        .where(Posting.category_id == category.id, Posting.deleted_at.is_(None))
    ).one()
    if filed > 0:
        raise CategoryInUseError(
            f"{filed} movement{'s' if filed != 1 else ''} are filed under {category.name}"
        )

    category.deleted_at = datetime.now(UTC)
    db.commit()
