"""Enumerations shared by the models, and their rendering into SQL."""

from enum import Enum, StrEnum


class AccountType(StrEnum):
    """What kind of account this is. A pot is a named sub-balance of a parent."""

    SAVINGS = "savings"
    CURRENT = "current"
    CREDIT_CARD = "credit_card"
    WALLET = "wallet"
    CASH = "cash"
    FD = "fd"
    RD = "rd"
    LOAN = "loan"
    POT = "pot"


class CaptureMode(StrEnum):
    """How the transactions for an account are expected to arrive."""

    STATEMENT_IMPORT = "statement_import"
    MANUAL_ONLY = "manual_only"
    HYBRID = "hybrid"


class RateFrequency(StrEnum):
    """How often interest at a given rate is credited."""

    DAILY = "daily"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class CategoryKind(StrEnum):
    """What a category is for, which its children inherit from it.

    `adjustment` is the kind the two write-off names carry, so a balance check's
    difference has a home without pretending to be spending or income.
    """

    EXPENSE = "expense"
    INCOME = "income"
    ADJUSTMENT = "adjustment"


class PostingKind(StrEnum):
    """What one account's side of a transaction is.

    Only expense and income count as spending or earning; a transfer, a card
    payment, a refund and an adjustment must never be counted as either.
    """

    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    INTEREST = "interest"
    FEE = "fee"
    INVESTMENT = "investment"


class TransactionSource(StrEnum):
    """How a transaction arrived, so an imported batch can be reversed whole."""

    MANUAL = "manual"
    IMPORT = "import"
    RECURRING = "recurring"
    AI_APPROVED = "ai_approved"


def enum_values(enum_class: type[Enum]) -> list[str]:
    """Persist the lower-case enum values rather than the member names."""
    return [str(member.value) for member in enum_class]


def allowed_values(column: str, enum_class: type[Enum]) -> str:
    """A SQL ``IN`` list for an enum column, so the database rejects bad values."""
    allowed = ", ".join(f"'{member.value}'" for member in enum_class)
    return f"{column} IN ({allowed})"
