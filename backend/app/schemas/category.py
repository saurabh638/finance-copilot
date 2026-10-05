"""Request and response shapes for the category tree."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CategoryKind

NAME_MAX = 80


class CategoryCreate(BaseModel):
    """A new name in the tree.

    `kind` is required for a top-level category and ignored for a child, which
    carries its parent's kind; the service words the refusal either way.
    """

    name: str = Field(min_length=1, max_length=NAME_MAX)
    kind: CategoryKind | None = None
    parent_id: int | None = None


class CategoryUpdate(BaseModel):
    """What may change: the name, where it sits, or both.

    An omitted field is left alone; an explicit `parent_id: null` moves the
    category to the top level, which is why the router tells the difference.
    """

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX)
    parent_id: int | None = None


class CategoryResponse(BaseModel):
    """One category as it is kept."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None
    kind: CategoryKind


class DefaultsResponse(BaseModel):
    """What the default set added, which is nothing when the tree was not empty."""

    created: list[CategoryResponse]


class CategorySpendResponse(BaseModel):
    """One row of the spend report.

    `direct_paise` is what was filed under this category itself; `total_paise`
    adds everything filed under its children, so a group answers for its whole
    branch. Categories with nothing spent are rows too, with zeros.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None
    kind: CategoryKind
    direct_paise: int
    total_paise: int
