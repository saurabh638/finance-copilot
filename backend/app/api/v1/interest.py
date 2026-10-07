"""Interest endpoints: what a period earned, and crediting the bank's figure.

Thin layer: parse the request, call one service function, translate a service
error into an HTTP status. No interest is worked out here.

The routes hang off an account, because interest belongs to one: a rate, a
balance and a bank statement are all the account's.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_session
from app.models import User
from app.schemas.interest import (
    AccountInterestResponse,
    ConfirmRequest,
    InterestCreditResponse,
    ProposeRequest,
)
from app.services import interest
from app.services.accounts import AccountNotFoundError
from app.services.interest import (
    InterestConflictError,
    InterestNotFoundError,
    InvalidInterestError,
)
from app.services.transactions import InvalidTransactionError

router = APIRouter(prefix="/accounts", tags=["interest"])


def _account_not_found(error: AccountNotFoundError) -> HTTPException:
    """The account is not the user's, or is gone."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Account {error} does not exist or is no longer in use",
    )


def _period_not_found(credit_id: int) -> HTTPException:
    """The single 404 raised for an unknown or dropped period."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Interest period {credit_id} does not exist",
    )


def _invalid(error: Exception) -> HTTPException:
    """A rule the database holds was broken by the request."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _conflict(error: InterestConflictError) -> HTTPException:
    """The request is fine; the period is not in a state where it can be done."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get(
    "/{account_id}/interest",
    response_model=AccountInterestResponse,
    responses={status.HTTP_404_NOT_FOUND: {"description": "The account does not exist"}},
)
def show(
    account_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AccountInterestResponse:
    """What this account has been credited, and what is waiting to be."""
    try:
        found = interest.summary(db, user.id, account_id)
    except AccountNotFoundError as error:
        raise _account_not_found(error) from error

    return AccountInterestResponse.model_validate(found)


@router.post(
    "/{account_id}/interest/propose",
    response_model=list[InterestCreditResponse],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Interest cannot be worked out"},
        status.HTTP_404_NOT_FOUND: {"description": "The account does not exist"},
    },
)
def propose(
    account_id: int,
    payload: ProposeRequest | None = None,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[InterestCreditResponse]:
    """Work out every period that has finished, up to a day. Running it twice is safe."""
    through = date.today() if payload is None or payload.through is None else payload.through

    try:
        made = interest.propose(db, user.id, account_id, through=through)
    except AccountNotFoundError as error:
        raise _account_not_found(error) from error
    except InvalidInterestError as error:
        raise _invalid(error) from error

    return [InterestCreditResponse.model_validate(row) for row in made]


@router.post(
    "/{account_id}/interest/{credit_id}/confirm",
    response_model=InterestCreditResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "A rule the database holds was broken"},
        status.HTTP_404_NOT_FOUND: {"description": "The account or the period does not exist"},
        status.HTTP_409_CONFLICT: {"description": "The period is already credited"},
    },
)
def confirm(
    account_id: int,
    credit_id: int,
    payload: ConfirmRequest | None = None,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> InterestCreditResponse:
    """Credit a period, for the figure the bank paid."""
    today = date.today()
    asked = ConfirmRequest() if payload is None else payload

    try:
        credited = interest.confirm(
            db,
            user.id,
            account_id,
            credit_id,
            on=asked.on if asked.on is not None else today,
            credited_paise=asked.credited_paise,
        )
    except AccountNotFoundError as error:
        raise _account_not_found(error) from error
    except InterestNotFoundError as error:
        raise _period_not_found(credit_id) from error
    except InterestConflictError as error:
        raise _conflict(error) from error
    except (InvalidInterestError, InvalidTransactionError) as error:
        raise _invalid(error) from error

    return InterestCreditResponse.model_validate(credited)


@router.delete(
    "/{account_id}/interest/{credit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "The account or the period does not exist"},
        status.HTTP_409_CONFLICT: {"description": "The period is already credited"},
    },
)
def drop(
    account_id: int,
    credit_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    """Throw a proposal away. A credited period is removed by removing its movement."""
    try:
        interest.drop(db, user.id, account_id, credit_id)
    except AccountNotFoundError as error:
        raise _account_not_found(error) from error
    except InterestNotFoundError as error:
        raise _period_not_found(credit_id) from error
    except InterestConflictError as error:
        raise _conflict(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
