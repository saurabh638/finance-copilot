"""Account endpoints.

Thin layer: parse the request, call one service function, translate a service
error into an HTTP status. No business rules live here.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_session
from app.models import User
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.services.accounts import (
    AccountNotFoundError,
    InvalidAccountError,
    create_account,
    get_account,
    list_accounts,
    soft_delete_account,
    update_account,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _not_found(account_id: int) -> HTTPException:
    """The single 404 raised for an unknown or soft-deleted account."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Account {account_id} does not exist",
    )


def _invalid(error: InvalidAccountError) -> HTTPException:
    """A business rule that needs the database was broken by the payload."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: AccountCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AccountResponse:
    """Create an account for the signed-in user."""
    try:
        account = create_account(db, user.id, payload)
    except InvalidAccountError as error:
        raise _invalid(error) from error
    return AccountResponse.model_validate(account)


@router.get("", response_model=list[AccountResponse])
def index(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AccountResponse]:
    """List the signed-in user's live accounts, oldest first."""
    accounts = list_accounts(db, user.id, limit, offset)
    return [AccountResponse.model_validate(account) for account in accounts]


@router.get("/{account_id}", response_model=AccountResponse)
def show(
    account_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AccountResponse:
    """Return one account, or 404 when it is unknown or soft-deleted."""
    try:
        account = get_account(db, user.id, account_id)
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error
    return AccountResponse.model_validate(account)


@router.patch("/{account_id}", response_model=AccountResponse)
def patch(
    account_id: int,
    payload: AccountUpdate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AccountResponse:
    """Apply the provided fields to an account. `type` cannot change."""
    try:
        account = update_account(db, user.id, account_id, payload)
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error
    except InvalidAccountError as error:
        raise _invalid(error) from error
    return AccountResponse.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def destroy(
    account_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    """Soft-delete an account. The row and its history are kept."""
    try:
        soft_delete_account(db, user.id, account_id)
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
