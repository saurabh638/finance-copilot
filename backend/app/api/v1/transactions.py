"""Transaction endpoints: recording money movements, and reading them back.

Thin layer: parse the request, call one service function, translate a service
error into an HTTP status. No business rules live here.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_session
from app.models import PostingKind, User
from app.schemas.transaction import (
    IncomeCreate,
    MovementCreate,
    PostingResponse,
    StreakResponse,
    SuggestionResponse,
    TransactionResponse,
    TransactionUpdate,
    TransferCreate,
)
from app.services import transactions
from app.services.accounts import AccountNotFoundError
from app.services.categories import CategoryNotFoundError
from app.services.transactions import (
    InvalidTransactionError,
    TransactionDetail,
    TransactionNotFoundError,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _not_found(transaction_id: int) -> HTTPException:
    """The single 404 raised for an unknown or soft-deleted transaction."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Transaction {transaction_id} does not exist",
    )


def _invalid(error: InvalidTransactionError) -> HTTPException:
    """A rule that needs the database was broken by the request."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _category_not_found(error: CategoryNotFoundError) -> HTTPException:
    """The same 404 as an account, so a category that is gone reads the same way."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Category {error} does not exist or is no longer in use",
    )


def _response(detail: TransactionDetail) -> TransactionResponse:
    """A transaction and its postings, in the shape the API promises."""
    return TransactionResponse(
        id=detail.transaction.id,
        transaction_date=detail.transaction.transaction_date,
        merchant=detail.transaction.merchant,
        note=detail.transaction.note,
        source=detail.transaction.source,
        postings=[PostingResponse.model_validate(posting) for posting in detail.postings],
    )


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "A rule the database holds was broken"},
        status.HTTP_404_NOT_FOUND: {"description": "An account does not exist"},
    },
)
def create(
    payload: MovementCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> TransactionResponse:
    """Record an expense, an income or a transfer."""
    try:
        if isinstance(payload, TransferCreate):
            transaction = transactions.record_transfer(
                db,
                user.id,
                payload.from_account_id,
                payload.to_account_id,
                payload.amount_paise,
                payload.transaction_date,
                payload.note,
            )
        elif isinstance(payload, IncomeCreate):
            transaction = transactions.record_income(
                db,
                user.id,
                payload.account_id,
                payload.amount_paise,
                payload.transaction_date,
                payload.merchant,
                payload.note,
                payload.category_id,
                payload.parts,
            )
        else:
            transaction = transactions.record_expense(
                db,
                user.id,
                payload.account_id,
                payload.amount_paise,
                payload.transaction_date,
                payload.merchant,
                payload.note,
                payload.category_id,
                payload.parts,
            )
        detail = transactions.transaction_detail(db, user.id, transaction.id)
    except AccountNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {error} does not exist or is no longer in use",
        ) from error
    except CategoryNotFoundError as error:
        raise _category_not_found(error) from error
    except InvalidTransactionError as error:
        raise _invalid(error) from error

    return _response(detail)


@router.get("", response_model=list[TransactionResponse])
def index(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    account_id: int | None = None,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    kind: PostingKind | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TransactionResponse]:
    """The user's transactions, newest first, filtered and paginated.

    `from` and `to` are inclusive dates on the transaction. The filters combine.
    """
    found = transactions.list_transactions(
        db,
        user.id,
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        kind=kind,
        limit=limit,
        offset=offset,
    )
    return [_response(detail) for detail in found]


@router.get("/suggestions", response_model=list[SuggestionResponse])
def suggestions(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    limit: int = Query(default=8, ge=1, le=50),
    on: date | None = None,
) -> list[SuggestionResponse]:
    """The names worth offering for fast entry, most used first.

    Each one carries how it was recorded last, so one tap records it again. `on`
    is the day to count the window back from, and defaults to today; a client
    sends it only when it is showing a day of its own.
    """
    found = transactions.merchant_suggestions(db, user.id, on=on or date.today(), limit=limit)
    return [SuggestionResponse.model_validate(row) for row in found]


@router.get("/streak", response_model=StreakResponse)
def streak(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> StreakResponse:
    """How many days in a row something has been recorded, and whether today is one."""
    today = date.today()
    days, today_recorded = transactions.streak(db, user.id, today)
    return StreakResponse(days=days, today_recorded=today_recorded)


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    responses={status.HTTP_404_NOT_FOUND: {"description": "The transaction does not exist"}},
)
def show(
    transaction_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> TransactionResponse:
    """One transaction, with its postings."""
    try:
        detail = transactions.transaction_detail(db, user.id, transaction_id)
    except TransactionNotFoundError as error:
        raise _not_found(transaction_id) from error
    return _response(detail)


@router.patch(
    "/{transaction_id}",
    response_model=TransactionResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "A rule the database holds was broken"},
        status.HTTP_404_NOT_FOUND: {"description": "The transaction does not exist"},
    },
)
def patch(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> TransactionResponse:
    """Change the date, merchant, note, the amount, or the filing of a movement."""
    try:
        transactions.update_transaction(db, user.id, transaction_id, payload)
        detail = transactions.transaction_detail(db, user.id, transaction_id)
    except TransactionNotFoundError as error:
        raise _not_found(transaction_id) from error
    except CategoryNotFoundError as error:
        raise _category_not_found(error) from error
    except InvalidTransactionError as error:
        raise _invalid(error) from error
    return _response(detail)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"description": "The transaction does not exist"}},
)
def destroy(
    transaction_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    """Soft-delete a transaction and its postings. The rows are kept."""
    try:
        transactions.soft_delete_transaction(db, user.id, transaction_id)
    except TransactionNotFoundError as error:
        raise _not_found(transaction_id) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
