"""Request and response shapes for interest rates."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import RateFrequency

# Matches NUMERIC(7, 4): three digits before the point, four after.
_MAX_RATE = Decimal("999.9999")
_STORED_SCALE = Decimal("0.0001")


class InterestRateCreate(BaseModel):
    """Fields accepted when recording a rate. A change is a new record, never an edit."""

    rate: Decimal = Field(ge=0, le=_MAX_RATE, max_digits=7, decimal_places=4)
    from_date: date
    frequency: RateFrequency
    note: str | None = Field(default=None, max_length=200)

    @field_validator("rate")
    @classmethod
    def _pad_to_the_stored_scale(cls, value: Decimal) -> Decimal:
        """Report 7.1 as 7.1000, the way the column stores it.

        Without this the same rate reads differently depending on the endpoint:
        a create echoes the value as sent, while a later read comes back at the
        column's scale. More than four decimals are already rejected by the
        field constraint, so this only ever pads zeros.
        """
        return value.quantize(_STORED_SCALE)


class InterestRateResponse(BaseModel):
    """A rate as returned by the API.

    `rate` is per cent per annum and is serialised as a string, so the exact
    decimal reaches the client without ever passing through a float. More than
    four decimal places are rejected rather than rounded.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    rate: Decimal
    from_date: date
    frequency: RateFrequency
    note: str | None
    created_at: datetime
    updated_at: datetime
