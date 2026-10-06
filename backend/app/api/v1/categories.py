"""Category endpoints: the tree a client reads and edits.

Thin layer: parse the request, call one service function, translate a service
error into an HTTP status. No tree rules live here.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_session
from app.models import User
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    DefaultsResponse,
    SpendReportResponse,
)
from app.services import categories
from app.services.categories import (
    CategoryInUseError,
    CategoryNotFoundError,
    InvalidCategoryError,
)

router = APIRouter(prefix="/categories", tags=["categories"])


def _not_found(category_id: int) -> HTTPException:
    """The single 404 raised for an unknown or removed category."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Category {category_id} does not exist",
    )


def _invalid(error: InvalidCategoryError) -> HTTPException:
    """A tree rule the database holds was broken."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _in_use(error: CategoryInUseError) -> HTTPException:
    """The request is fine; the tree is not in a state where it can be done."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get("", response_model=list[CategoryResponse])
def index(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[CategoryResponse]:
    """The user's categories: each branch, then the names under it."""
    return [CategoryResponse.model_validate(row) for row in categories.list_categories(db, user.id)]


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"description": "A rule of the tree was broken"}},
)
def create(
    payload: CategoryCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CategoryResponse:
    """Add a name to the tree, as a branch of its own or under one."""
    try:
        made = categories.create_category(
            db, user.id, payload.name, kind=payload.kind, parent_id=payload.parent_id
        )
    except CategoryNotFoundError as error:
        raise _not_found(payload.parent_id or 0) from error
    except InvalidCategoryError as error:
        raise _invalid(error) from error

    return CategoryResponse.model_validate(made)


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "A rule of the tree was broken"},
        status.HTTP_404_NOT_FOUND: {"description": "The category does not exist"},
    },
)
def update(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CategoryResponse:
    """Rename a category, move it in the tree, or both."""
    try:
        changed = categories.update_category(
            db,
            user.id,
            category_id,
            name=payload.name,
            move_to_parent_id=payload.parent_id,
            is_moving="parent_id" in payload.model_fields_set,
        )
    except CategoryNotFoundError as error:
        raise _not_found(category_id) from error
    except InvalidCategoryError as error:
        raise _invalid(error) from error

    return CategoryResponse.model_validate(changed)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "The category does not exist"},
        status.HTTP_409_CONFLICT: {"description": "Something is filed under the category"},
    },
)
def remove(
    category_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    """Remove a category. The row is kept, so the history stays readable."""
    try:
        categories.remove_category(db, user.id, category_id)
    except CategoryNotFoundError as error:
        raise _not_found(category_id) from error
    except CategoryInUseError as error:
        raise _in_use(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/spend", response_model=SpendReportResponse)
def spend(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> SpendReportResponse:
    """What was spent in a period: every expense category, and the money in none.

    `from` and `to` are inclusive dates on the transaction, and either may be
    left out. A category with nothing spent is a row of zeros rather than a
    missing row, so the tree the client draws is the whole tree; spending filed
    under no category has no row at all, so it comes back beside them and is
    counted in the period's `total_paise`.
    """
    return SpendReportResponse.model_validate(
        categories.spend_by_category(db, user.id, from_date=from_date, to_date=to_date)
    )


@router.post("/defaults", response_model=DefaultsResponse)
def create_defaults(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DefaultsResponse:
    """Seed the default set, which does something only on an empty tree."""
    created = categories.seed_defaults(db, user.id)
    return DefaultsResponse(
        created=[CategoryResponse.model_validate(row) for row in created],
    )
