"""Tests for the alias a user may give an account, and the words it makes theirs.

An alias exists so that `hdfc` can mean the credit card in a typed line. The rules
are therefore about words meaning one thing rather than two, which is what makes
them worth pinning down here rather than leaving to the screen.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, User
from app.schemas.account import AccountCreate, AccountUpdate
from app.services.accounts import (
    InvalidAccountError,
    _clean_alias,
    create_account,
    soft_delete_account,
    update_account,
)
from app.services.auth import create_user

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
OPENED = date(2026, 4, 1)

ACCOUNTS = "/api/v1/accounts"


def _sign_in(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})
    assert response.status_code == 200


def _make(db: Session, user: User, name: str, **overrides: object) -> object:
    payload: dict[str, object] = {
        "name": name,
        "type": AccountType.SAVINGS,
        "capture_mode": CaptureMode.STATEMENT_IMPORT,
        "opening_balance_paise": 0,
        "opening_date": OPENED,
        **overrides,
    }
    return create_account(db, user.id, AccountCreate.model_validate(payload))


def test_an_account_can_be_created_without_an_alias(db: Session, user: User) -> None:
    account = _make(db, user, "SBI")

    assert account.alias is None  # type: ignore[attr-defined]


def test_an_alias_is_stored_as_it_was_typed(db: Session, user: User) -> None:
    account = _make(db, user, "SBI Credit Card", alias="HDFC")

    assert account.alias == "HDFC"  # type: ignore[attr-defined]


def test_an_alias_is_trimmed(db: Session, user: User) -> None:
    account = _make(db, user, "SBI Credit Card", alias="  hdfc  ")

    assert account.alias == "hdfc"  # type: ignore[attr-defined]


def test_a_blank_alias_is_no_alias(db: Session, user: User) -> None:
    account = _make(db, user, "SBI", alias="   ")

    assert account.alias is None  # type: ignore[attr-defined]


def test_two_accounts_cannot_share_an_alias(db: Session, user: User) -> None:
    _make(db, user, "SBI Credit Card", alias="hdfc")

    with pytest.raises(InvalidAccountError):
        _make(db, user, "SBI Debit Card", alias="hdfc")


def test_an_alias_cannot_clash_with_another_accounts_name(db: Session, user: User) -> None:
    # A word that means two accounts would make every typed line a question.
    _make(db, user, "slice")

    with pytest.raises(InvalidAccountError):
        _make(db, user, "SBI", alias="slice")


def test_an_alias_may_match_a_name_after_it_is_taken_away(db: Session, user: User) -> None:
    gone = _make(db, user, "slice")
    soft_delete_account(db, user.id, gone.id)  # type: ignore[attr-defined]

    account = _make(db, user, "SBI", alias="slice")

    assert account.alias == "slice"  # type: ignore[attr-defined]


def test_an_account_may_keep_its_own_alias_while_changing_something_else(
    db: Session, user: User
) -> None:
    account = _make(db, user, "SBI", alias="hdfc")

    changed = update_account(
        db,
        user.id,
        account.id,
        AccountUpdate(purpose="salary account"),  # type: ignore[attr-defined]
    )

    assert changed.alias == "hdfc"


def test_an_alias_can_be_changed_and_taken_away(db: Session, user: User) -> None:
    account = _make(db, user, "SBI", alias="hdfc")

    changed = update_account(
        db,
        user.id,
        account.id,
        AccountUpdate(alias="bank"),  # type: ignore[attr-defined]
    )
    assert changed.alias == "bank"

    cleared = update_account(
        db,
        user.id,
        account.id,
        AccountUpdate(alias=None),  # type: ignore[attr-defined]
    )
    assert cleared.alias is None


def test_an_alias_longer_than_the_column_is_refused_by_the_schema(db: Session, user: User) -> None:
    # The schema is the front door: a 41-character alias never reaches the service.
    with pytest.raises(ValidationError):
        _make(db, user, "SBI", alias="x" * 41)


def test_the_service_refuses_an_overlong_alias_too(db: Session, user: User) -> None:
    # A belt for callers that build the account without going through the schema.
    with pytest.raises(InvalidAccountError):
        _clean_alias("x" * 41)


def test_another_users_alias_is_not_a_clash(db: Session, user: User) -> None:
    other = create_user(db, "someone@example.com", "another-passphrase")
    _make(db, other, "SBI Credit Card", alias="hdfc")

    mine = _make(db, user, "SBI Credit Card", alias="hdfc")

    assert mine.alias == "hdfc"  # type: ignore[attr-defined]


def test_the_api_carries_the_alias_both_ways(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)

    made = client.post(
        ACCOUNTS,
        json={
            "name": "SBI Credit Card",
            "type": "credit_card",
            "capture_mode": "statement_import",
            "opening_balance_paise": 0,
            "opening_date": OPENED.isoformat(),
            "alias": "hdfc",
            "statement_day": 5,
        },
    )

    assert made.status_code == 201, made.text
    assert made.json()["alias"] == "hdfc"

    listed = client.get(ACCOUNTS).json()
    assert [row["alias"] for row in listed] == ["hdfc"]


def test_the_api_refuses_a_clashing_alias(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    _make(db, user, "SBI")

    refused = client.post(
        ACCOUNTS,
        json={
            "name": "SBI Credit Card",
            "type": "credit_card",
            "capture_mode": "statement_import",
            "opening_balance_paise": 0,
            "opening_date": OPENED.isoformat(),
            "alias": "sbi",
            "statement_day": 5,
        },
    )

    assert refused.status_code == 400
    assert "sbi" in refused.json()["detail"]
