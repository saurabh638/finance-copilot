"""Import endpoints: read a statement in, look at it, write it, undo it.

Thin layer: parse the upload, call one service function, translate a service error
into an HTTP status. No reconciliation and no money are worked out here.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_session
from app.models import ImportStatus, User
from app.schemas.imports import ImportBatchResponse, batch_response
from app.services import imports
from app.services.accounts import AccountNotFoundError
from app.services.imports import (
    ImportConflictError,
    ImportNotFoundError,
    InvalidImportError,
)

router = APIRouter(prefix="/imports", tags=["imports"])

# A statement is a text file of a few hundred rows. Anything of this size is not one.
LARGEST_STATEMENT_BYTES = 5 * 1024 * 1024


def _not_found(batch_id: int) -> HTTPException:
    """The single 404 raised for an unknown batch."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Import {batch_id} does not exist",
    )


def _invalid(error: Exception) -> HTTPException:
    """The file, or the batch it would make, is wrong."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _conflict(error: ImportConflictError) -> HTTPException:
    """The request is fine; the batch is not in a state where it can be done."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


def _read(file: UploadFile, content: bytes) -> str:
    """The file as text, refusing what cannot be read or is too large to be one."""
    if len(content) > LARGEST_STATEMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="a statement is a text file of a few hundred rows; this one is too large",
        )
    try:
        # utf-8-sig so a byte-order mark from a spreadsheet does not break the header.
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{file.filename or 'the file'} is not UTF-8 text; open it and save it as CSV",
        ) from None


@router.post("", response_model=ImportBatchResponse, status_code=status.HTTP_201_CREATED)
def upload_statement(
    account_id: Annotated[int, Form(description="The account the statement belongs to.")],
    file: Annotated[UploadFile, File(description="The statement file, as CSV text.")],
    opening_paise: Annotated[
        int | None, Form(description="What the statement opened at, if the file does not say.")
    ] = None,
    closing_paise: Annotated[
        int | None, Form(description="What the statement closed at, if the file does not say.")
    ] = None,
    parser: Annotated[str | None, Form(description="Which reader to use; generic by default.")] = (
        None
    ),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ImportBatchResponse:
    """Read a statement and show what committing it would do. Writes nothing."""
    content = file.file.read()
    try:
        preview = imports.preview(
            db,
            user.id,
            account_id=account_id,
            filename=file.filename or "statement",
            text=_read(file, content),
            opening_paise=opening_paise,
            closing_paise=closing_paise,
            parser=parser,
        )
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error
    except InvalidImportError as error:
        raise _invalid(error) from error
    return batch_response(preview.batch, preview.to_add, preview.duplicates)


@router.get("", response_model=list[ImportBatchResponse])
def list_statements(
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ImportBatchResponse]:
    """Every statement read in so far, newest first."""
    return [batch_response(batch) for batch in imports.list_batches(db, user.id, limit, offset)]


@router.get("/{batch_id}", response_model=ImportBatchResponse)
def read_statement(
    batch_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ImportBatchResponse:
    """One statement, with what committing it would still add."""
    try:
        batch = imports.get_batch(db, user.id, batch_id)
    except ImportNotFoundError as error:
        raise _not_found(batch_id) from error
    preview = imports.describe(db, user.id, batch)
    if batch.status is not ImportStatus.PREVIEWED:
        # Nothing left to decide, so the rows are not reported again.
        return batch_response(batch)
    return batch_response(batch, preview.to_add, preview.duplicates)


@router.post("/{batch_id}/commit", response_model=ImportBatchResponse)
def commit_statement(
    batch_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ImportBatchResponse:
    """Write the movements this statement adds, skipping the ones already recorded."""
    try:
        batch = imports.commit(db, user.id, batch_id)
    except ImportNotFoundError as error:
        raise _not_found(batch_id) from error
    except ImportConflictError as error:
        raise _conflict(error) from error
    return batch_response(batch)


@router.post("/{batch_id}/reverse", response_model=ImportBatchResponse)
def reverse_statement(
    batch_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ImportBatchResponse:
    """Undo the whole batch, or put away a preview that was never committed."""
    try:
        batch = imports.reverse(db, user.id, batch_id)
    except ImportNotFoundError as error:
        raise _not_found(batch_id) from error
    except ImportConflictError as error:
        raise _conflict(error) from error
    return batch_response(batch)
