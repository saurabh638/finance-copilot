"""Rolling a child's spending up into the group above it.

The report the user reads is per group, but the spending happens in the leaves:
"Groceries" is the total of what was spent under it, not a number of its own.
"""

from app.core.ledger import roll_up


def test_a_leaf_keeps_its_own_spending() -> None:
    totals = roll_up(parents={1: None}, direct_paise={1: 30_000})

    assert totals == {1: 30_000}


def test_a_childs_spending_is_added_to_its_parent() -> None:
    totals = roll_up(parents={1: None, 2: 1}, direct_paise={2: 30_000})

    # The parent's own total is what its children spent; the child is unchanged.
    assert totals == {1: 30_000, 2: 30_000}


def test_a_parents_own_spending_is_added_to_its_childrens() -> None:
    totals = roll_up(parents={1: None, 2: 1}, direct_paise={1: 10_000, 2: 30_000})

    assert totals == {1: 40_000, 2: 30_000}


def test_siblings_add_up_under_one_parent() -> None:
    totals = roll_up(parents={1: None, 2: 1, 3: 1}, direct_paise={2: 30_000, 3: 20_000})

    assert totals == {1: 50_000, 2: 30_000, 3: 20_000}


def test_a_grandchild_reaches_both_ancestors() -> None:
    totals = roll_up(parents={1: None, 2: 1, 3: 2}, direct_paise={3: 5_000})

    assert totals == {1: 5_000, 2: 5_000, 3: 5_000}


def test_nothing_spent_is_a_zero_and_not_a_missing_row() -> None:
    totals = roll_up(parents={1: None, 2: 1}, direct_paise={})

    assert totals == {1: 0, 2: 0}


def test_spending_with_no_category_is_not_rolled_into_anyone() -> None:
    totals = roll_up(parents={1: None}, direct_paise={7: 30_000})

    assert totals == {1: 0}


def test_a_cycle_in_the_tree_stops_rather_than_hanging() -> None:
    """The tree cannot hold a cycle; a report that hung on one would be worse."""
    totals = roll_up(parents={1: 2, 2: 1}, direct_paise={1: 10_000})

    # Both are above each other, so both are counted, each exactly once.
    assert totals == {1: 10_000, 2: 10_000}


def test_a_negative_total_is_carried_upwards_too() -> None:
    """Corrections are real: a refund under a child reduces the group."""
    totals = roll_up(parents={1: None, 2: 1}, direct_paise={2: -5_000})

    assert totals == {1: -5_000, 2: -5_000}


def test_the_roll_up_works_in_whole_paise() -> None:
    totals = roll_up(parents={1: None, 2: 1, 3: 1}, direct_paise={2: 1, 3: 2})

    assert totals[1] == 3
