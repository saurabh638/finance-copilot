"""Tests for the seed command: what it asks, what it creates, what it refuses."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.cli import main
from app.config import get_settings
from app.models import User
from app.services.accounts import list_accounts
from app.services.auth import create_user

# What a person would type, in the order they are asked: balance, then date.
TYPED_BALANCES = ["1,00,000", "50,000.50", "-12,345.67", "2,500.25", "100", "0"]
TYPED_DATES = ["2026-04-01", "2026-04-01", "2026-04-01", "2026-04-01", "2026-04-01", "2026-05-15"]


@pytest.fixture
def seed_user(db: Session) -> User:
    """The one user the seed command attaches accounts to."""
    return create_user(db, get_settings().admin_email, "s3cret-passphrase")


def _type(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> None:
    """Feed the prompts from a script, ending in EOF like a piped run."""
    remaining = iter(answers)

    def fake_input(prompt: str = "") -> str:
        try:
            return next(remaining)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr("builtins.input", fake_input)


def _script() -> list[str]:
    answers: list[str] = []
    for balance, when in zip(TYPED_BALANCES, TYPED_DATES, strict=True):
        answers.extend([balance, when])
    return answers


def test_seed_creates_six_accounts_from_what_is_typed(
    db: Session,
    seed_user: User,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _type(monkeypatch, _script())

    assert main(["seed"]) == 0

    stored = {account.name: account for account in list_accounts(db, seed_user.id, 50, 0)}
    assert len(stored) == 6
    assert stored["SBI"].opening_balance_paise == 10_000_000
    assert stored["SBI Credit Card"].opening_balance_paise == -1_234_567
    assert stored["Cash"].opening_balance_paise == 0
    assert stored["Cash"].opening_date == date(2026, 5, 15)
    assert "Created SBI." in capsys.readouterr().out


def test_seed_says_it_is_skipping_what_already_exists(
    db: Session,
    seed_user: User,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _type(monkeypatch, _script())
    main(["seed"])
    _type(monkeypatch, _script())

    assert main(["seed"]) == 0

    output = capsys.readouterr().out
    assert "Skipped SBI: it already exists." in output
    assert len(list_accounts(db, seed_user.id, 50, 0)) == 6


def test_seed_creates_nothing_when_the_input_stops_early(
    db: Session,
    seed_user: User,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _type(monkeypatch, _script()[:3])

    assert main(["seed"]) == 1

    assert list_accounts(db, seed_user.id, 50, 0) == []
    assert "Nothing was created" in capsys.readouterr().err


def test_seed_asks_again_after_a_mistyped_amount(
    db: Session,
    seed_user: User,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _type(monkeypatch, ["10.005", *_script()])

    assert main(["seed"]) == 0

    stored = {account.name: account for account in list_accounts(db, seed_user.id, 50, 0)}
    assert stored["SBI"].opening_balance_paise == 10_000_000
    assert "not a valid money amount" in capsys.readouterr().out


def test_seed_tells_you_to_create_the_user_first(
    db: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _type(monkeypatch, _script())

    assert main(["seed"]) == 1

    assert "create-user" in capsys.readouterr().err


def test_the_placeholder_run_creates_marked_accounts_and_removes_them_again(
    db: Session, seed_user: User, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["seed", "--demo"]) == 0

    stored = list_accounts(db, seed_user.id, 50, 0)
    assert len(stored) == 6
    assert all(account.name.endswith(" (demo)") for account in stored)
    assert "Created SBI (demo)." in capsys.readouterr().out

    assert main(["seed", "--remove-demo"]) == 0

    assert list_accounts(db, seed_user.id, 50, 0) == []
    assert "Removed 6 placeholder account(s)" in capsys.readouterr().out


def test_removing_placeholders_when_there_are_none_is_harmless(
    db: Session, seed_user: User, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["seed", "--remove-demo"]) == 0

    assert "No placeholder accounts to remove." in capsys.readouterr().out
