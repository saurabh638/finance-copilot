"""Request and response shapes for transactions and balances."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PostingKind, TransactionSource


class BalanceResponse(BaseModel):
    """An account's balance, and the two figures it was worked out from.

    The parts are reported as well as the answer, so a figure can always be
    explained rather than merely trusted. Money is integer paise throughout.
    """

    account_id: int
    as_of: date | None
    opening_balance_paise: int
    postings_paise: int
    balance_paise: int


class MovementBase(BaseModel):
    """What every movement the user records by hand has in common."""

    transaction_date: date
    merchant: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)


class ExpenseCreate(MovementBase):
    """Money leaving one account. The amount is positive; the kind sets the sign."""

    kind: Literal["expense"]
    account_id: int
    amount_paise: int = Field(gt=0)


class IncomeCreate(MovementBase):
    """Money arriving in one account."""

    kind: Literal["income"]
    account_id: int
    amount_paise: int = Field(gt=0)


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

    An omitted field is left alone; an explicit null clears it. The amount may
    only be changed when the transaction has a single posting, because a transfer
    is two postings that must keep summing to zero.
    """

    transaction_date: date | None = None
    merchant: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)
    amount_paise: int | None = Field(default=None, gt=0)


class PostingResponse(BaseModel):
    """One account's side of a transaction, as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    amount_paise: int
    kind: PostingKind


class TransactionResponse(BaseModel):
    """A transaction and the postings that carry its amounts."""

    id: int
    transaction_date: date
    merchant: str | None
    note: str | None
    source: TransactionSource
    postings: list[PostingResponse]
