"""Ranking what to offer for fast entry, and counting a run of days.

Two small pieces of arithmetic that the daily screen leans on: which names are
worth offering as chips, and how many days in a row the user has recorded
something. Both are pure, so both are settled here rather than in a screen.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Suggestion:
    """One merchant as the history remembers it: what, how often, and how."""

    merchant: str
    times_used: int
    last_used: date
    account_id: int
    category_id: int | None
    amount_paise: int


def rank_suggestions(
    suggestions: Sequence[Suggestion],
    within_days: int,
    on: date,
) -> list[Suggestion]:
    """The names worth offering, most used first.

    A name the user has stopped using is not a suggestion, so only what was used
    within the window is offered. Among names used equally often the most recent
    comes first, and two names still equal are ordered by name: a list that
    reshuffles itself for no reason is a list nobody can learn.
    """
    cutoff = on - timedelta(days=within_days)
    recent = [row for row in suggestions if row.last_used >= cutoff]
    return sorted(
        recent, key=lambda row: (-row.times_used, -row.last_used.toordinal(), row.merchant)
    )


def streak_days(days: Iterable[date], today: date) -> int:
    """How many days in a row, ending today or yesterday, have a movement.

    Yesterday counts as the end of a run, because the day is not over: a user who
    recorded something last night and opens the app this morning has not broken
    their run, and telling them they have would be the negative messaging this
    milestone is told not to do. Nothing to count is no days, never a scolding.
    """
    recorded = set(days)

    start = today if today in recorded else today - timedelta(days=1)
    if start not in recorded:
        return 0

    counted = 0
    day = start
    while day in recorded:
        counted += 1
        day -= timedelta(days=1)
    return counted
