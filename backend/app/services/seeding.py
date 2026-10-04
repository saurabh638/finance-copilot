"""The accounts this product expects, described once, and how to create them.

MILESTONES.md M5 fixes the six names, types and capture modes. The only things
the user supplies are each account's opening balance and the date that balance
was true. Nothing here invents a real number: a missing balance is asked for, and
the placeholder path says so in the name it creates.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session as DbSession

from app.core.money import parse_paise
from app.models import Account, AccountType, CaptureMode
from app.schemas.account import AccountCreate
from app.services.accounts import create_account

# Marks the accounts the placeholder run creates, so they can be removed again
# with no chance of touching a real account.
DEMO_SUFFIX = " (demo)"
DEMO_PURPOSE = "Placeholder data. Safe to delete."

# Deliberately fixed, not "today": the placeholder run must give the same result
# on every machine and every day, so it can be tested and reasoned about.
DEMO_BALANCE_PAISE = 12_345_00
DEMO_OPENING_DATE = date(2026, 4, 1)


@dataclass(frozen=True)
class SeedAccount:
    """One account the product expects, before any numbers are known."""

    name: str
    type: AccountType
    capture_mode: CaptureMode


@dataclass(frozen=True)
class SeedEntry:
    """One account with the two numbers only the user can supply."""

    account: SeedAccount
    opening_balance_paise: int
    opening_date: date


@dataclass(frozen=True)
class SeedResult:
    """What a seed run did, so the caller can report it honestly."""

    created: list[str]
    skipped: list[str]


# The order here is the order the user is asked, and the order they appear in.
SEED_ACCOUNTS: tuple[SeedAccount, ...] = (
    SeedAccount("SBI", AccountType.SAVINGS, CaptureMode.STATEMENT_IMPORT),
    SeedAccount("Central Bank", AccountType.SAVINGS, CaptureMode.STATEMENT_IMPORT),
    SeedAccount("SBI Credit Card", AccountType.CREDIT_CARD, CaptureMode.STATEMENT_IMPORT),
    SeedAccount("slice", AccountType.SAVINGS, CaptureMode.STATEMENT_IMPORT),
    SeedAccount("Indian Bank", AccountType.SAVINGS, CaptureMode.MANUAL_ONLY),
    SeedAccount("Cash", AccountType.CASH, CaptureMode.MANUAL_ONLY),
)


def demo_entries() -> list[SeedEntry]:
    """The six accounts with obvious placeholders instead of real numbers."""
    return [SeedEntry(account, DEMO_BALANCE_PAISE, DEMO_OPENING_DATE) for account in SEED_ACCOUNTS]


def name_for(account: SeedAccount, *, demo: bool) -> str:
    """The name to create, which carries the marker on a placeholder run."""
    return f"{account.name}{DEMO_SUFFIX}" if demo else account.name


def parse_balance(text: str) -> int:
    """Read a typed balance as whole paise, using the one money parser."""
    return parse_paise(text)


def parse_opening_date(text: str) -> date:
    """Read a typed date, with a message that says what a good one looks like."""
    try:
        return date.fromisoformat(text.strip())
    except ValueError as error:
        raise ValueError(f"Give a date like 2026-04-01, not {text!r}") from error


def apply(
    db: DbSession,
    user_id: int,
    entries: Sequence[SeedEntry],
    *,
    demo: bool = False,
) -> SeedResult:
    """Create the accounts that are missing, and leave every other one alone.

    Running this twice creates nothing the second time. An account that already
    exists by name is skipped rather than updated, because an opening balance
    that has since been corrected must never be overwritten.
    """
    existing = _live_account_names(db, user_id)
    created: list[str] = []
    skipped: list[str] = []

    for entry in entries:
        name = name_for(entry.account, demo=demo)
        if name in existing:
            skipped.append(name)
            continue

        create_account(
            db,
            user_id,
            AccountCreate(
                name=name,
                type=entry.account.type,
                capture_mode=entry.account.capture_mode,
                purpose=DEMO_PURPOSE if demo else None,
                opening_balance_paise=entry.opening_balance_paise,
                opening_date=entry.opening_date,
                is_active=True,
            ),
        )
        created.append(name)

    return SeedResult(created=created, skipped=skipped)


def remove_demo(db: DbSession, user_id: int) -> list[str]:
    """Soft-delete the placeholder accounts, and nothing else.

    Only names carrying the marker are matched, so a real account can never be
    caught by this, however many times it is run.
    """
    statement = _live_accounts(user_id).where(Account.name.endswith(DEMO_SUFFIX))
    removed: list[str] = []

    for account in db.scalars(statement):
        account.deleted_at = datetime.now(UTC)
        removed.append(account.name)

    db.commit()
    return removed


def _live_accounts(user_id: int) -> Select[Account]:
    """The user's live accounts. Soft-deleted rows are never touched."""
    return select(Account).where(Account.user_id == user_id, Account.deleted_at.is_(None))


def _live_account_names(db: DbSession, user_id: int) -> set[str]:
    return set(
        db.scalars(
            select(Account.name).where(
                Account.user_id == user_id,
                Account.deleted_at.is_(None),
            )
        )
    )
