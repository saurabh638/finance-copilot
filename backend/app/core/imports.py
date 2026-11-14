"""What an imported row is, and whether a statement adds up.

Two answers, and nothing else: a row's *identity* (so the same payment cannot be
recorded twice) and a statement's *arithmetic* (so nothing is written from a file
that does not agree with itself or with the ledger). Neither reads a file or
touches a database — the importers produce the values and the service does the
writing.

Money here is integer paise, and the only arithmetic is addition and subtraction
of whole numbers.
"""

import hashlib
from dataclasses import dataclass
from datetime import date

# Bumping this makes every fingerprint computed under the old rule stale, which is
# the point: a change to what counts as "the same row" must not silently match rows
# recorded under the previous understanding.
FINGERPRINT_VERSION = "v1"


def normalise_narration(text: str) -> str:
    """The words of a narration: lowercased, with runs of space made single.

    Deliberately nothing more. Reference numbers are kept, because the same payment
    re-read from an overlapping statement carries the same reference, while two
    different payments can differ only by one. Dropping "noise" would be guessing
    which words matter.
    """
    return " ".join(text.split()).lower()


def fingerprint(account_id: int, on: date, amount_paise: int, narration: str) -> str:
    """A row's identity: the account it lands on, the day, the amount, the words.

    The account is part of it, so one payment cannot block the same payment on a
    different account. The sign is part of it, so money in and money out are never
    the same row.
    """
    material = "|".join(
        [
            FINGERPRINT_VERSION,
            str(account_id),
            on.isoformat(),
            str(amount_paise),
            normalise_narration(narration),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Reconciliation:
    """How far a statement is from adding up, on each of the two checks.

    `file_difference_paise` is the statement's own arithmetic: what it opened with
    plus the rows it lists, against the balance it closes at. `ledger_difference_paise`
    is the same sum from the ledger's side, and is None when the ledger was not
    asked. Both are zero when everything agrees; a positive difference means the
    statement (or the ledger) is short of the closing figure.
    """

    file_difference_paise: int
    ledger_difference_paise: int | None

    @property
    def adds_up(self) -> bool:
        """True when the file's opening, rows and closing agree with each other."""
        return self.file_difference_paise == 0

    @property
    def ledger_agrees(self) -> bool | None:
        """True when the ledger's balance plus these rows reaches the closing figure."""
        if self.ledger_difference_paise is None:
            return None
        return self.ledger_difference_paise == 0


def reconcile(
    *,
    opening_paise: int,
    rows_paise: int,
    closing_paise: int,
    ledger_balance_paise: int | None = None,
    rows_the_ledger_is_missing_paise: int | None = None,
) -> Reconciliation:
    """Compare a statement with itself, and with the ledger if it was supplied.

    The two questions are kept apart on purpose. A file can add up perfectly while
    the ledger is missing movements the statement already has, and the answer says
    which of the two is wrong rather than one vague "does not reconcile".

    `rows_paise` is every row the file lists, for the file's own arithmetic.
    `rows_the_ledger_is_missing_paise` is only the rows the ledger does not already
    hold: a statement read twice has every row recorded, so nothing is missing and
    the ledger should already stand at the closing figure. It defaults to all the
    rows, which is the first reading of a statement.
    """
    file_difference = opening_paise + rows_paise - closing_paise
    missing = (
        rows_paise if rows_the_ledger_is_missing_paise is None else rows_the_ledger_is_missing_paise
    )
    ledger_difference = (
        None if ledger_balance_paise is None else ledger_balance_paise + missing - closing_paise
    )
    return Reconciliation(
        file_difference_paise=file_difference,
        ledger_difference_paise=ledger_difference,
    )
