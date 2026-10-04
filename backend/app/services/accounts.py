"""Account business logic and database access.

Soft delete is the only delete. Live accounts are read through `_active_accounts`
so the `deleted_at IS NULL` filter lives in exactly one place.
"""

from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session as DbSession

from app.models import Account, AccountType
from app.schemas.account import AccountCreate, AccountUpdate


class AccountNotFoundError(LookupError):
    """Raised when an account does not exist for the user, or is soft-deleted."""


class InvalidAccountError(ValueError):
    """Raised when an account would break a rule that needs the database."""


def _active_accounts(user_id: int) -> Select[Account]:
    """The one shared filter: soft-deleted rows are never returned."""
    return select(Account).where(Account.user_id == user_id, Account.deleted_at.is_(None))


def list_accounts(db: DbSession, user_id: int, limit: int, offset: int) -> list[Account]:
    """Return the user's live accounts, oldest first, paginated."""
    statement = _active_accounts(user_id).order_by(Account.id).limit(limit).offset(offset)
    return list(db.scalars(statement))


def get_account(db: DbSession, user_id: int, account_id: int) -> Account:
    """Return one live account, or raise AccountNotFoundError."""
    account = db.scalars(_active_accounts(user_id).where(Account.id == account_id)).first()
    if account is None:
        raise AccountNotFoundError(account_id)
    return account


def _validate_parent(db: DbSession, user_id: int, parent_id: int) -> None:
    """A pot's parent must exist, be live, and not itself be a pot."""
    parent = db.scalars(_active_accounts(user_id).where(Account.id == parent_id)).first()
    if parent is None:
        raise InvalidAccountError(f"parent account {parent_id} does not exist")
    if parent.type is AccountType.POT:
        raise InvalidAccountError("a pot cannot be the parent of another pot")


def _validate_state(account: Account) -> None:
    """Rules that depend on the final state of the account."""
    if (account.type is AccountType.POT) != (account.parent_id is not None):
        raise InvalidAccountError("a pot needs a parent account, and only a pot may have one")
    if account.type is not AccountType.CREDIT_CARD and (
        account.statement_day is not None or account.due_day is not None
    ):
        raise InvalidAccountError("statement_day and due_day are only for credit_card accounts")


def create_account(db: DbSession, user_id: int, data: AccountCreate) -> Account:
    """Create an account after checking the rules that need the database."""
    if data.parent_id is not None:
        _validate_parent(db, user_id, data.parent_id)

    account = Account(
        user_id=user_id,
        name=data.name,
        type=data.type,
        purpose=data.purpose,
        capture_mode=data.capture_mode,
        parent_id=data.parent_id,
        opening_balance_paise=data.opening_balance_paise,
        opening_date=data.opening_date,
        statement_day=data.statement_day,
        due_day=data.due_day,
        is_active=data.is_active,
    )
    _validate_state(account)
    db.add(account)
    db.commit()
    return account


def update_account(db: DbSession, user_id: int, account_id: int, data: AccountUpdate) -> Account:
    """Apply the provided fields, then re-check the rules against the result."""
    account = get_account(db, user_id, account_id)
    changes = data.model_dump(exclude_unset=True)

    new_parent_id = changes.get("parent_id")
    if new_parent_id is not None:
        _validate_parent(db, user_id, new_parent_id)

    for field, value in changes.items():
        setattr(account, field, value)

    _validate_state(account)
    db.commit()
    return account


def soft_delete_account(db: DbSession, user_id: int, account_id: int) -> None:
    """Soft-delete an account; financial records are never hard-deleted."""
    account = get_account(db, user_id, account_id)
    account.deleted_at = datetime.now(UTC)
    db.commit()
