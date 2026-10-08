"""API-level balance tests: what the balance endpoint says, and to whom."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account, soft_delete_account
from app.services.auth import create_user
from app.services.transactions import (
    record_expense,
    record_income,
    record_interest,
    soft_delete_transaction,
)

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
OPENED = date(2026, 4, 1)
OPENING_PAISE = 1_00_000_00  # ₹1,00,000.00


def _sign_in(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})
    assert response.status_code == 200


def _account(db: Session, user: User, *, opening_paise: int = OPENING_PAISE) -> int:
    account = create_account(
        db,
        user.id,
        AccountCreate(
            name="SBI",
            type=AccountType.SAVINGS,
            capture_mode=CaptureMode.STATEMENT_IMPORT,
            opening_balance_paise=opening_paise,
            opening_date=OPENED,
        ),
    )
    return account.id


def _balance_path(account_id: int) -> str:
    return f"/api/v1/accounts/{account_id}/balance"


def test_the_balance_needs_a_session(client: TestClient) -> None:
    assert client.get(_balance_path(1)).status_code == 401


def test_an_account_with_no_postings_holds_its_opening_balance(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = client.get(_balance_path(account_id))

    assert response.status_code == 200
    assert response.json() == {
        "account_id": account_id,
        "as_of": None,
        "opening_balance_paise": OPENING_PAISE,
        "postings_paise": 0,
        "interest_paise": 0,
        "balance_paise": OPENING_PAISE,
    }


def test_the_balance_follows_an_expense_and_an_income(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    record_expense(db, user.id, account_id, 500_00, date(2026, 4, 15))
    record_income(db, user.id, account_id, 200_00, date(2026, 4, 16))

    body = client.get(_balance_path(account_id)).json()

    assert body["opening_balance_paise"] == OPENING_PAISE
    assert body["postings_paise"] == -300_00
    assert body["balance_paise"] == OPENING_PAISE - 300_00


def test_the_balance_can_be_asked_for_as_of_a_date(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    record_expense(db, user.id, account_id, 500_00, date(2026, 4, 15))
    record_expense(db, user.id, account_id, 250_00, date(2026, 5, 15))

    body = client.get(_balance_path(account_id), params={"as_of": "2026-04-30"}).json()

    assert body["as_of"] == "2026-04-30"
    assert body["postings_paise"] == -500_00
    assert body["balance_paise"] == OPENING_PAISE - 500_00


def test_a_date_that_is_not_a_date_is_refused(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = client.get(_balance_path(account_id), params={"as_of": "30-04-2026"})

    assert response.status_code == 422


def test_the_balance_says_how_much_of_it_is_interest(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    record_expense(db, user.id, account_id, 500_00, date(2026, 4, 15))
    record_interest(db, user.id, account_id, 581_50, date(2026, 4, 30))

    body = client.get(_balance_path(account_id)).json()

    # Interest is part of the movements, not a third part of the balance: the
    # opening balance plus the movements still has to come to the balance.
    assert body["postings_paise"] == -500_00 + 581_50
    assert body["interest_paise"] == 581_50
    assert body["balance_paise"] == OPENING_PAISE + body["postings_paise"]


def test_interest_that_was_removed_is_no_longer_counted(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    credited = record_interest(db, user.id, account_id, 581_50, date(2026, 4, 30))
    soft_delete_transaction(db, user.id, credited.id)

    body = client.get(_balance_path(account_id)).json()

    assert body["interest_paise"] == 0
    assert body["postings_paise"] == 0


def test_an_unknown_account_is_not_found(client: TestClient, user: User) -> None:
    _sign_in(client)

    assert client.get(_balance_path(999)).status_code == 404


def test_a_soft_deleted_account_is_not_found(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    soft_delete_account(db, user.id, account_id)

    assert client.get(_balance_path(account_id)).status_code == 404


def test_another_users_account_is_not_found(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    other = create_user(db, "other@example.com", PASSPHRASE)
    theirs = _account(db, other)

    assert client.get(_balance_path(theirs)).status_code == 404


def test_a_savings_account_reads_as_money_held(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    record_expense(db, user.id, account_id, 1_23_456_78, date(2026, 4, 15))

    body = client.get(_balance_path(account_id)).json()

    assert body["balance_paise"] == OPENING_PAISE - 1_23_456_78
    assert isinstance(body["balance_paise"], int)
