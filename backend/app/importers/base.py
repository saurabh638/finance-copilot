"""What a statement reader must produce, and what it must refuse.

Every bank's export is different, but the import path only ever needs the same
three things from any of them: the rows, the balance the statement opened at, and
the balance it closed at. A reader that cannot supply the rows yet still cannot
supply the figures simply leaves them out — the service fills what it can from the
request and refuses the batch if the closing balance is still unknown.

Amounts are signed in this ledger's convention by the time a row exists here:
positive is money into the account, negative is money out. A statement that prints
what is *owed* rather than what is held says so with `Side`, and the reader flips
every figure, so nothing downstream has to know which kind of statement it was.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol


class StatementError(ValueError):
    """Raised when a file is not a statement of the shape a reader expects.

    The message names the row it failed on, because a person looking at their own
    statement needs to know which line to look at.
    """


class Side(StrEnum):
    """Which way a statement counts its money."""

    HELD = "held"
    """The figures are money in the account: a credit is positive."""

    OWED = "owed"
    """The figures are money owed, as a card statement prints them."""


def in_ledger_terms(paise: int, side: Side) -> int:
    """The figure as this ledger counts it: held money as printed, owed money negated."""
    return paise if side is Side.HELD else -paise


@dataclass(frozen=True)
class ParsedRow:
    """One line of a statement, already in the ledger's terms."""

    posted_on: date
    value_on: date
    amount_paise: int
    narration: str


@dataclass(frozen=True)
class Statement:
    """Everything a reader could get out of a file.

    The figures are optional: a plain export often prints rows and nothing else. The
    period is optional for the same reason — it can be taken from the rows.
    """

    rows: Sequence[ParsedRow]
    opening_paise: int | None = None
    closing_paise: int | None = None
    period_start: date | None = None
    period_end: date | None = None


class StatementParser(Protocol):
    """One bank's export, read into the shape above.

    `name` is stored on the batch, so a year from now it is still clear which reader
    understood a file and which rules applied to it.
    """

    name: str

    def read(self, text: str) -> Statement:
        """Read the file, or raise StatementError naming the row that failed."""
        ...
