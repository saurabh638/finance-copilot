"""Request and response shapes for balance checks."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class BalanceCheckCreate(BaseModel):
    """What the user brings: the real balance, and whether to write the gap off.

    `adjust` has no default on purpose. Writing a difference off moves real
    figures, so the request has to say what it wants rather than have it assumed.
    """

    on: date
    stated_balance_paise: int
    adjust: bool


class BalanceCheckSummaryResponse(BaseModel):
    """One check as it is kept: the figures, as they were at the time."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    checked_on: date
    computed_balance_paise: int
    stated_balance_paise: int
    difference_paise: int
    # Set only when the difference was written off, so the write-off can be found.
    adjustment_transaction_id: int | None


class BalanceCheckResponse(BalanceCheckSummaryResponse):
    """The answer to a check just made, including the nudge.

    The warning is advice about what has just happened by today's threshold, so
    it belongs to this answer and not to the history of past checks.
    """

    warning: bool
    threshold_paise: int


class AdjustmentShareResponse(BaseModel):
    """Write-offs against spending for one month, as positive magnitudes."""

    month: date
    spend_paise: int
    adjustments_paise: int
    # A whole percent, rounded. Zero when the month has no spending to compare to.
    share_percent: int
