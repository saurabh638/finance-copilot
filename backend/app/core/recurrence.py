"""When repeating money falls due.

Working out whether something is owed today is calendar arithmetic, and calendar
arithmetic is where the quiet mistakes live: a rent due on the 31st is due on the
30th in April and the 28th in February, and a weekly item asked about on a Sunday
belongs to the week that is ending, not the one that is starting.

Everything here is pure and takes the day being asked about as an argument, so
nothing in this module reads a clock and a test can put it on any date it likes.
The database only ever stores the answers: the rhythm lives in the rows, the
dates live here.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class Frequency(StrEnum):
    """How often a recurring item comes round."""

    MONTHLY = "monthly"
    WEEKLY = "weekly"


@dataclass(frozen=True)
class Rhythm:
    """How often something repeats, and on which day.

    A monthly item carries a day of the month (1 to 31, brought back to the last
    day when the month is shorter); a weekly one carries a weekday, counted the
    way Python counts them, Monday 0 through Sunday 6.
    """

    frequency: Frequency
    day_of_month: int | None = None
    weekday: int | None = None


def monthly_due(year: int, month: int, day_of_month: int) -> date:
    """The day a monthly item falls on, pulled back to the month's last day.

    The 31st is the day the user agreed with their landlord, not a promise that
    every month has one, so a month that is too short uses its last day.
    """
    return date(year, month, min(day_of_month, monthrange(year, month)[1]))


def weekly_due(weekday: int, on: date) -> date:
    """The day with that weekday in the Monday-to-Sunday week containing `on`."""
    return on - timedelta(days=on.weekday() - weekday)


def occurrence_on(rhythm: Rhythm, on: date) -> date:
    """The date this rhythm falls on in the period that contains `on`."""
    if rhythm.frequency is Frequency.MONTHLY:
        if rhythm.day_of_month is None:
            raise ValueError("a monthly item needs a day of the month")
        return monthly_due(on.year, on.month, rhythm.day_of_month)

    if rhythm.weekday is None:
        raise ValueError("a weekly item needs a weekday")
    return weekly_due(rhythm.weekday, on)


def due_on(
    rhythm: Rhythm,
    starts_on: date,
    ends_on: date | None,
    on: date,
) -> date | None:
    """The date this item is owed on in the period containing `on`, if it is owed.

    Three things have to be true. The period's day has to have arrived, because a
    rent due on the 31st is not owed on the 30th. It has to fall inside the item's
    own life, so an item that starts next month stays quiet and one that was
    stopped stays stopped. And the occurrence stays owed for the rest of its
    period, so a payment confirmed late is still counted as this period's rather
    than quietly dropped.
    """
    occurrence = occurrence_on(rhythm, on)
    if occurrence > on or occurrence < starts_on:
        return None
    if ends_on is not None and occurrence > ends_on:
        return None
    return occurrence
