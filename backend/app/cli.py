"""Command-line tasks.

Run inside the container, for example:

    docker compose exec backend python -m app.cli create-user
    docker compose exec backend python -m app.cli seed
    docker compose exec backend python -m app.cli seed --demo
    docker compose exec backend python -m app.cli seed --remove-demo

Credentials are read from the environment (ADMIN_EMAIL, ADMIN_PASSWORD) so a
password never lands in shell history or the process list.
"""

import argparse
import sys
from datetime import date

from app.config import get_settings
from app.core.money import InvalidMoneyError
from app.db import SessionLocal
from app.services.auth import EmailAlreadyUsedError, create_user, find_user
from app.services.seeding import (
    SEED_ACCOUNTS,
    SeedEntry,
    SeedResult,
    apply,
    demo_entries,
    parse_balance,
    parse_opening_date,
    remove_demo,
)


def _create_user() -> int:
    """Create the single user from ADMIN_EMAIL / ADMIN_PASSWORD."""
    settings = get_settings()
    email = settings.admin_email
    password = settings.admin_password
    if not email or not password:
        print("Set ADMIN_EMAIL and ADMIN_PASSWORD in the environment first.", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        try:
            user = create_user(db, email, password)
        except EmailAlreadyUsedError:
            print(f"A user with email {email} already exists.", file=sys.stderr)
            return 1
        print(f"Created user {user.email} (id {user.id}).")

    return 0


def _seed(*, demo: bool, remove_placeholders: bool) -> int:
    """Create the six accounts for the one user, or remove the placeholders."""
    settings = get_settings()
    with SessionLocal() as db:
        user = find_user(db, settings.admin_email) if settings.admin_email else None
        if user is None:
            print(
                "No user yet. Run: docker compose exec backend python -m app.cli create-user",
                file=sys.stderr,
            )
            return 1

        if remove_placeholders:
            removed = remove_demo(db, user.id)
            if removed:
                print(f"Removed {len(removed)} placeholder account(s): {', '.join(removed)}")
            else:
                print("No placeholder accounts to remove.")
            return 0

        entries = demo_entries() if demo else _ask_for_entries()
        _report(apply(db, user.id, entries, demo=demo))

    return 0


def _ask_for_entries() -> list[SeedEntry]:
    """Ask for the two numbers only the user can know, once per account."""
    print("For each account, give the balance that was true on the start date.")
    print("Amounts are rupees, for example 1,23,456.78. A card's outstanding can be negative.\n")

    entries: list[SeedEntry] = []
    for account in SEED_ACCOUNTS:
        print(f"{account.name} ({account.type}, {account.capture_mode})")
        balance = _ask_balance(account.name)
        opening_date = _ask_date(account.name)
        entries.append(SeedEntry(account, balance, opening_date))
    return entries


def _ask_balance(account_name: str) -> int:
    """Ask until the money parser accepts what was typed."""
    while True:
        text = input(f"  Opening balance for {account_name}: ")
        try:
            return parse_balance(text)
        except InvalidMoneyError as error:
            print(f"  {error}. Try again, for example 1,23,456.78")


def _ask_date(account_name: str) -> date:
    """Ask until the text is a real date."""
    while True:
        text = input(f"  Start date for {account_name} (YYYY-MM-DD): ")
        try:
            return parse_opening_date(text)
        except ValueError as error:
            print(f"  {error}")


def _report(result: SeedResult) -> None:
    """Say what happened, including what was left alone."""
    for name in result.created:
        print(f"Created {name}.")
    for name in result.skipped:
        print(f"Skipped {name}: it already exists.")
    if not result.created:
        print("Nothing to create.")


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m app.cli``."""
    parser = argparse.ArgumentParser(prog="app.cli", description="Finance Co-pilot tasks.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("create-user", help="Create the single user.")

    seed = subcommands.add_parser("seed", help="Create the six real accounts.")
    seed.add_argument(
        "--demo",
        action="store_true",
        help="Use placeholder values, named '(demo)' so they can be removed.",
    )
    seed.add_argument(
        "--remove-demo",
        dest="remove_placeholders",
        action="store_true",
        help="Remove the placeholder accounts, and nothing else.",
    )

    args = parser.parse_args(argv)

    if args.command == "create-user":
        return _create_user()

    try:
        return _seed(demo=args.demo, remove_placeholders=args.remove_placeholders)
    except EOFError:
        print("\nInput ended before every account was given. Nothing was created.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
