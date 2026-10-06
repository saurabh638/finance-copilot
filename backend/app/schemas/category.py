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


class SpendReportResponse(BaseModel):
    """A period's spending: the tree, the money in no category, and the whole.

    Spending filed under no category has no row to appear in, so it is reported
    beside the rows rather than left out: otherwise the rows would not add up to
    what the period actually cost. `total_paise` is the two together, so a client
    never has to decide what counts as spending.
    """

    model_config = ConfigDict(from_attributes=True)

    rows: list[CategorySpendResponse]
    uncategorised_paise: int
    total_paise: int
