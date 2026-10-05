"""A movement split between categories, and the parts adding up to the whole.

The rule the ledger has always held is that a transaction's postings describe one
complete movement. A split is a third shape of that: several postings of the same
sign, which is one flow from or to the world outside, divided up inside the app.
"""

import pytest

from app.core.ledger import is_balanced, parts_make_whole


def test_postings_of_one_sign_are_a_split_of_one_flow() -> None:
    # ₹500 spent, filed as ₹300 of groceries and ₹200 of household.
    assert is_balanced([-300_00, -200_00]) is True
    assert is_balanced([300_00, 200_00]) is True


def test_a_split_reaches_past_two_parts() -> None:
    assert is_balanced([-100_00, -100_00, -100_00]) is True


def test_postings_of_mixed_signs_that_do_not_cancel_are_still_refused() -> None:
    assert is_balanced([-300_00, 200_00]) is False
    assert is_balanced([-300_00, 300_00, 100_00]) is False


def test_the_internal_movement_rule_is_unchanged() -> None:
    assert is_balanced([-50_00_000, 50_00_000]) is True
    assert is_balanced([-50_00_000, 40_00_000]) is False


def test_a_zero_beside_another_posting_is_not_a_split() -> None:
    # A posting of nothing is a posting that says nothing, and the database
    # refuses them anyway.
    assert is_balanced([-300_00, 0]) is False


def test_a_split_of_one_part_is_not_a_split() -> None:
    assert parts_make_whole(500_00, [500_00]) is False
    assert parts_make_whole(500_00, [300_00, 200_00]) is True


def test_the_parts_must_add_up_to_the_whole_exactly() -> None:
    assert parts_make_whole(500_00, [300_00, 200_01]) is False
    assert parts_make_whole(500_01, [300_00, 200_00]) is False
    # A single paise out, in either direction, is still out.
    assert parts_make_whole(500_00, [300_00, 199_99]) is False


def test_a_split_needs_parts_at_all() -> None:
    assert parts_make_whole(500_00, []) is False


def test_the_parts_are_magnitudes_of_the_flow() -> None:
    """Signs belong to the kind: an expense of ₹500 splits into ₹300 and ₹200."""
    assert parts_make_whole(500_00, [300_00, 200_00]) is True
    with pytest.raises(ValueError, match="magnitudes"):
        parts_make_whole(500_00, [-300_00, -200_00])
