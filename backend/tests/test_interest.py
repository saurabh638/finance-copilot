"""What a rate earns over a period, worked out exactly.

Every figure here is hand-worked from the stated convention — actual days over a
fixed 365, rounded once, half away from zero — so the tests are an independent
statement of the rule rather than a snapshot of what the code happens to do.

The awkward cases are all written down before the code that has to get them
right: a rate that changes mid-period, a balance that moves, a leap day, a
quarter boundary, an overdrawn balance, and a crore that has to stay exact.
"""

from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest

from app.core.interest import (
    Crediting,
    DatedRate,
    accrued_exactly,
    accrued_paise,
    credit_periods,
    rate_on,
    rate_periods,
    stretches,
    to_paise,
)
from app.core.ledger import DatedAmount

OCT = date(2026, 10, 1)
LATER = date(2026, 10, 11)
END_OF_OCT = date(2026, 10, 30)
LAKH = 1_00_000_00  # ₹1,00,000.00
SEVEN_ONE = Decimal("7.1")


def test_a_month_at_one_rate() -> None:
    # ₹1,00,000 at 7.1% for 30 days = 1,00,000 x 71/1000 x 30/365.
    exact = accrued_exactly(
        opening_balance_paise=LAKH,
        opening_date=OCT,
        postings=[],
        rates=[DatedRate(OCT, SEVEN_ONE)],
        start=OCT,
        end=END_OF_OCT,
    )

    assert exact == Fraction(21_300_000, 365)
    assert (
        accrued_paise(
            opening_balance_paise=LAKH,
            opening_date=OCT,
            postings=[],
            rates=[DatedRate(OCT, SEVEN_ONE)],
            start=OCT,
            end=END_OF_OCT,
        )
        == 58_356
    )


def test_a_rate_change_mid_period_uses_both_rates() -> None:
    # 15 days at 7.1% then 15 days at 8%, on an unchanged balance.
    rates = [DatedRate(OCT, SEVEN_ONE), DatedRate(date(2026, 10, 16), Decimal("8"))]

    exact = accrued_exactly(
        opening_balance_paise=LAKH,
        opening_date=OCT,
        postings=[],
        rates=rates,
        start=OCT,
        end=END_OF_OCT,
    )

    assert exact == Fraction(710_000 * 15 + 800_000 * 15, 365)
    assert to_paise(exact) == 62_055


def test_a_movement_changes_the_balance_from_its_own_day() -> None:
    movements = [DatedAmount(LATER, -20_000_00)]

    exact = accrued_exactly(
        opening_balance_paise=LAKH,
        opening_date=OCT,
        postings=movements,
        rates=[DatedRate(OCT, SEVEN_ONE)],
        start=OCT,
        end=END_OF_OCT,
    )

    assert exact == Fraction(710_000 * 10 + 568_000 * 20, 365)
    assert to_paise(exact) == 50_575


def test_the_stretches_say_where_the_balance_and_the_rate_changed() -> None:
    found = stretches(
        opening_balance_paise=LAKH,
        opening_date=OCT,
        postings=[DatedAmount(LATER, -20_000_00)],
        rates=[DatedRate(date(2026, 10, 21), Decimal("8"))],
        start=OCT,
        end=END_OF_OCT,
    )

    assert [(row.start, row.end, row.balance_paise) for row in found] == [
        (date(2026, 10, 1), date(2026, 10, 10), LAKH),
        (date(2026, 10, 11), date(2026, 10, 20), LAKH - 20_000_00),
        (date(2026, 10, 21), date(2026, 10, 30), LAKH - 20_000_00),
    ]
    # Every day in the period is in exactly one stretch.
    assert sum((row.end - row.start).days + 1 for row in found) == 30


def test_rate_periods_split_on_a_rate_changing_and_not_on_money_moving() -> None:
    # One proposal per agreement, not one per movement: the balance changes inside
    # these runs are added up within them.
    rates = [DatedRate(OCT, SEVEN_ONE), DatedRate(date(2026, 10, 16), Decimal("8"))]

    assert rate_periods(rates, start=OCT, end=END_OF_OCT) == [
        (date(2026, 10, 1), date(2026, 10, 15), SEVEN_ONE),
        (date(2026, 10, 16), date(2026, 10, 30), Decimal("8")),
    ]


def test_rate_periods_leave_out_the_days_before_a_rate_arrived() -> None:
    assert rate_periods([DatedRate(LATER, SEVEN_ONE)], start=OCT, end=END_OF_OCT) == [
        (date(2026, 10, 11), date(2026, 10, 30), SEVEN_ONE)
    ]
    assert rate_periods([], start=OCT, end=END_OF_OCT) == []
    assert rate_periods([DatedRate(OCT, SEVEN_ONE)], start=END_OF_OCT, end=OCT) == []


def test_a_quarter_at_one_rate() -> None:
    # October to December 2026 is 92 days.
    quarter = (date(2026, 10, 1), date(2026, 12, 31))

    exact = accrued_exactly(
        opening_balance_paise=2_00_000_00,
        opening_date=quarter[0],
        postings=[],
        rates=[DatedRate(quarter[0], Decimal("6.5"))],
        start=quarter[0],
        end=quarter[1],
    )

    assert exact == Fraction(1_300_000 * 92, 365)
    assert to_paise(exact) == 327_671


def test_a_leap_day_is_a_day_and_the_divisor_stays_365() -> None:
    # The calendar year 2028 is 366 days of actual time, because of 29 February.
    exact = accrued_exactly(
        opening_balance_paise=LAKH,
        opening_date=date(2028, 1, 1),
        postings=[],
        rates=[DatedRate(date(2028, 1, 1), Decimal("10"))],
        start=date(2028, 1, 1),
        end=date(2028, 12, 31),
    )

    assert exact == Fraction(1_000_000 * 366, 365)
    assert to_paise(exact) == 1_002_740


def test_a_crore_stays_exact() -> None:
    a_crore = 1_00_00_000_00  # ₹1,00,00,000.00
    exact = accrued_exactly(
        opening_balance_paise=a_crore,
        opening_date=date(2026, 1, 1),
        postings=[],
        rates=[DatedRate(date(2026, 1, 1), Decimal("12.3456"))],
        start=date(2026, 1, 1),
        end=date(2026, 12, 31),
    )

    assert exact == Fraction(123_456_000)
    assert to_paise(exact) == 123_456_000
    assert isinstance(to_paise(exact), int)


def test_an_empty_account_earns_nothing() -> None:
    for balance in (0, -LAKH):
        exact = accrued_exactly(
            opening_balance_paise=balance,
            opening_date=OCT,
            postings=[],
            rates=[DatedRate(OCT, SEVEN_ONE)],
            start=OCT,
            end=END_OF_OCT,
        )
        assert exact == 0


def test_an_account_with_no_rate_earns_nothing() -> None:
    exact = accrued_exactly(
        opening_balance_paise=LAKH,
        opening_date=OCT,
        postings=[],
        rates=[],
        start=OCT,
        end=END_OF_OCT,
    )

    assert exact == 0


def test_a_balance_with_no_rate_in_force_earns_nothing_until_one_arrives() -> None:
    # The rate starts on the 11th, so the first ten days earn nothing at all.
    exact = accrued_exactly(
        opening_balance_paise=LAKH,
        opening_date=OCT,
        postings=[],
        rates=[DatedRate(LATER, SEVEN_ONE)],
        start=OCT,
        end=END_OF_OCT,
    )

    assert exact == Fraction(710_000 * 20, 365)


@pytest.mark.parametrize(
    ("exact", "expected"),
    [
        (Fraction(1, 2), 1),
        (Fraction(1, 3), 0),
        (Fraction(49, 100), 0),
        (Fraction(3, 2), 2),
        (Fraction(0), 0),
        (Fraction(-1, 2), -1),
    ],
)
def test_rounding_is_half_away_from_zero(exact: Fraction, expected: int) -> None:
    assert to_paise(exact) == expected


def test_half_a_paise_is_credited_rather_than_lost() -> None:
    # ₹10 at 18.25% for one day is exactly half a paise.
    assert (
        accrued_paise(
            opening_balance_paise=1_000,
            opening_date=OCT,
            postings=[],
            rates=[DatedRate(OCT, Decimal("18.25"))],
            start=OCT,
            end=OCT,
        )
        == 1
    )


def test_the_rate_in_force_is_the_latest_record_on_or_before_the_day() -> None:
    rates = [
        DatedRate(date(2026, 1, 1), Decimal("6")),
        DatedRate(date(2026, 4, 1), Decimal("7.1")),
        DatedRate(date(2026, 10, 16), Decimal("8")),
    ]

    assert rate_on(rates, date(2026, 3, 31)) == Decimal("6")
    assert rate_on(rates, date(2026, 4, 1)) == Decimal("7.1")
    assert rate_on(rates, date(2026, 10, 15)) == Decimal("7.1")
    assert rate_on(rates, date(2026, 10, 16)) == Decimal("8")
    assert rate_on([], OCT) is None
    assert rate_on(rates, date(2025, 12, 31)) is None


def test_a_period_that_ends_before_it_starts_earns_nothing() -> None:
    exact = accrued_exactly(
        opening_balance_paise=LAKH,
        opening_date=OCT,
        postings=[],
        rates=[DatedRate(OCT, SEVEN_ONE)],
        start=END_OF_OCT,
        end=OCT,
    )

    assert exact == 0


def test_daily_crediting_gives_every_finished_day() -> None:
    assert credit_periods(
        Crediting.DAILY, first_day=date(2026, 10, 1), through=date(2026, 10, 3)
    ) == [
        (date(2026, 10, 1), date(2026, 10, 1)),
        (date(2026, 10, 2), date(2026, 10, 2)),
        (date(2026, 10, 3), date(2026, 10, 3)),
    ]


def test_daily_crediting_has_nothing_for_a_day_that_has_not_finished() -> None:
    assert (
        credit_periods(Crediting.DAILY, first_day=date(2026, 10, 1), through=date(2026, 9, 30))
        == []
    )


def test_monthly_crediting_waits_for_the_month_to_end() -> None:
    assert (
        credit_periods(Crediting.MONTHLY, first_day=date(2026, 10, 1), through=date(2026, 10, 30))
        == []
    )
    assert credit_periods(
        Crediting.MONTHLY, first_day=date(2026, 10, 1), through=date(2026, 10, 31)
    ) == [(date(2026, 10, 1), date(2026, 10, 31))]


def test_monthly_crediting_clips_its_first_month() -> None:
    # A rate that starts on the 15th still earns for the rest of October, and the
    # bank credits it at the month's end; skipping the month would lose those days.
    assert credit_periods(
        Crediting.MONTHLY, first_day=date(2026, 10, 15), through=date(2026, 10, 31)
    ) == [(date(2026, 10, 15), date(2026, 10, 31))]
    assert credit_periods(
        Crediting.MONTHLY, first_day=date(2026, 10, 15), through=date(2026, 11, 30)
    ) == [
        (date(2026, 10, 15), date(2026, 10, 31)),
        (date(2026, 11, 1), date(2026, 11, 30)),
    ]


def test_monthly_crediting_runs_across_a_year_end() -> None:
    assert credit_periods(
        Crediting.MONTHLY, first_day=date(2026, 11, 1), through=date(2027, 2, 28)
    ) == [
        (date(2026, 11, 1), date(2026, 11, 30)),
        (date(2026, 12, 1), date(2026, 12, 31)),
        (date(2027, 1, 1), date(2027, 1, 31)),
        (date(2027, 2, 1), date(2027, 2, 28)),
    ]


def test_quarterly_crediting_waits_for_the_quarter_to_end() -> None:
    assert (
        credit_periods(Crediting.QUARTERLY, first_day=date(2026, 10, 1), through=date(2026, 12, 30))
        == []
    )
    assert credit_periods(
        Crediting.QUARTERLY, first_day=date(2026, 10, 1), through=date(2026, 12, 31)
    ) == [(date(2026, 10, 1), date(2026, 12, 31))]


def test_quarterly_crediting_uses_calendar_quarters() -> None:
    assert credit_periods(
        Crediting.QUARTERLY, first_day=date(2026, 10, 1), through=date(2027, 6, 30)
    ) == [
        (date(2026, 10, 1), date(2026, 12, 31)),
        (date(2027, 1, 1), date(2027, 3, 31)),
        (date(2027, 4, 1), date(2027, 6, 30)),
    ]


def test_quarterly_crediting_clips_its_first_quarter() -> None:
    # A rate that starts on 5 October earns from the 5th and is credited with the
    # quarter, at the end of December.
    assert (
        credit_periods(Crediting.QUARTERLY, first_day=date(2026, 10, 5), through=date(2026, 12, 30))
        == []
    )
    assert credit_periods(
        Crediting.QUARTERLY, first_day=date(2026, 10, 5), through=date(2026, 12, 31)
    ) == [(date(2026, 10, 5), date(2026, 12, 31))]
    assert credit_periods(
        Crediting.QUARTERLY, first_day=date(2026, 10, 5), through=date(2027, 3, 31)
    ) == [
        (date(2026, 10, 5), date(2026, 12, 31)),
        (date(2027, 1, 1), date(2027, 3, 31)),
    ]


def test_quarterly_crediting_waits_for_a_month_to_end() -> None:
    assert (
        credit_periods(Crediting.QUARTERLY, first_day=date(2026, 1, 1), through=date(2026, 3, 30))
        == []
    )
    assert credit_periods(
        Crediting.QUARTERLY, first_day=date(2026, 1, 1), through=date(2026, 3, 31)
    ) == [(date(2026, 1, 1), date(2026, 3, 31))]
