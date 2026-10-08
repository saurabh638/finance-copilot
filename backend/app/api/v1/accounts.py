"""Account endpoints, including each account's interest-rate history and balance.

Thin layer: parse the request, call one service function, translate a service
error into an HTTP status. No business rules live here.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.db import get_session
from app.models import User
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate
from app.schemas.balance_check import (
    AdjustmentShareResponse,
    BalanceCheckCreate,
    BalanceCheckResponse,
    BalanceCheckSummaryResponse,
)
from app.schemas.interest_rate import InterestRateCreate, InterestRateResponse
from app.schemas.transaction import BalanceResponse
from app.services import balance_checks, interest_rates, transactions
from app.services.accounts import (
    AccountNotFoundError,
    InvalidAccountError,
    create_account,
    get_account,
    list_accounts,
    soft_delete_account,
    update_account,
)
from app.services.balance_checks import BalanceCheckConflictError, BalanceCheckNotFoundError
from app.services.interest_rates import DuplicateRateError, RateNotFoundError
from app.services.transactions import InvalidTransactionError

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


@router.get(
    "/{account_id}/balance",
    response_model=BalanceResponse,
    responses={status.HTTP_404_NOT_FOUND: {"description": "The account does not exist"}},
)
def read_balance(
    account_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    as_of: date | None = None,
) -> BalanceResponse:
    """The account's balance, and the figures it was worked out from."""
    try:
        found = transactions.balance(db, user.id, account_id, as_of)
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error

    return BalanceResponse(
        account_id=found.account_id,
        as_of=found.as_of,
        opening_balance_paise=found.opening_balance_paise,
        postings_paise=found.postings_paise,
        interest_paise=found.interest_paise,
        balance_paise=found.balance_paise,
    )


def _rate_not_found(rate_id: int) -> HTTPException:
    """The single 404 raised for an unknown or soft-deleted rate."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Interest rate {rate_id} does not exist",
    )


def _duplicate(error: DuplicateRateError) -> HTTPException:
    """The account already has a live rate starting on that date."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.post(
    "/{account_id}/interest-rates",
    response_model=InterestRateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "The account does not exist"},
        status.HTTP_409_CONFLICT: {"description": "A live rate already starts on that date"},
    },
)
def create_rate(
    account_id: int,
    payload: InterestRateCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> InterestRateResponse:
    """Record a rate from a given date. Earlier rates are left untouched."""
    try:
        rate = interest_rates.create_rate(db, user.id, account_id, payload)
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error
    except DuplicateRateError as error:
        raise _duplicate(error) from error
    return InterestRateResponse.model_validate(rate)


@router.get(
    "/{account_id}/interest-rates",
    response_model=list[InterestRateResponse],
    responses={status.HTTP_404_NOT_FOUND: {"description": "The account does not exist"}},
)
def list_interest_rates(
    account_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[InterestRateResponse]:
    """List an account's rates, newest first."""
    try:
        rates = interest_rates.list_rates(db, user.id, account_id, limit, offset)
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error
    return [InterestRateResponse.model_validate(rate) for rate in rates]


@router.delete(
    "/{account_id}/interest-rates/{rate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "The account or the rate does not exist"}
    },
)
def delete_rate(
    account_id: int,
    rate_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    """Soft-delete a rate. The row is kept, so the history stays auditable."""
    try:
        interest_rates.soft_delete_rate(db, user.id, account_id, rate_id)
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error
    except RateNotFoundError as error:
        raise _rate_not_found(rate_id) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _too_early(error: InvalidTransactionError) -> HTTPException:
    """The one 400 a date rule produces, worded by the service."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _check_not_found(check_id: int) -> HTTPException:
    """The single 404 raised for a check that is not there."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Balance check {check_id} does not exist",
    )


@router.post(
    "/{account_id}/balance-checks",
    response_model=BalanceCheckResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "The check date is before the account opened"},
        status.HTTP_404_NOT_FOUND: {"description": "The account does not exist"},
    },
)
def create_balance_check(
    account_id: int,
    payload: BalanceCheckCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> BalanceCheckResponse:
    """Compare the ledger with the bank, and write the difference off if asked.

    The threshold is advice, not a rule: a large difference is flagged and the
    write-off still happens when the user has decided on it.
    """
    try:
        outcome = balance_checks.check_balance(
            db,
            user.id,
            account_id,
            on=payload.on,
            stated_paise=payload.stated_balance_paise,
            adjust=payload.adjust,
            warning_threshold_paise=get_settings().balance_check_warning_paise,
        )
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error
    except InvalidTransactionError as error:
        raise _too_early(error) from error

    summary = BalanceCheckSummaryResponse.model_validate(outcome.record)
    return BalanceCheckResponse(
        **summary.model_dump(),
        warning=outcome.warning,
        threshold_paise=outcome.threshold_paise,
    )


@router.get(
    "/{account_id}/balance-checks",
    response_model=list[BalanceCheckSummaryResponse],
    responses={status.HTTP_404_NOT_FOUND: {"description": "The account does not exist"}},
)
def index_balance_checks(
    account_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[BalanceCheckSummaryResponse]:
    """The account's balance checks, most recent first."""
    try:
        found = balance_checks.list_checks(db, user.id, account_id)
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error

    return [BalanceCheckSummaryResponse.model_validate(record) for record in found]


@router.post(
    "/{account_id}/balance-checks/{check_id}/adjust",
    response_model=BalanceCheckResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "The account or the check does not exist"},
        status.HTTP_409_CONFLICT: {
            "description": "The check is already written off, or has no difference"
        },
    },
)
def adjust_balance_check(
    account_id: int,
    check_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> BalanceCheckResponse:
    """Write off the difference a check found earlier.

    The figures are the ones recorded at the time, so the write-off cannot drift
    from what the user actually saw.
    """
    try:
        outcome = balance_checks.adjust_check(
            db,
            user.id,
            account_id,
            check_id,
            get_settings().balance_check_warning_paise,
        )
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error
    except BalanceCheckNotFoundError as error:
        raise _check_not_found(check_id) from error
    except BalanceCheckConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    summary = BalanceCheckSummaryResponse.model_validate(outcome.record)
    return BalanceCheckResponse(
        **summary.model_dump(),
        warning=outcome.warning,
        threshold_paise=outcome.threshold_paise,
    )


@router.get(
    "/{account_id}/adjustment-share",
    response_model=AdjustmentShareResponse,
    responses={status.HTTP_404_NOT_FOUND: {"description": "The account does not exist"}},
)
def read_adjustment_share(
    account_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    month: date | None = None,
) -> AdjustmentShareResponse:
    """Write-offs as a share of the month's spending, for the month given."""
    try:
        share = balance_checks.adjustment_share(db, user.id, account_id, month or date.today())
    except AccountNotFoundError as error:
        raise _not_found(account_id) from error

    return AdjustmentShareResponse(
        month=share.month,
        spend_paise=share.spend_paise,
        adjustments_paise=share.adjustments_paise,
        share_percent=share.share_percent,
    )
