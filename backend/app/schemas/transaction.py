"""Request and response shapes for transactions and balances."""

from datetime import date

from pydantic import BaseModel


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
