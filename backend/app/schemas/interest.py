"""Request and response shapes for interest credits."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InterestCreditResponse(BaseModel):
    """One period of interest, proposed or credited.

    Both figures come back: `computed_paise` is what the ledger's arithmetic said
    and `credited_paise` is what the bank paid. A client that shows both is showing
    where the stated day-count convention differs from the bank's.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    period_start: date
    period_end: date
    rate_percent: Decimal
    computed_paise: int
    credited_paise: int | None
    transaction_id: int | None
    confirmed_on: date | None


class AccountInterestResponse(BaseModel):
    """An account's interest: what is credited, and what is waiting to be."""

    model_config = ConfigDict(from_attributes=True)

    credited_paise: int
    uncredited_paise: int
    proposals: list[InterestCreditResponse]
    history: list[InterestCreditResponse]


class ProposeRequest(BaseModel):
    """Working out interest up to a day. An omitted day means today."""

    through: date | None = None


class ConfirmRequest(BaseModel):
    """Confirming a period, for the figure the bank actually paid.

    `credited_paise` is optional: without it the ledger's own figure is credited,
    which is what the common case wants. `on` is the day the confirmation was made,
    which is not the day the interest was paid — that is the period's last day.
    """

    on: date | None = None
    credited_paise: int | None = Field(default=None, gt=0)
