"""Shapes for reading a statement in. Money is integer paise, dates are ISO."""

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import ImportBatch, ImportStatus


class ImportRowResponse(BaseModel):
    """One row of a statement, as it was read."""

    posted_on: date = Field(description="The bank's own date for the row.")
    value_on: date = Field(description="The day the money moved; the movement is dated here.")
    amount_paise: int = Field(description="Signed: negative is money out.")
    narration: str
    fingerprint: str = Field(description="The row's identity, so it cannot be recorded twice.")


class ImportBatchResponse(BaseModel):
    """A statement that was read, and what committing it would do.

    `to_add` and `duplicates` are what the screen shows: the rows that are new, and
    the rows the ledger already holds. A batch that has been committed or reversed
    reports neither, because there is nothing left to decide.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    filename: str
    parser: str
    status: ImportStatus
    period_start: date
    period_end: date
    opening_paise: int
    closing_paise: int
    row_count: int
    created_at: datetime
    committed_at: datetime | None
    reversed_at: datetime | None
    to_add: list[ImportRowResponse] = []
    duplicates: list[ImportRowResponse] = []


def batch_response(
    batch: ImportBatch,
    to_add: Iterable[dict[str, Any]] = (),
    duplicates: Iterable[dict[str, Any]] = (),
) -> ImportBatchResponse:
    """The one shape every import route answers with."""
    response = ImportBatchResponse.model_validate(batch)
    response.to_add = [ImportRowResponse.model_validate(row) for row in to_add]
    response.duplicates = [ImportRowResponse.model_validate(row) for row in duplicates]
    return response
