"""When repeating money falls due.

The calendar is where this kind of arithmetic goes wrong, so the awkward days are
written down before the code that has to get them right: the 31st in a month that
has no 31st, February in a leap year and the year before it, a weekly item across
the Monday-to-Sunday boundary, an item that has not started, and an item that has
ended. Nothing here reads a clock: the day being asked about is always handed in.
"""

from calendar import monthrange
from datetime import date

import pytest

from app.core.recurrence import (
    Frequency,
    Rhythm,
    due_on,
    monthly_due,
    occurrence_on,
    weekly_due,
)

LONG_AGO = date(2026, 1, 1)
MONTHLY_1 = Rhythm(Frequency.MONTHLY, day_of_month=1)
MONTHLY_31 = Rhythm(Frequency.MONTHLY, day_of_month=31)
EVERY_MONDAY = Rhythm(Frequency.WEEKLY, weekday=0)
EVERY_SUNDAY = Rhythm(Frequency.WEEKLY, weekday=6)


def test_a_monthly_item_on_the_first_is_the_first() -> None:
    assert monthly_due(2026, 10, 1) == date(2026, 10, 1)
    assert monthly_due(2026, 10, 15) == date(2026, 10, 15)


def test_a_month_without_the_31st_uses_its_last_day() -> None:
    assert monthly_due(2026, 4, 31) == date(2026, 4, 30)
    assert monthly_due(2026, 6, 31) == date(2026, 6, 30)
    assert monthly_due(2026, 11, 31) == date(2026, 11, 30)


def test_february_keeps_its_29th_when_it_has_one() -> None:
    assert monthly_due(2026, 2, 31) == date(2026, 2, 28)
    assert monthly_due(2026, 2, 29) == date(2026, 2, 28)
    assert monthly_due(2028, 2, 31) == date(2028, 2, 29)
    assert monthly_due(2028, 2, 29) == date(2028, 2, 29)


def test_the_31st_falls_on_the_last_day_of_every_month_of_a_year() -> None:
    expected = [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
        date(2026, 5, 31),
        date(2026, 6, 30),
        date(2026, 7, 31),
        date(2026, 8, 31),
        date(2026, 9, 30),
        date(2026, 10, 31),
        date(2026, 11, 30),
        date(2026, 12, 31),
    ]

    assert [monthly_due(2026, month, 31) for month in range(1, 13)] == expected


def test_a_month_rolls_over_a_year() -> None:
    assert monthly_due(2027, 1, 31) == date(2027, 1, 31)
    assert monthly_due(2026, 12, 31) == date(2026, 12, 31)


@pytest.mark.parametrize("weekday", range(7))
def test_a_weekday_lands_in_the_week_that_contains_the_day(weekday: int) -> None:
    # Monday 5 October 2026 to Sunday 11 October 2026 is one week, so every
    # weekday asked about from inside it has to come back inside it.
    for on in (date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 11)):
        day = weekly_due(weekday, on)
        assert day.weekday() == weekday
        assert day.isocalendar()[:2] == on.isocalendar()[:2]


def test_a_weekday_after_the_day_comes_from_the_same_week() -> None:
    assert weekly_due(6, date(2026, 10, 6)) == date(2026, 10, 11)


def test_a_weekday_before_the_day_comes_from_the_same_week() -> None:
    assert weekly_due(0, date(2026, 10, 11)) == date(2026, 10, 5)


def test_the_period_of_a_monthly_item_is_its_month() -> None:
    assert occurrence_on(MONTHLY_31, date(2026, 2, 10)) == date(2026, 2, 28)
    assert occurrence_on(MONTHLY_31, date(2028, 2, 10)) == date(2028, 2, 29)
    assert occurrence_on(MONTHLY_1, date(2026, 12, 20)) == date(2026, 12, 1)


def test_the_period_of_a_weekly_item_is_its_week() -> None:
    assert occurrence_on(EVERY_MONDAY, date(2026, 10, 8)) == date(2026, 10, 5)
    assert occurrence_on(EVERY_SUNDAY, date(2026, 10, 5)) == date(2026, 10, 11)


def test_nothing_is_owed_until_the_day_arrives() -> None:
    assert due_on(MONTHLY_31, LONG_AGO, None, date(2026, 10, 30)) is None
    assert due_on(MONTHLY_31, LONG_AGO, None, date(2026, 10, 31)) == date(2026, 10, 31)


def test_something_due_is_still_owed_for_the_rest_of_its_period() -> None:
    # Money that went unrecorded is not forgotten: a rent due on the 1st is still
    # the thing this period is waiting for on the 28th.
    assert due_on(MONTHLY_1, LONG_AGO, None, date(2026, 10, 28)) == date(2026, 10, 1)
    assert due_on(EVERY_MONDAY, LONG_AGO, None, date(2026, 10, 11)) == date(2026, 10, 5)


def test_it_waits_for_its_own_start() -> None:
    assert due_on(MONTHLY_1, date(2026, 11, 1), None, date(2026, 10, 20)) is None
    assert due_on(MONTHLY_1, date(2026, 10, 1), None, date(2026, 10, 20)) == date(2026, 10, 1)


def test_a_start_after_the_day_leaves_the_first_month_alone() -> None:
    # Starting on the 20th of October does not make October's first-of-the-month
    # rent something the user owes.
    assert due_on(MONTHLY_1, date(2026, 10, 20), None, date(2026, 10, 25)) is None
    assert due_on(MONTHLY_1, date(2026, 10, 20), None, date(2026, 11, 25)) == date(2026, 11, 1)


def test_it_stops_at_its_end() -> None:
    assert due_on(MONTHLY_1, LONG_AGO, date(2026, 9, 30), date(2026, 10, 20)) is None
    assert due_on(MONTHLY_1, LONG_AGO, date(2026, 10, 1), date(2026, 10, 20)) == date(2026, 10, 1)


def test_a_rhythm_without_its_day_is_refused() -> None:
    with pytest.raises(ValueError):
        occurrence_on(Rhythm(Frequency.MONTHLY), date(2026, 10, 6))

    with pytest.raises(ValueError):
        occurrence_on(Rhythm(Frequency.WEEKLY), date(2026, 10, 6))


def test_every_resolved_day_is_a_real_day_of_a_real_month() -> None:
    for month in range(1, 13):
        for day_of_month in (28, 29, 30, 31):
            resolved = monthly_due(2026, month, day_of_month)
            assert resolved.day <= monthrange(2026, month)[1]
            assert resolved.month == month
