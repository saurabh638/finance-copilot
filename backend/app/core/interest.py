"""Pure interest arithmetic: what a rate earned over a period.

Two conventions are stated here and nowhere else, because both are policy rather
than fact and both change every figure the engine produces:

* **Day count: actual days over a fixed 365.** A stretch of 30 days counts 30,
  and 29 February is a real day in the stretch. The divisor stays 365 even in a
  leap year, so a bank that divides by 366 differs by one day's interest - and
  the user sees that as a difference between the proposed figure and the credited
  one, which is where a difference belongs.
* **Rounding once, at the end, half away from zero.** Accrual is exact rational
  arithmetic: a Decimal rate becomes a Fraction exactly, so no float is ever
  involved and nothing is lost by adding a day at a time. Only the figure that is
  proposed is rounded, and only once; rounding each day would leak a paise a day.

Everything is a pure function of the dates, the postings and the rates it is
handed. Nothing here reads a clock or touches a database.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction

from app.core.ledger import DatedAmount

# The divisor. Stated as a constant because it is the convention, not arithmetic.
DAYS_IN_YEAR = 365

PER_CENT = Fraction(100)


class Crediting(StrEnum):
    """How often a bank actually pays the interest over.

    The ranges match `app.models.enums.RateFrequency` word for word for the three
    the engine understands. A yearly rate has no period here: it would credit
    once a year, and refusing it loudly is better than proposing nothing.
    """

    DAILY = "daily"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass(frozen=True)
class DatedRate:
    """One rate record: the day it takes effect, and the rate itself.

    `percent` is per cent per annum, exactly as stored: 7.1 means 7.1%.
    """

    on: date
    percent: Decimal


@dataclass(frozen=True)
class AccrualStretch:
    """Days over which both the balance and the rate are unchanged.

    `exact_paise` is the stretch's interest as an exact fraction of a paise. A
    stretch that earned nothing - an empty account, an overdrawn one, or days
    before a rate arrived - is still a stretch, with zero, so that the days of a
    period always add up to the period.
    """

    start: date
    end: date
    balance_paise: int
    percent: Decimal | None
    exact_paise: Fraction


def rate_on(rates: Sequence[DatedRate], day: date) -> Decimal | None:
    """The rate in force on a day: the latest record dated on or before it."""
    in_force = [row for row in rates if row.on <= day]
    if not in_force:
        return None
    return max(in_force, key=lambda row: row.on).percent


def _balance_on(
    opening_balance_paise: int,
    opening_date: date,
    postings: Sequence[DatedAmount],
    day: date,
) -> int:
    """The balance that stands during a day: everything posted up to and including it.

    Money that arrived during a day earns on that day, which is how a savings
    account's daily balance works - and it is a convention rather than a fact, so
    it is stated here rather than left to be inferred from a boundary.
    """
    total = opening_balance_paise
    for posting in postings:
        if opening_date <= posting.on <= day:
            total += posting.amount_paise
    return total


def _breakpoints(
    postings: Sequence[DatedAmount],
    rates: Sequence[DatedRate],
    start: date,
    end: date,
) -> list[date]:
    """The days a stretch begins on: the first day, and every day something changed.

    The period's last day is not a breakpoint. A stretch ends where the next one
    begins, so adding the last day separately would leave a stretch of its own
    holding nothing but that one day.
    """
    changing = {start}
    for posting in postings:
        if start < posting.on <= end:
            changing.add(posting.on)
    for rate in rates:
        if start < rate.on <= end:
            changing.add(rate.on)
    return sorted(changing)


def stretches(
    *,
    opening_balance_paise: int,
    opening_date: date,
    postings: Sequence[DatedAmount],
    rates: Sequence[DatedRate],
    start: date,
    end: date,
) -> list[AccrualStretch]:
    """The period broken into stretches of constant balance and rate.

    A movement dated inside the period starts a new stretch on its own day, and so
    does a new rate, which is what makes "a rate change mid-period uses the right
    rate" fall out of the arithmetic rather than needing a special case.
    """
    if start > end:
        return []

    found: list[AccrualStretch] = []
    breaks = _breakpoints(postings, rates, start, end)
    for index, first in enumerate(breaks):
        last = end if index + 1 == len(breaks) else breaks[index + 1] - timedelta(days=1)
        balance = _balance_on(opening_balance_paise, opening_date, postings, first)
        percent = rate_on(rates, first)
        found.append(
            AccrualStretch(
                start=first,
                end=last,
                balance_paise=balance,
                percent=percent,
                exact_paise=_stretch_interest(balance, percent, (last - first).days + 1),
            )
        )
    return found


def rate_periods(
    rates: Sequence[DatedRate],
    *,
    start: date,
    end: date,
) -> list[tuple[date, date, Decimal]]:
    """The period split by rate changes: each run of days under one rate.

    Money moving in and out does *not* split these. A bank credits one figure for a
    month, not one per movement, so the balance changes inside a rate stretch
    belong to the same proposal and are added up within it. A rate change is
    different: it is a different agreement, and the days on either side of it earned
    at different rates, so those are two proposals.
    """
    if start > end:
        return []

    found: list[tuple[date, date, Decimal]] = []
    day = start
    while day <= end:
        percent = rate_on(rates, day)
        if percent is None:
            day += timedelta(days=1)
            continue

        last = end
        for rate in rates:
            if day < rate.on <= end:
                last = min(last, rate.on - timedelta(days=1))
        found.append((day, last, percent))
        day = last + timedelta(days=1)
    return found


def _stretch_interest(balance_paise: int, percent: Decimal | None, days: int) -> Fraction:
    """What one stretch earned, exactly.

    Money that is not there earns nothing, and neither does money with no rate on
    it: an overdrawn account owes no interest, and inventing one would be inventing
    a bank's behaviour.
    """
    if percent is None or balance_paise <= 0 or days <= 0:
        return Fraction(0)

    return Fraction(balance_paise) * Fraction(percent) / PER_CENT / DAYS_IN_YEAR * days


def accrued_exactly(
    *,
    opening_balance_paise: int,
    opening_date: date,
    postings: Sequence[DatedAmount],
    rates: Sequence[DatedRate],
    start: date,
    end: date,
) -> Fraction:
    """The period's interest as an exact fraction of a paise, unrounded.

    Exactness is the point: a bank pays the sum over the days, not the sum of the
    rounded days, and only the final figure is a whole number of paise.
    """
    return sum(
        (
            row.exact_paise
            for row in stretches(
                opening_balance_paise=opening_balance_paise,
                opening_date=opening_date,
                postings=postings,
                rates=rates,
                start=start,
                end=end,
            )
        ),
        Fraction(0),
    )


def to_paise(exact: Fraction) -> int:
    """An exact amount rounded to whole paise, half away from zero.

    Half goes up, in both directions, because a bank's rounding of a half is not
    something this code can know: what it can promise is that it is stated, and
    that the user confirms the figure the bank actually paid.
    """
    sign = -1 if exact < 0 else 1
    magnitude = abs(exact)
    whole = magnitude.numerator // magnitude.denominator
    if magnitude - whole >= Fraction(1, 2):
        whole += 1
    return sign * whole


def accrued_paise(
    *,
    opening_balance_paise: int,
    opening_date: date,
    postings: Sequence[DatedAmount],
    rates: Sequence[DatedRate],
    start: date,
    end: date,
) -> int:
    """The period's interest in whole paise, ready to be proposed."""
    return to_paise(
        accrued_exactly(
            opening_balance_paise=opening_balance_paise,
            opening_date=opening_date,
            postings=postings,
            rates=rates,
            start=start,
            end=end,
        )
    )


def _quarter_end(day: date) -> date:
    """The last day of the calendar quarter that contains a day.

    Indian financial quarters end in March, June, September and December, and
    December's ends in its own year, so no quarter ever runs over into the next.
    """
    month = ((day.month - 1) // 3 + 1) * 3
    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(day.year, month, days)


def _month_end(day: date) -> date:
    """The last day of the month that contains a day."""
    first_of_next = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first_of_next - timedelta(days=1)


def credit_periods(
    frequency: Crediting,
    *,
    first_day: date,
    through: date,
) -> list[tuple[date, date]]:
    """The crediting periods that have finished, clipped to the first known day.

    The periods are the calendar's: a month ends on its last day, a quarter on the
    last day of March, June, September or December. Nothing about the still
    running period is returned, which is what stops a part month being credited
    twice over.

    The *first* period is clipped to `first_day` rather than skipped. A rate that
    arrives on the 15th means the bank credits the month at its end for the days it
    actually had the rate, and skipping that month would quietly throw those days
    away. The next period starts the day after this one ends, so no day is in two
    periods either.
    """
    if through < first_day:
        return []

    if frequency is Crediting.DAILY:
        day = first_day
        days: list[tuple[date, date]] = []
        while day <= through:
            days.append((day, day))
            day += timedelta(days=1)
        return days

    periods: list[tuple[date, date]] = []
    day = first_day
    while day <= through:
        if frequency is Crediting.MONTHLY:
            first = day.replace(day=1)
            last = _month_end(day)
        else:
            first_month = ((day.month - 1) // 3) * 3 + 1
            first = date(day.year, first_month, 1)
            last = _quarter_end(day)

        if last <= through:
            periods.append((max(first, first_day), last))
        # Step past the period just considered, whether or not it qualified.
        day = last + timedelta(days=1)

    return periods
