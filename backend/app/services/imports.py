"""Reading a statement in, showing what it would do, and then doing it.

Three steps and no shortcuts. `preview` reads the file, checks it against itself
and against the ledger, and stores the rows without writing anything; `commit`
writes the movements that are not already there; `reverse` removes the whole batch
again. Nothing is ever written from a statement that does not reconcile.

The rows are stored as they were read, so the preview a person agreed to is the
same reading that gets committed.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session as DbSession

from app.core.imports import fingerprint, reconcile
from app.core.money import format_paise
from app.importers.base import ParsedRow, StatementError, StatementParser
from app.importers.generic import GenericCsvParser
from app.models import ImportBatch, ImportStatus, Transaction, TransactionSource
from app.services.accounts import get_account
from app.services.transactions import ImportedLine, balance, record_expense, record_income

# Which readers exist, by the name stored on a batch. The SBI reader joins this in
# M15b; keeping the registry here means a batch always names the reader that read it.
PARSERS: dict[str, StatementParser] = {GenericCsvParser.name: GenericCsvParser()}


class ImportNotFoundError(LookupError):
    """Raised when a batch does not exist for the user."""


class InvalidImportError(ValueError):
    """Raised when a file cannot be read, or does not reconcile."""


class ImportConflictError(ValueError):
    """Raised when a batch is not in a state where the request makes sense."""


@dataclass(frozen=True)
class ImportPreview:
    """A batch as a screen needs it: what would be added, and what is already there."""

    batch: ImportBatch
    to_add: list[dict[str, Any]]
    duplicates: list[dict[str, Any]]


def _batches(user_id: int) -> Select[ImportBatch]:
    """The one shared filter, newest first when it is read."""
    return select(ImportBatch).where(ImportBatch.user_id == user_id)


def get_batch(db: DbSession, user_id: int, batch_id: int) -> ImportBatch:
    """One batch, or ImportNotFoundError."""
    batch = db.scalars(_batches(user_id).where(ImportBatch.id == batch_id)).first()
    if batch is None:
        raise ImportNotFoundError(batch_id)
    return batch


def list_batches(db: DbSession, user_id: int, limit: int, offset: int) -> list[ImportBatch]:
    """The user's batches, newest first."""
    statement = (
        _batches(user_id)
        .order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement))


def _row_from(row: ParsedRow, account_id: int) -> dict[str, Any]:
    """A parsed row as it is stored: plain values, and its identity.

    The identity is taken from the day the money moved, which is also the day the
    movement is recorded on, so reading the same statement again finds the same rows.
    """
    return {
        "posted_on": row.posted_on.isoformat(),
        "value_on": row.value_on.isoformat(),
        "amount_paise": row.amount_paise,
        "narration": row.narration,
        "fingerprint": fingerprint(account_id, row.value_on, row.amount_paise, row.narration),
    }


def _day(row: dict[str, Any], key: str) -> date:
    return date.fromisoformat(str(row[key]))


def _already_recorded(db: DbSession, user_id: int, rows: list[dict[str, Any]]) -> set[str]:
    """Which of these rows the ledger already holds."""
    if not rows:
        return set()
    marks = {str(row["fingerprint"]) for row in rows}
    found = db.scalars(
        select(Transaction.fingerprint).where(
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
            Transaction.fingerprint.in_(marks),
        )
    )
    return {mark for mark in found if mark is not None}


def preview(
    db: DbSession,
    user_id: int,
    *,
    account_id: int,
    filename: str,
    text: str,
    opening_paise: int | None = None,
    closing_paise: int | None = None,
    parser: str | None = None,
) -> ImportPreview:
    """Read a statement and hold it, writing nothing.

    Refused, with the reason, when the file cannot be read, when its own arithmetic
    does not add up, when the ledger disagrees with the balance it closes at, or when
    two of its rows are indistinguishable.
    """
    account = get_account(db, user_id, account_id)
    reader = _reader(parser)

    try:
        statement = reader.read(text)
    except StatementError as trouble:
        raise InvalidImportError(str(trouble)) from trouble

    opening = statement.opening_paise if opening_paise is None else opening_paise
    closing = statement.closing_paise if closing_paise is None else closing_paise
    if opening is None or closing is None:
        raise InvalidImportError(
            "a statement has to say what it opened and closed at, or you have to"
        )

    rows = [_row_from(row, account.id) for row in statement.rows]
    _require_distinct(rows)

    total = sum(int(row["amount_paise"]) for row in rows)
    # A statement read twice has every row already recorded, so nothing is missing
    # and the ledger should already stand at the closing figure.
    already = _already_recorded(db, user_id, rows)
    missing = sum(
        int(row["amount_paise"]) for row in rows if str(row["fingerprint"]) not in already
    )
    start = min(_day(row, "value_on") for row in rows)
    end = max(_day(row, "value_on") for row in rows)
    ledger_balance = balance(db, user_id, account.id, as_of=end).balance_paise

    result = reconcile(
        opening_paise=opening,
        rows_paise=total,
        closing_paise=closing,
        ledger_balance_paise=ledger_balance,
        rows_the_ledger_is_missing_paise=missing,
    )
    if not result.adds_up:
        raise InvalidImportError(
            "the statement does not add up: it opens at "
            f"{format_paise(opening)}, lists {format_paise(total)} of movements and closes at "
            f"{format_paise(closing)}, which is {format_paise(result.file_difference_paise)} out"
        )
    if result.ledger_agrees is not True:
        raise InvalidImportError(
            f"the ledger holds {format_paise(ledger_balance)} on {end.isoformat()}, and the rows "
            f"it is missing would put it at {format_paise(ledger_balance + missing)}; the "
            f"statement closes at {format_paise(closing)}, so "
            f"{format_paise(-(result.ledger_difference_paise or 0))} is missing or extra. Record "
            "or import the movements in between first"
        )

    batch = ImportBatch(
        user_id=user_id,
        account_id=account.id,
        filename=filename[:255],
        parser=reader.name,
        period_start=statement.period_start or start,
        period_end=statement.period_end or end,
        opening_paise=opening,
        closing_paise=closing,
        row_count=len(rows),
        rows=rows,
        status=ImportStatus.PREVIEWED,
    )
    db.add(batch)
    db.commit()
    return describe(db, user_id, batch)


def _reader(parser: str | None) -> StatementParser:
    """The named reader, defaulting to the plain layout."""
    name = GenericCsvParser.name if parser is None else parser
    reader = PARSERS.get(name)
    if reader is None:
        raise InvalidImportError(
            f"there is no reader called {name!r}; this build has {', '.join(sorted(PARSERS))}"
        )
    return reader


def _require_distinct(rows: list[dict[str, Any]]) -> None:
    """Two rows that cannot be told apart are refused rather than quietly merged."""
    seen: dict[str, int] = {}
    for number, row in enumerate(rows, start=1):
        mark = str(row["fingerprint"])
        if mark in seen:
            raise InvalidImportError(
                f"rows {seen[mark]} and {number} are the same payment: "
                f"{format_paise(int(row['amount_paise']))} on {row['value_on']}, "
                f"{row['narration']!r}. Nothing here can tell them apart, so import them one at "
                "a time or change one line's narration"
            )
        seen[mark] = number


def describe(db: DbSession, user_id: int, batch: ImportBatch) -> ImportPreview:
    """Split a previewed batch into what would be added and what is already here."""
    already = _already_recorded(db, user_id, batch.rows)
    to_add = [row for row in batch.rows if str(row["fingerprint"]) not in already]
    duplicates = [row for row in batch.rows if str(row["fingerprint"]) in already]
    return ImportPreview(batch=batch, to_add=to_add, duplicates=duplicates)


def commit(db: DbSession, user_id: int, batch_id: int) -> ImportBatch:
    """Write the batch's movements, skipping any the ledger already holds.

    Each row is written through the ordinary recording path, so an imported
    movement is a movement like any other: it can be corrected or removed with the
    tools that already exist, and its balance is derived the same way.
    """
    batch = get_batch(db, user_id, batch_id)
    if batch.status is not ImportStatus.PREVIEWED:
        raise ImportConflictError(f"this statement is already {batch.status.value}")

    already = _already_recorded(db, user_id, batch.rows)
    for row in batch.rows:
        mark = str(row["fingerprint"])
        if mark in already:
            continue
        _write(db, user_id, batch, row)
        already.add(mark)

    batch.status = ImportStatus.COMMITTED
    batch.committed_at = datetime.now(UTC)
    db.commit()
    return batch


def _write(db: DbSession, user_id: int, batch: ImportBatch, row: dict[str, Any]) -> None:
    """One stored row as one movement, on the day the money moved."""
    imported = ImportedLine(
        posted_on=_day(row, "posted_on"),
        raw_narration=str(row["narration"]),
        batch_id=batch.id,
        fingerprint=str(row["fingerprint"]),
    )
    amount = int(row["amount_paise"])
    recorder = record_expense if amount < 0 else record_income
    recorder(
        db,
        user_id,
        batch.account_id,
        abs(amount),
        _day(row, "value_on"),
        source=TransactionSource.IMPORT,
        imported=imported,
    )


def reverse(db: DbSession, user_id: int, batch_id: int) -> ImportBatch:
    """Undo a batch whole: every movement it wrote is soft-deleted, and it is marked.

    A preview that was never committed has no movements, so reversing it simply puts
    it away.
    """
    batch = get_batch(db, user_id, batch_id)
    if batch.status is ImportStatus.REVERSED:
        raise ImportConflictError("this statement has already been reversed")

    now = datetime.now(UTC)
    written = db.scalars(
        select(Transaction).where(
            Transaction.import_batch_id == batch.id,
            Transaction.deleted_at.is_(None),
        )
    )
    for transaction in written:
        transaction.deleted_at = now

    batch.status = ImportStatus.REVERSED
    batch.reversed_at = now
    db.commit()
    return batch
