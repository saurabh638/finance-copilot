"""Tests for the category tree and the seeded default set.

The default set is data, so it is checked as data first: two levels, no duplicate
names, and a kind on every branch. Then the seeding rules, which are the ones
that decide whether running it twice is safe.
"""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, Category, CategoryKind, Posting, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.categories import (
    DEFAULT_TREE,
    CategoryInUseError,
    CategoryNotFoundError,
    InvalidCategoryError,
    create_category,
    get_category,
    list_categories,
    remove_category,
    seed_defaults,
    update_category,
)
from app.services.transactions import record_expense

ADJUSTMENT_NAMES = {"Unaccounted for spending", "Unrecorded income"}


def _all_names() -> list[str]:
    names: list[str] = []
    for group in DEFAULT_TREE:
        names.append(group.name)
        names.extend(group.children)
    return names


def test_the_default_set_has_no_duplicate_names() -> None:
    names = _all_names()

    assert len(names) == len(set(names))


def test_every_default_group_is_a_branch_with_a_name() -> None:
    for group in DEFAULT_TREE:
        assert group.name.strip() != ""
        for child in group.children:
            assert child.strip() != ""


def test_spending_is_broken_down_and_earning_need_not_be() -> None:
    # Spending is where the detail pays for itself; a salary is just a salary.
    spending = [group for group in DEFAULT_TREE if group.kind is CategoryKind.EXPENSE]

    assert all(len(group.children) > 0 for group in spending)
    assert len(spending) >= 5


def test_the_default_set_covers_spending_earning_and_the_write_offs() -> None:
    kinds = {group.kind for group in DEFAULT_TREE}
    adjustment_groups = [g for g in DEFAULT_TREE if g.kind is CategoryKind.ADJUSTMENT]

    assert CategoryKind.EXPENSE in kinds
    assert CategoryKind.INCOME in kinds
    assert {group.name for group in adjustment_groups} == ADJUSTMENT_NAMES


def test_seeding_creates_the_whole_set_with_children_under_their_parent(
    db: Session, user: User
) -> None:
    created = seed_defaults(db, user.id)

    rows = db.scalars(select(Category).where(Category.user_id == user.id)).all()
    assert len(rows) == len(_all_names())
    assert len(created) == len(rows)

    by_name = {row.name: row for row in rows}
    for group in DEFAULT_TREE:
        parent = by_name[group.name]
        assert parent.parent_id is None
        for child in group.children:
            assert by_name[child].parent_id == parent.id
            # A child always carries its parent's kind.
            assert by_name[child].kind is parent.kind


def test_seeding_twice_creates_nothing_the_second_time(db: Session, user: User) -> None:
    seed_defaults(db, user.id)
    before = db.scalars(select(Category.id)).all()

    again = seed_defaults(db, user.id)

    assert again == []
    assert db.scalars(select(Category.id)).all() == before


def test_seeding_an_empty_tree_creates_every_name(db: Session, user: User) -> None:
    created = seed_defaults(db, user.id)

    assert {row.name for row in created} == set(_all_names())


def test_seeding_leaves_a_tree_the_user_has_touched_alone(db: Session, user: User) -> None:
    seed_defaults(db, user.id)
    groceries = db.scalars(select(Category).where(Category.name == "Groceries")).one()
    groceries.name = "Groceries & vegetables"
    db.commit()
    count_before = len(db.scalars(select(Category.id)).all())

    seed_defaults(db, user.id)

    names = set(db.scalars(select(Category.name)).all())
    # The rename stands, and nothing is added back underneath it.
    assert "Groceries & vegetables" in names
    assert "Groceries" not in names
    assert len(db.scalars(select(Category.id)).all()) == count_before


def test_seeding_does_not_bring_back_a_removed_name(db: Session, user: User) -> None:
    seed_defaults(db, user.id)
    takeaway = db.scalars(select(Category).where(Category.name == "Food delivery")).one()

    remove_category(db, user.id, takeaway.id)
    seed_defaults(db, user.id)

    live = db.scalars(
        select(Category).where(Category.name == "Food delivery", Category.deleted_at.is_(None))
    ).all()
    assert live == []


def _branch(
    db: Session,
    user: User,
    name: str = "Coffee",
    kind: CategoryKind = CategoryKind.EXPENSE,
) -> Category:
    return create_category(db, user.id, name, kind=kind)


def _child(db: Session, user: User, parent: Category, name: str = "Latte") -> Category:
    return create_category(db, user.id, name, kind=None, parent_id=parent.id)


def _categorised_posting(db: Session, user: User, category: Category) -> Posting:
    account = create_account(
        db,
        user.id,
        AccountCreate(
            name="SBI",
            type=AccountType.SAVINGS,
            capture_mode=CaptureMode.STATEMENT_IMPORT,
            opening_balance_paise=10_000_00,
            opening_date=date(2026, 4, 1),
        ),
    )
    record_expense(db, user.id, account.id, 5_000, date(2026, 10, 1))
    posting = db.scalars(select(Posting)).one()
    posting.category_id = category.id
    db.commit()
    return posting


def test_listing_shows_each_branch_with_the_names_under_it(db: Session, user: User) -> None:
    coffee = _branch(db, user, "Coffee")
    tea = _branch(db, user, "Tea")
    _child(db, user, coffee, "Latte")
    _child(db, user, tea, "Green tea")

    listed = list_categories(db, user.id)

    # Branch first, then its own children: never a branch on its own, and never
    # a child without the branch it belongs to.
    assert [row.name for row in listed] == ["Coffee", "Latte", "Tea", "Green tea"]


def test_listing_still_shows_a_name_whose_branch_was_removed(db: Session, user: User) -> None:
    coffee = _branch(db, user, "Coffee")
    _child(db, user, coffee, "Latte")
    child = _child(db, user, coffee, "Extra shot")
    update_category(db, user.id, child.id, move_to_parent_id=None, is_moving=True)
    coffee.deleted_at = datetime.now(UTC)
    db.commit()

    listed = list_categories(db, user.id)

    assert [row.name for row in listed] == ["Extra shot", "Latte"]


def test_a_child_carries_its_parents_kind(db: Session, user: User) -> None:
    income = _branch(db, user, "Pocket money", CategoryKind.INCOME)

    child = _child(db, user, income)

    assert child.kind is CategoryKind.INCOME
    assert child.parent_id == income.id


def test_a_top_level_category_needs_a_kind(db: Session, user: User) -> None:
    with pytest.raises(InvalidCategoryError, match="kind"):
        create_category(db, user.id, "Coffee", kind=None)


def test_a_child_cannot_disagree_with_its_parent(db: Session, user: User) -> None:
    coffee = _branch(db, user)

    with pytest.raises(InvalidCategoryError, match="parent's kind"):
        create_category(db, user.id, "Latte", kind=CategoryKind.INCOME, parent_id=coffee.id)


def test_the_tree_is_two_levels_deep_and_no_more(db: Session, user: User) -> None:
    coffee = _branch(db, user)
    latte = _child(db, user, coffee)

    with pytest.raises(InvalidCategoryError, match="two levels"):
        create_category(db, user.id, "Extra shot", kind=None, parent_id=latte.id)


def test_a_name_cannot_be_used_twice_under_the_same_parent(db: Session, user: User) -> None:
    coffee = _branch(db, user)
    _child(db, user, coffee)

    with pytest.raises(InvalidCategoryError, match="already"):
        _child(db, user, coffee)


def test_a_name_cannot_be_used_twice_at_the_top_level(db: Session, user: User) -> None:
    _branch(db, user)

    with pytest.raises(InvalidCategoryError, match="already"):
        _branch(db, user)


def test_the_same_name_can_live_under_two_different_parents(db: Session, user: User) -> None:
    coffee = _branch(db, user, "Coffee")
    tea = _branch(db, user, "Tea")

    _child(db, user, coffee, "Snack")
    other = _child(db, user, tea, "Snack")

    assert other.parent_id == tea.id


def test_a_name_can_be_used_again_once_the_earlier_one_is_removed(db: Session, user: User) -> None:
    coffee = _branch(db, user)
    remove_category(db, user.id, coffee.id)

    again = _branch(db, user)

    assert again.id != coffee.id


def test_a_category_can_be_renamed(db: Session, user: User) -> None:
    coffee = _branch(db, user)

    renamed = update_category(db, user.id, coffee.id, name="  Chai  ")

    assert renamed.name == "Chai"


def test_renaming_to_a_name_in_use_is_refused(db: Session, user: User) -> None:
    _branch(db, user, "Coffee")
    tea = _branch(db, user, "Tea")

    with pytest.raises(InvalidCategoryError, match="already"):
        update_category(db, user.id, tea.id, name="Coffee")


def test_renaming_a_category_to_its_own_name_is_fine(db: Session, user: User) -> None:
    coffee = _branch(db, user)

    assert update_category(db, user.id, coffee.id, name="Coffee").name == "Coffee"


def test_moving_a_child_under_another_branch_follows_that_branch(db: Session, user: User) -> None:
    coffee = _branch(db, user, "Coffee")
    income = _branch(db, user, "Pocket money", CategoryKind.INCOME)
    snack = _child(db, user, coffee, "Snack")

    moved = update_category(db, user.id, snack.id, move_to_parent_id=income.id, is_moving=True)

    assert moved.parent_id == income.id
    assert moved.kind is CategoryKind.INCOME


def test_moving_a_child_to_the_top_keeps_its_kind(db: Session, user: User) -> None:
    income = _branch(db, user, "Pocket money", CategoryKind.INCOME)
    child = _child(db, user, income, "Pocket money weekly")

    moved = update_category(db, user.id, child.id, move_to_parent_id=None, is_moving=True)

    assert moved.parent_id is None
    assert moved.kind is CategoryKind.INCOME


def test_a_branch_with_children_cannot_become_a_child(db: Session, user: User) -> None:
    coffee = _branch(db, user)
    _child(db, user, coffee)
    other = _branch(db, user, "Tea")

    with pytest.raises(InvalidCategoryError):
        update_category(db, user.id, coffee.id, move_to_parent_id=other.id, is_moving=True)


def test_a_branch_cannot_be_moved_under_its_own_child(db: Session, user: User) -> None:
    coffee = _branch(db, user)
    latte = _child(db, user, coffee)

    with pytest.raises(InvalidCategoryError):
        update_category(db, user.id, coffee.id, move_to_parent_id=latte.id, is_moving=True)


def test_a_branch_with_children_cannot_be_removed(db: Session, user: User) -> None:
    coffee = _branch(db, user)
    _child(db, user, coffee)

    with pytest.raises(CategoryInUseError, match="Latte"):
        remove_category(db, user.id, coffee.id)


def test_a_category_with_movements_filed_under_it_cannot_be_removed(
    db: Session, user: User
) -> None:
    coffee = _branch(db, user)
    _categorised_posting(db, user, coffee)

    with pytest.raises(CategoryInUseError, match="movement"):
        remove_category(db, user.id, coffee.id)


def test_removing_an_unused_category_keeps_the_row(db: Session, user: User) -> None:
    coffee = _branch(db, user)

    remove_category(db, user.id, coffee.id)

    row = db.get(Category, coffee.id)
    assert row is not None
    assert row.deleted_at is not None
    assert list_categories(db, user.id) == []


def test_a_removed_category_is_not_there(db: Session, user: User) -> None:
    coffee = _branch(db, user)
    remove_category(db, user.id, coffee.id)

    with pytest.raises(CategoryNotFoundError):
        get_category(db, user.id, coffee.id)
