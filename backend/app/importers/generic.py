"""A plain statement: a date, an amount and a narration, one row per line.

This is the layout the framework is tested against, and the one to hand-write a
statement in when a bank's export cannot be read yet. It is deliberately strict —
ISO dates and a signed decimal amount — because a stricter reader that says which
line is wrong is more useful than a forgiving one that guesses.

```
date,amount,narration
2026-09-01,-450.00,UPI/ Swiggy
2026-09-07,1250.00,Interest credit
```

The columns may be in any order. A negative amount is money out. The file prints no
balances, so the batches made from it take them from the request.
"""

import csv
import io
from datetime import date

from app.core.money import parse_paise
from app.importers.base import ParsedRow, Side, Statement, StatementError, in_ledger_terms

COLUMNS = ("date", "amount", "narration")
NAME = "generic"
DATE_FORMAT = "%Y-%m-%d"


class GenericCsvParser:
    """Reads the plain layout above."""

    name = NAME

    def __init__(self, side: Side = Side.HELD) -> None:
        self.side = side

    def read(self, text: str) -> Statement:
        """Read every row, or raise StatementError naming the line that failed."""
        reader = csv.DictReader(io.StringIO(text))
        header = [column.strip().lower() for column in (reader.fieldnames or [])]
        missing = [column for column in COLUMNS if column not in header]
        if missing:
            header_line = "a statement needs a date, an amount and a narration column; "
            raise StatementError(f"{header_line}this one has no {', '.join(missing)}")
        reader.fieldnames = header

        rows: list[ParsedRow] = []
        # One-based, counting the header, so the number matches a spreadsheet's.
        for number, raw in enumerate(reader, start=2):
            row = self._row(raw, number)
            if row is not None:
                rows.append(row)

        if not rows:
            raise StatementError("this file has no rows in it")
        return Statement(rows=rows)

    def _row(self, raw: dict[str, str | None], number: int) -> ParsedRow | None:
        """One row, or None for a line that is entirely blank."""
        words = {column: (raw.get(column) or "").strip() for column in COLUMNS}
        if all(value == "" for value in words.values()):
            return None

        on = self._date(words["date"], number)
        paise = self._amount(words["amount"], number)
        return ParsedRow(
            posted_on=on,
            value_on=on,
            amount_paise=in_ledger_terms(paise, self.side),
            narration=words["narration"],
        )

    def _date(self, text: str, number: int) -> date:
        try:
            return date.fromisoformat(text)
        except ValueError:
            raise StatementError(
                f"row {number}: {text!r} is not a date; this layout takes 2026-09-30"
            ) from None

    def _amount(self, text: str, number: int) -> int:
        try:
            paise = parse_paise(text)
        except ValueError:
            raise StatementError(
                f"row {number}: {text!r} is not an amount, like -450.00 or 1250.00"
            ) from None
        if paise == 0:
            raise StatementError(f"row {number}: an amount of nothing is not a movement")
        return paise
