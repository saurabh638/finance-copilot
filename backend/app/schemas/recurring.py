"""Request and response shapes for recurring items."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PostingKind, RecurringFrequency

NAME_MAX = 80


class RecurringItemCreate(BaseModel):
    """A new repeating item.

    The rhythm is given whole with its frequency: a monthly item carries a day of
    the month, a weekly one a weekday, and the service refuses one that is half
    given rather than guessing which half was meant.
    """

    name: str = Field(min_length=1, max_length=NAME_MAX)
    kind: PostingKind
    amount_paise: int = Field(gt=0)
    account_id: int
    frequency: RecurringFrequency
    starts_on: date
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    weekday: int | None = Field(default=None, ge=0, le=6)
    category_id: int | None = None
    ends_on: date | None = None


class RecurringItemUpdate(BaseModel):
    """What may change. An omitted field is left alone.

    `category_id: null` clears the filing, so the router asks whether the field
    was sent rather than reading its value. `frequency` changes the rhythm and
    brings its own day with it.
    """

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX)
    amount_paise: int | None = Field(default=None, gt=0)
    account_id: int | None = None
    category_id: int | None = None
    frequency: RecurringFrequency | None = None
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    weekday: int | None = Field(default=None, ge=0, le=6)
    starts_on: date | None = None
    ends_on: date | None = None


class RecurringItemResponse(BaseModel):
    """One item as it is kept."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: PostingKind
    amount_paise: int
    account_id: int
    category_id: int | None
    frequency: RecurringFrequency
    day_of_month: int | None
    weekday: int | None
    starts_on: date
    ends_on: date | None
    is_active: bool


class DueItemResponse(BaseModel):
    """An item and the day it is owed for.

    The day comes out with the item because it is not always today: a rent due on
    the 1st that is confirmed on the 28th is still the 1st's rent, and the row
    that gets written has to say so.
    """

    model_config = ConfigDict(from_attributes=True)

    item: RecurringItemResponse
    due_on: date


class ConfirmRequest(BaseModel):
    """Confirming a period, optionally for a different amount this time."""

    amount_paise: int | None = Field(default=None, gt=0)


class ConfirmedResponse(BaseModel):
    """What confirming wrote: the item, the day, and the movement that recorded it."""

    model_config = ConfigDict(from_attributes=True)

    item: RecurringItemResponse
    due_on: date
    transaction_id: int
