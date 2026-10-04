"""Request and response shapes for accounts."""

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AccountType, CaptureMode


class AccountCreate(BaseModel):
    """Fields accepted when creating an account."""

    name: str = Field(min_length=1, max_length=100)
    type: AccountType
    purpose: str | None = Field(default=None, max_length=100)
    capture_mode: CaptureMode
    parent_id: int | None = None
    opening_balance_paise: int
    opening_date: date
    statement_day: int | None = Field(default=None, ge=1, le=31)
    due_day: int | None = Field(default=None, ge=1, le=31)
    is_active: bool = True

    @model_validator(mode="after")
    def _check_type_specific_fields(self) -> Self:
        """Enforce the rules that need only the payload, not the database."""
        if self.type is not AccountType.CREDIT_CARD and (
            self.statement_day is not None or self.due_day is not None
        ):
            raise ValueError("statement_day and due_day are only for credit_card accounts")
        if (self.type is AccountType.POT) != (self.parent_id is not None):
            raise ValueError("a pot needs a parent account, and only a pot may have one")
        return self


class AccountUpdate(BaseModel):
    """Fields that may change; omitted fields are left alone. `type` is fixed."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    purpose: str | None = Field(default=None, max_length=100)
    capture_mode: CaptureMode | None = None
    parent_id: int | None = None
    opening_balance_paise: int | None = None
    opening_date: date | None = None
    statement_day: int | None = Field(default=None, ge=1, le=31)
    due_day: int | None = Field(default=None, ge=1, le=31)
    is_active: bool | None = None


class AccountResponse(BaseModel):
    """An account as returned by the API. Money is integer paise."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: AccountType
    purpose: str | None
    capture_mode: CaptureMode
    parent_id: int | None
    opening_balance_paise: int
    opening_date: date
    statement_day: int | None
    due_day: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
