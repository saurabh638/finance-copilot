"""Ranking the names offered for fast entry, and counting a run of days.

The chip row is the shortcut the whole daily ritual rests on, so what it offers
and in what order is a rule worth stating rather than a sort that drifted.
"""

from datetime import date, timedelta

from app.core.suggestions import Suggestion, rank_suggestions, streak_days

TODAY = date(2026, 10, 6)


def suggestion(
    merchant: str,
    times_used: int,
    last_used: date,
    *,
    account_id: int = 1,
    category_id: int | None = 11,
    amount_paise: int = 50_000,
) -> Suggestion:
    return Suggestion(
        merchant=merchant,
        times_used=times_used,
        last_used=last_used,
        account_id=account_id,
        category_id=category_id,
        amount_paise=amount_paise,
    )


def test_nothing_recorded_offers_nothing() -> None:
    assert rank_suggestions([], within_days=90, on=TODAY) == []


def test_the_most_used_name_comes_first() -> None:
    rows = [
        suggestion("Blinkit", 3, TODAY),
        suggestion("Swiggy", 11, TODAY),
        suggestion("Uber", 7, TODAY),
    ]

    assert [row.merchant for row in rank_suggestions(rows, within_days=90, on=TODAY)] == [
        "Swiggy",
        "Uber",
        "Blinkit",
    ]


def test_among_names_used_equally_often_the_most_recent_comes_first() -> None:
    rows = [
        suggestion("Swiggy", 5, TODAY - timedelta(days=20)),
        suggestion("Blinkit", 5, TODAY - timedelta(days=2)),
        suggestion("Uber", 5, TODAY - timedelta(days=9)),
    ]

    assert [row.merchant for row in rank_suggestions(rows, within_days=90, on=TODAY)] == [
        "Blinkit",
        "Uber",
        "Swiggy",
    ]


def test_two_names_still_equal_are_ordered_by_name_so_the_list_does_not_reshuffle() -> None:
    rows = [suggestion("Zomato", 4, TODAY), suggestion("Amazon", 4, TODAY)]

    assert [row.merchant for row in rank_suggestions(rows, within_days=90, on=TODAY)] == [
        "Amazon",
        "Zomato",
    ]


def test_a_name_the_user_stopped_using_is_not_offered() -> None:
    rows = [
        suggestion("Old shop", 40, TODAY - timedelta(days=91)),
        suggestion("Blinkit", 1, TODAY),
    ]

    assert [row.merchant for row in rank_suggestions(rows, within_days=90, on=TODAY)] == ["Blinkit"]


def test_the_window_counted_back_from_the_day_given() -> None:
    """The day exactly at the edge of the window still counts."""
    rows = [suggestion("Blinkit", 1, TODAY - timedelta(days=90))]

    assert rank_suggestions(rows, within_days=90, on=TODAY) != []


def test_a_suggestion_carries_how_to_record_it_again() -> None:
    rows = [suggestion("Blinkit", 2, TODAY, account_id=3, category_id=None, amount_paise=123_45)]

    offered = rank_suggestions(rows, within_days=90, on=TODAY)

    assert offered[0] == Suggestion(
        merchant="Blinkit",
        times_used=2,
        last_used=TODAY,
        account_id=3,
        category_id=None,
        amount_paise=123_45,
    )


def test_a_run_of_days_counts_back_from_today() -> None:
    days = [TODAY, TODAY - timedelta(days=1), TODAY - timedelta(days=2)]

    assert streak_days(days, TODAY) == 3


def test_a_run_that_ended_yesterday_still_counts() -> None:
    """The day is not over: last night's entry has not broken anything."""
    days = [TODAY - timedelta(days=1), TODAY - timedelta(days=2)]

    assert streak_days(days, TODAY) == 2


def test_a_run_stops_at_the_first_day_with_nothing() -> None:
    days = [TODAY, TODAY - timedelta(days=1), TODAY - timedelta(days=3)]

    assert streak_days(days, TODAY) == 2


def test_nothing_to_count_is_no_days_and_not_a_scolding() -> None:
    assert streak_days([], TODAY) == 0
    assert streak_days([TODAY - timedelta(days=4)], TODAY) == 0


def test_the_same_day_twice_still_counts_once() -> None:
    days = [TODAY, TODAY, TODAY - timedelta(days=1)]

    assert streak_days(days, TODAY) == 2


def test_a_run_of_days_that_ends_long_ago_is_over() -> None:
    days = [TODAY - timedelta(days=2), TODAY - timedelta(days=3)]

    assert streak_days(days, TODAY) == 0
