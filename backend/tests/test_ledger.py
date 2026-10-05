"""Tests for app.core.ledger: the arithmetic that decides every balance.

Written before the implementation, as MILESTONES.md M7 requires. No database and
no clock: every date and amount is given explicitly.
"""

from datetime import date

import pytest

from app.core.ledger import (
    DatedAmount,
    balance_paise,
    difference_paise,
    is_balanced,
    is_large_adjustment,
    share_percent,
    sum_paise,
    transfer_amounts,
)

OPENED = date(2026, 4, 1)
OPENING_PAISE = 1_23_456_78


def test_an_account_with_no_postings_holds_its_opening_balance() -> None:
    assert balance_paise(OPENING_PAISE, OPENED, []) == OPENING_PAISE


def test_an_expense_reduces_the_balance() -> None:
    postings = [DatedAmount(date(2026, 4, 2), -50_000)]

    assert balance_paise(OPENING_PAISE, OPENED, postings) == OPENING_PAISE - 50_000


def test_income_increases_the_balance() -> None:
    postings = [DatedAmount(date(2026, 4, 2), 25_000_00)]

    assert balance_paise(OPENING_PAISE, OPENED, postings) == OPENING_PAISE + 25_000_00


def test_a_transfer_moves_money_without_changing_the_total() -> None:
    out_of_savings, into_current = transfer_amounts(50_000)
    day = date(2026, 4, 2)

    savings = balance_paise(OPENING_PAISE, OPENED, [DatedAmount(day, out_of_savings)])
    current = balance_paise(0, OPENED, [DatedAmount(day, into_current)])

    assert savings == OPENING_PAISE - 50_000
    assert current == 50_000
    assert savings + current == OPENING_PAISE


def test_balance_as_of_a_date_ignores_later_postings() -> None:
    postings = [
        DatedAmount(date(2026, 4, 2), -50_000),
        DatedAmount(date(2026, 5, 2), -10_000),
    ]

    assert (
        balance_paise(OPENING_PAISE, OPENED, postings, as_of=date(2026, 4, 30))
        == OPENING_PAISE - 50_000
    )
    assert (
        balance_paise(OPENING_PAISE, OPENED, postings, as_of=date(2026, 5, 2))
        == OPENING_PAISE - 60_000
    )


def test_postings_before_the_opening_date_are_ignored() -> None:
    postings = [DatedAmount(date(2026, 3, 31), -99_999)]

    assert balance_paise(OPENING_PAISE, OPENED, postings) == OPENING_PAISE


def test_a_posting_on_the_opening_date_itself_counts() -> None:
    postings = [DatedAmount(OPENED, -1)]

    assert balance_paise(OPENING_PAISE, OPENED, postings) == OPENING_PAISE - 1


def test_a_card_balance_goes_further_negative_when_it_is_used() -> None:
    owing = -25_000_00
    postings = [DatedAmount(date(2026, 4, 3), -1_000_00)]

    assert balance_paise(owing, OPENED, postings) == -26_000_00


def test_lakh_and_crore_boundaries_are_exact() -> None:
    one_crore = 1_00_00_000_00

    assert balance_paise(0, OPENED, [DatedAmount(date(2026, 4, 2), one_crore)]) == one_crore
    assert balance_paise(one_crore, OPENED, [DatedAmount(date(2026, 4, 3), -1)]) == one_crore - 1


def test_every_amount_stays_whole_paise_and_never_a_float() -> None:
    postings = [DatedAmount(date(2026, 4, 2), -50_000), DatedAmount(date(2026, 4, 3), 25_000)]

    result = balance_paise(OPENING_PAISE, OPENED, postings)

    assert isinstance(result, int)
    assert result == OPENING_PAISE - 25_000


def test_postings_may_arrive_as_any_iterable_and_are_read_once() -> None:
    postings = (DatedAmount(date(2026, 4, 2), -50_000) for _ in range(2))

    assert balance_paise(OPENING_PAISE, OPENED, postings) == OPENING_PAISE - 1_00_000


def test_the_two_sides_of_a_transfer_always_sum_to_zero() -> None:
    for amount in (1, 50_000, 12_345_678, 99_999_999_99):
        out_of, into = transfer_amounts(amount)

        assert out_of + into == 0
        assert out_of == -amount
        assert into == amount


@pytest.mark.parametrize("amount", [0, -1, -50_000])
def test_a_transfer_must_move_a_positive_amount(amount: int) -> None:
    with pytest.raises(ValueError, match="positive amount"):
        transfer_amounts(amount)


def test_a_lone_posting_is_an_external_flow_and_so_is_balanced() -> None:
    assert is_balanced([-50_000]) is True
    assert is_balanced([25_000_00]) is True


def test_two_or_more_postings_must_sum_to_zero() -> None:
    assert is_balanced([-50_000, 50_000]) is True
    assert is_balanced([-50_000, 40_000]) is False
    assert is_balanced([-50_000, 25_000, 25_000]) is True


def test_a_transaction_with_no_postings_is_not_balanced() -> None:
    assert is_balanced([]) is False


def test_sum_paise_totals_whole_paise() -> None:
    assert sum_paise([1, 2, 3]) == 6
    assert sum_paise([]) == 0
    assert sum_paise([-1, 1]) == 0


# --- the balance check: what the ledger says against what the bank says ---


def test_money_short_is_a_negative_difference() -> None:
    # The bank says there is less than the ledger thinks: spending went unrecorded.
    assert difference_paise(computed_paise=1_00_000, stated_paise=95_000) == -5_000


def test_money_found_is_a_positive_difference() -> None:
    # The bank says there is more: income arrived that was never entered.
    assert difference_paise(computed_paise=1_00_000, stated_paise=1_05_000) == 5_000


def test_a_matching_balance_has_no_difference() -> None:
    assert difference_paise(computed_paise=1_23_456_78, stated_paise=1_23_456_78) == 0


def test_the_difference_keeps_every_paise_of_a_large_one() -> None:
    assert difference_paise(computed_paise=99_999_999_99, stated_paise=1) == -99_999_999_98


def test_the_difference_is_what_the_adjustment_must_post() -> None:
    # Opening balance plus a written-off difference lands exactly on the stated one.
    for computed, stated in ((1_00_000, 95_000), (95_000, 1_00_000), (1, 1), (0, -50_000)):
        difference = difference_paise(computed_paise=computed, stated_paise=stated)

        assert computed + difference == stated


def test_a_write_off_at_the_threshold_is_not_yet_large() -> None:
    assert is_large_adjustment(difference_paise=1_00_000, threshold_paise=1_00_000) is False
    assert is_large_adjustment(difference_paise=1_00_001, threshold_paise=1_00_000) is True


def test_a_large_write_off_is_large_in_either_direction() -> None:
    assert is_large_adjustment(difference_paise=-2_00_000, threshold_paise=1_00_000) is True
    assert is_large_adjustment(difference_paise=2_00_000, threshold_paise=1_00_000) is True
    assert is_large_adjustment(difference_paise=-1, threshold_paise=1_00_000) is False


def test_nothing_written_off_is_never_large() -> None:
    assert is_large_adjustment(difference_paise=0, threshold_paise=0) is False


def test_a_share_of_spending_is_a_whole_percent() -> None:
    # ₹600 written off against ₹20,000 of spending is 3%.
    assert share_percent(adjustments_paise=60_000, spend_paise=20_00_000) == 3
    assert share_percent(adjustments_paise=0, spend_paise=20_00_000) == 0


def test_a_share_rounds_to_the_nearest_percent() -> None:
    assert share_percent(adjustments_paise=1_00_000, spend_paise=1_00_000) == 100
    assert share_percent(adjustments_paise=1_50_000, spend_paise=1_00_000) == 150
    # 1.5% rounds up, 1.4% rounds down: no float is involved either way.
    assert share_percent(adjustments_paise=3, spend_paise=200) == 2
    assert share_percent(adjustments_paise=7, spend_paise=500) == 1


def test_a_share_of_nothing_spent_is_not_a_percentage() -> None:
    assert share_percent(adjustments_paise=50_000, spend_paise=0) == 0


def test_a_share_needs_magnitudes_not_signs() -> None:
    with pytest.raises(ValueError, match="magnitudes"):
        share_percent(adjustments_paise=-1, spend_paise=1_00_000)
    with pytest.raises(ValueError, match="magnitudes"):
        share_percent(adjustments_paise=1, spend_paise=-1_00_000)
