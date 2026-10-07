"""Recurring item endpoints: the plan, what it owes, and settling a period.

Thin layer: parse the request, call one service function, translate a service
error into an HTTP status. No rhythms and no money are worked out here.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_session
from app.models import User
from app.schemas.recurring import (
    ConfirmedResponse,
    ConfirmRequest,
    DueItemResponse,
    RecurringItemCreate,
    RecurringItemResponse,
    RecurringItemUpdate,
)
from app.services import recurring
from app.services.accounts import AccountNotFoundError
from app.services.categories import CategoryNotFoundError
from app.services.recurring import (
    InvalidRecurringItemError,
    RecurringItemConflictError,
    RecurringItemNotFoundError,
)
from app.services.transactions import InvalidTransactionError

router = APIRouter(prefix="/recurring-items", tags=["recurring"])


def _not_found(item_id: int) -> HTTPException:
    """The single 404 raised for an unknown or removed item."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Recurring item {item_id} does not exist",
    )


def _invalid(error: Exception) -> HTTPException:
    """A rule the database holds was broken by the request."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _conflict(error: RecurringItemConflictError) -> HTTPException:
    """The request is fine; this period is not in a state where it can be done."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


def _missing_account_or_category(error: Exception) -> HTTPException:
    """An account or a category the request named is gone, or is not the user's."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{error} does not exist or is no longer in use",
    )


@router.get("", response_model=list[RecurringItemResponse])
def index(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[RecurringItemResponse]:
    """Every live item, paused ones included."""
    return [RecurringItemResponse.model_validate(row) for row in recurring.list_items(db, user.id)]


@router.get("/due", response_model=list[DueItemResponse])
def due(
    on: date | None = Query(default=None, description="The day to ask about; today if omitted"),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[DueItemResponse]:
    """What is owed on a day: the active items, on their day, not yet settled."""
    day = on if on is not None else date.today()
    return [DueItemResponse.model_validate(row) for row in recurring.due_items(db, user.id, day)]


@router.post(
    "",
    response_model=RecurringItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "A rule the database holds was broken"},
        status.HTTP_404_NOT_FOUND: {"description": "An account or category does not exist"},
    },
)
def create(
    payload: RecurringItemCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RecurringItemResponse:
    """Plan something that repeats."""
    try:
        made = recurring.create_item(
            db,
            user.id,
            name=payload.name,
            kind=payload.kind,
            amount_paise=payload.amount_paise,
            account_id=payload.account_id,
            frequency=payload.frequency,
            starts_on=payload.starts_on,
            day_of_month=payload.day_of_month,
            weekday=payload.weekday,
            category_id=payload.category_id,
            ends_on=payload.ends_on,
        )
    except (AccountNotFoundError, CategoryNotFoundError) as error:
        raise _missing_account_or_category(error) from error
    except (InvalidRecurringItemError, InvalidTransactionError) as error:
        raise _invalid(error) from error

    return RecurringItemResponse.model_validate(made)


@router.patch(
    "/{item_id}",
    response_model=RecurringItemResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "A rule the database holds was broken"},
        status.HTTP_404_NOT_FOUND: {"description": "The item does not exist"},
    },
)
def update(
    item_id: int,
    payload: RecurringItemUpdate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RecurringItemResponse:
    """Change an item's plan, never the money it has already recorded."""
    rhythm: recurring.RhythmChange | None = None
    if "frequency" in payload.model_fields_set:
        if payload.frequency is None:
            raise _invalid(InvalidRecurringItemError("a rhythm change needs a frequency"))
        rhythm = recurring.RhythmChange(
            payload.frequency,
            day_of_month=payload.day_of_month,
            weekday=payload.weekday,
        )

    try:
        changed = recurring.update_item(
            db,
            user.id,
            item_id,
            name=payload.name,
            amount_paise=payload.amount_paise,
            account_id=payload.account_id,
            category_id=payload.category_id,
            is_filing="category_id" in payload.model_fields_set,
            rhythm=rhythm,
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
        )
    except RecurringItemNotFoundError as error:
        raise _not_found(item_id) from error
    except (AccountNotFoundError, CategoryNotFoundError) as error:
        raise _missing_account_or_category(error) from error
    except (InvalidRecurringItemError, InvalidTransactionError) as error:
        raise _invalid(error) from error

    return RecurringItemResponse.model_validate(changed)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"description": "The item does not exist"}},
)
def remove(
    item_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    """Remove an item. The periods it already dealt with keep their record."""
    try:
        recurring.soft_delete_item(db, user.id, item_id)
    except RecurringItemNotFoundError as error:
        raise _not_found(item_id) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{item_id}/pause",
    response_model=RecurringItemResponse,
    responses={status.HTTP_404_NOT_FOUND: {"description": "The item does not exist"}},
)
def pause(
    item_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RecurringItemResponse:
    """Stop offering this item. Nothing owed is recorded."""
    return _set_active(db, user.id, item_id, is_active=False)


@router.post(
    "/{item_id}/resume",
    response_model=RecurringItemResponse,
    responses={status.HTTP_404_NOT_FOUND: {"description": "The item does not exist"}},
)
def resume(
    item_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> RecurringItemResponse:
    """Start offering this item again."""
    return _set_active(db, user.id, item_id, is_active=True)


def _set_active(
    db: Session, user_id: int, item_id: int, *, is_active: bool
) -> RecurringItemResponse:
    """Pausing and resuming are one service call with two words for it."""
    try:
        changed = recurring.set_active(db, user_id, item_id, is_active=is_active)
    except RecurringItemNotFoundError as error:
        raise _not_found(item_id) from error

    return RecurringItemResponse.model_validate(changed)


@router.post(
    "/{item_id}/confirm",
    response_model=ConfirmedResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "A rule the database holds was broken"},
        status.HTTP_404_NOT_FOUND: {"description": "The item does not exist"},
        status.HTTP_409_CONFLICT: {"description": "The period is already settled"},
    },
)
def confirm(
    item_id: int,
    payload: ConfirmRequest | None = None,
    on: date | None = Query(default=None, description="The day to ask about; today if omitted"),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ConfirmedResponse:
    """Record this period's money, as one movement dated the day it was owed."""
    day = on if on is not None else date.today()

    try:
        written = recurring.confirm(
            db,
            user.id,
            item_id,
            on=day,
            amount_paise=None if payload is None else payload.amount_paise,
        )
    except RecurringItemNotFoundError as error:
        raise _not_found(item_id) from error
    except RecurringItemConflictError as error:
        raise _conflict(error) from error
    except InvalidTransactionError as error:
        raise _invalid(error) from error

    return ConfirmedResponse.model_validate(written)


@router.post(
    "/{item_id}/skip",
    response_model=DueItemResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "The item does not exist"},
        status.HTTP_409_CONFLICT: {"description": "The period is already settled"},
    },
)
def skip(
    item_id: int,
    on: date | None = Query(default=None, description="The day to ask about; today if omitted"),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DueItemResponse:
    """Say this period is not happening. Nothing is recorded at all."""
    day = on if on is not None else date.today()

    try:
        settled = recurring.skip(db, user.id, item_id, on=day)
    except RecurringItemNotFoundError as error:
        raise _not_found(item_id) from error
    except RecurringItemConflictError as error:
        raise _conflict(error) from error

    return DueItemResponse.model_validate(settled)
