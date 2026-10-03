"""Command-line tasks.

Run inside the container, for example:

    docker compose exec backend python -m app.cli create-user

Credentials are read from the environment (ADMIN_EMAIL, ADMIN_PASSWORD) so a
password never lands in shell history or the process list.
"""

import argparse
import sys

from app.config import get_settings
from app.db import SessionLocal
from app.services.auth import EmailAlreadyUsedError, create_user


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


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m app.cli``."""
    parser = argparse.ArgumentParser(prog="app.cli", description="Finance Co-pilot tasks.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("create-user", help="Create the single user.")
    parser.parse_args(argv)

    # Only one command exists so far; dispatch arrives with the second.
    return _create_user()


if __name__ == "__main__":
    raise SystemExit(main())
