"""Pure ledger arithmetic: a balance is its opening balance plus its postings.

No I/O, no database, no clock and no floats. Every amount is a whole number of
paise and every date is given, so the same postings always produce the same
balance. Callers fetch the postings; nothing here reaches for anything.

It also holds the balance check: what the bank says against what the ledger says,
and the figures that decide whether a write-off is worth a second look.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from app.core.money import add_paise, subtract_paise


@dataclass(frozen=True)
class DatedAmount:
    """One posting's effect on one account: the day it applies, and how much."""

    on: date
    amount_paise: int


def balance_paise(
    opening_balance_paise: int,
    opening_date: date,
    postings: Iterable[DatedAmount],
    as_of: date | None = None,
) -> int:
    """The account's balance: the opening balance plus the postings that apply.

    A posting dated before `opening_date` is ignored, because the opening balance
    already describes the account at that moment. When `as_of` is given, a
    posting after it is ignored too, which is what "balance as of a date" means.
    Everything stays whole paise.
    """
    affecting = [
        posting.amount_paise
        for posting in postings
        if posting.on >= opening_date and (as_of is None or posting.on <= as_of)
    ]
    return add_paise(opening_balance_paise, *affecting)


def sum_paise(amounts: Iterable[int]) -> int:
    """The total of a set of postings, in whole paise."""
    return add_paise(*amounts)


def transfer_amounts(amount_paise: int) -> tuple[int, int]:
    """Both sides of a transfer: out of one account, into the other.

    They always sum to zero, so a transfer can never create or destroy money.
    """
    if amount_paise <= 0:
        raise ValueError(f"a transfer must move a positive amount, got {amount_paise}")
    return (-amount_paise, amount_paise)


def is_balanced(amounts: Sequence[int]) -> bool:
    """True when a transaction's postings are a complete set.

    Three shapes are accepted, and no others. One posting is an external flow -
    an expense or an income - and is balanced by definition: its other side is
    the world outside the app, not an account. Two or more postings that sum to
    zero are an internal movement: a transfer, or anything else that stays
    inside. Two or more postings of a single sign are one external flow split
    between categories, which is the same money counted once, twice over. A
    transaction with no postings is never balanced.
    """
    if len(amounts) == 0:
        return False
    if len(amounts) == 1:
        return True
    if sum_paise(amounts) == 0:
        return True
    return all(amount > 0 for amount in amounts) or all(amount < 0 for amount in amounts)


def parts_make_whole(total_paise: int, parts_paise: Sequence[int]) -> bool:
    """True when a split's parts are exactly the amount the user stated.

    Both are magnitudes: the sign belongs to the kind of the movement, so an
    expense of ₹500 splits into ₹300 and ₹200 and nothing else. A split needs at
    least two parts, since one part is simply the whole, and the parts must add
    up exactly: a paise gained or lost here would quietly unbalance the ledger.
    """
    if total_paise < 0 or any(part < 0 for part in parts_paise):
        raise ValueError("a split is stated in magnitudes, not signs")
    if len(parts_paise) < 2:
        return False
    return sum_paise(parts_paise) == total_paise


def roll_up(
    parents: Mapping[int, int | None],
    direct_paise: Mapping[int, int],
) -> dict[int, int]:
    """Each category's total: what was filed under it, and under all of its children.

    `parents` says where each category sits, and `direct_paise` says what was
    filed under it by name. Every amount is added to its category and to each
    category above it, so a group's figure is the whole of what is beneath it.
    Spending filed under a category that is not in the tree is nobody's, and is
    left out; a cycle would be a tree we cannot read, and is cut off after one
    pass rather than looped over.
    """
    totals = dict.fromkeys(parents, 0)
    for category_id, amount_paise in direct_paise.items():
        above: int | None = category_id
        for _ in range(len(parents)):
            if above is None or above not in totals:
                break
            totals[above] = add_paise(totals[above], amount_paise)
            above = parents.get(above)
    return totals


def difference_paise(computed_paise: int, stated_paise: int) -> int:
    """What the bank says minus what the ledger says, in whole paise.

    This is exactly what a write-off has to post: the computed balance plus this
    difference lands on the stated balance, with no paise gained or lost. A
    positive figure is money the ledger never knew about; a negative one is
    spending that went unrecorded.
    """
    return subtract_paise(stated_paise, computed_paise)


def is_large_adjustment(difference_paise: int, threshold_paise: int) -> bool:
    """True when a write-off is big enough to be worth a second look first.

    The size matters, not the direction: money missing and money found are both
    worth asking about. A write-off exactly at the threshold is not above it, and
    nothing to write off is never large.
    """
    return abs(difference_paise) > threshold_paise


def share_percent(adjustments_paise: int, spend_paise: int) -> int:
    """Write-offs as a whole percent of spending, rounded to the nearest.

    Both figures are magnitudes, because a share does not care which way either
    one went. With nothing spent there is no share to state, so the answer is 0
    rather than a division by zero. Rounded with integers alone, so no float and
    no lost paise are involved.
    """
    if adjustments_paise < 0 or spend_paise < 0:
        raise ValueError("a share needs magnitudes, not signed amounts")
    if spend_paise == 0:
        return 0
    return (2 * adjustments_paise * 100 + spend_paise) // (2 * spend_paise)
