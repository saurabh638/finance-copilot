"""Enumerations shared by the models."""

from enum import StrEnum


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
