"""SQLAlchemy models. Importing this package registers every table."""

from app.models.account import Account
from app.models.balance_check import BalanceCheck
from app.models.base import Base
from app.models.category import Category
from app.models.enums import (
    AccountType,
    CaptureMode,
    CategoryKind,
    PostingKind,
    RateFrequency,
    TransactionSource,
)
from app.models.interest_rate import InterestRate
from app.models.login_failure import LoginFailure
from app.models.posting import Posting
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
    "InterestRate",
    "LoginFailure",
    "Posting",
    "PostingKind",
    "RateFrequency",
    "Session",
    "Transaction",
    "TransactionSource",
    "User",
]
