"""Request and response shapes for transactions and balances."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PostingKind, TransactionSource


class BalanceResponse(BaseModel):
    """An account's balance, the figures it was worked out from, and its interest.

    The parts are reported as well as the answer, so a figure can always be
    explained rather than merely trusted. Money is integer paise throughout.
    `interest_paise` is part of `postings_paise` rather than another part of the
    balance: it is a reading of the movements, so that a client can show how much
    of what moved was interest without adding it twice.
    """

    account_id: int
    as_of: date | None
    opening_balance_paise: int
    postings_paise: int
    interest_paise: int
    balance_paise: int


class MovementBase(BaseModel):
    """What every movement the user records by hand has in common."""

    transaction_date: date
    merchant: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)


class SplitPartCreate(BaseModel):
    """One part of a movement the user split between categories."""

    amount_paise: int = Field(gt=0)
    category_id: int


class OneAccountMovement(MovementBase):
    """Money leaving or arriving at one account.

    The amount is the figure the statement shows. A movement is filed under one
    category, or - when one purchase was really several things - split into
    parts, which must add up to the amount exactly. The two are not mixed.
    """

    account_id: int
    amount_paise: int = Field(gt=0)
    category_id: int | None = None
    parts: list[SplitPartCreate] | None = None


class ExpenseCreate(OneAccountMovement):
    """Money leaving one account. The amount is positive; the kind sets the sign."""

    kind: Literal["expense"]


class IncomeCreate(OneAccountMovement):
    """Money arriving in one account."""

    kind: Literal["income"]


class TransferCreate(MovementBase):
    """Money moving between two accounts, as two postings that sum to zero."""

    kind: Literal["transfer"]
    from_account_id: int
    to_account_id: int
    amount_paise: int = Field(gt=0)


# The discriminator refuses a malformed transfer before any code runs, and gives
# the generated TypeScript client a union it can narrow on.
MovementCreate = Annotated[
    ExpenseCreate | IncomeCreate | TransferCreate,
    Field(discriminator="kind"),
]


class TransactionUpdate(BaseModel):
    """What may change. The accounts and the kind never do.

    An omitted field is left alone; an explicit null clears it. The amount and
    the category may only be changed when the transaction has a single posting,
    because a transfer is two postings that must keep summing to zero.
    """

    transaction_date: date | None = None
    merchant: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)
    amount_paise: int | None = Field(default=None, gt=0)
    category_id: int | None = None


class PostingResponse(BaseModel):
    """One account's side of a transaction, as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    amount_paise: int
    kind: PostingKind
    category_id: int | None


class TransactionResponse(BaseModel):
    """A transaction and the postings that carry its amounts."""

    id: int
    transaction_date: date
    merchant: str | None
    note: str | None
    source: TransactionSource
    postings: list[PostingResponse]


class SuggestionResponse(BaseModel):
    """One name to offer for fast entry, and how it was recorded last.

    `times_used` is how often the name has been recorded, and the rest is the
    most recent time: one tap records the same thing again. `category_id` is null
    for a movement that was split, because a split has no single category.
    """

    model_config = ConfigDict(from_attributes=True)

    merchant: str
    times_used: int
    last_used: date
    account_id: int
    category_id: int | None
    amount_paise: int


class StreakResponse(BaseModel):
    """How many days in a row something has been recorded, and whether today is one.

    A run that ended yesterday is not over: the day is not finished yet.
    """

    days: int
    today_recorded: bool
