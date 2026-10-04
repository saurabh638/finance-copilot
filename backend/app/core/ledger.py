"""Pure ledger arithmetic: a balance is its opening balance plus its postings.

No I/O, no database, no clock and no floats. Every amount is a whole number of
paise and every date is given, so the same postings always produce the same
balance. Callers fetch the postings; nothing here reaches for anything.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from app.core.money import add_paise


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

    One posting is an external flow - an expense or an income - and is balanced
    by definition: its other side is the world outside the app, not an account.
    Two or more postings are an internal movement and must sum to zero. A
    transaction with no postings is never balanced.
    """
    if len(amounts) == 0:
        return False
    if len(amounts) == 1:
        return True
    return sum_paise(amounts) == 0
