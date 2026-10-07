"""SQLAlchemy models. Importing this package registers every table."""

from app.models.account import Account
from app.models.balance_check import BalanceCheck
from app.models.base import Base
from app.models.category import Category
from app.models.enums import (
    AccountType,
    CaptureMode,
    CategoryKind,
    OccurrenceState,
    PostingKind,
    RateFrequency,
    RecurringFrequency,
    TransactionSource,
)
from app.models.interest_credit import InterestCredit
from app.models.interest_rate import InterestRate
from app.models.login_failure import LoginFailure
from app.models.posting import Posting
from app.models.recurring_item import RecurringItem
from app.models.recurring_occurrence import RecurringOccurrence
from app.models.session import Session
from app.models.transaction import Transaction
from app.models.user import User

__all__ = [
    "Account",
    "AccountType",
    "BalanceCheck",
    "Base",
    "CaptureMode",
    "Category",
    "CategoryKind",
    "InterestCredit",
    "InterestRate",
    "LoginFailure",
    "OccurrenceState",
    "Posting",
    "PostingKind",
    "RateFrequency",
    "RecurringFrequency",
    "RecurringItem",
    "RecurringOccurrence",
    "Session",
    "Transaction",
    "TransactionSource",
    "User",
]
