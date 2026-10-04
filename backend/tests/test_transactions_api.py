"""API-level transaction tests: validation, filtering, pagination and editing."""

from datetime import date

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, Posting, Transaction, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account, soft_delete_account
from app.services.auth import create_user
from app.services.transactions import record_expense

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
OPENED = date(2026, 4, 1)
OPENING_PAISE = 1_00_000_00  # ₹1,00,000.00

TRANSACTIONS = "/api/v1/transactions"


def _sign_in(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})
    assert response.status_code == 200


def _account(db: Session, user: User, name: str = "SBI", opening_paise: int = OPENING_PAISE) -> int:
    account = create_account(
        db,
        user.id,
        AccountCreate(
            name=name,
            type=AccountType.SAVINGS,
            capture_mode=CaptureMode.STATEMENT_IMPORT,
            opening_balance_paise=opening_paise,
            opening_date=OPENED,
        ),
    )
    return account.id


def _expense(
    client: TestClient, account_id: int, paise: int, on: str = "2026-10-01", **extra: object
) -> Response:
    return client.post(
        TRANSACTIONS,
        json={
            "kind": "expense",
            "account_id": account_id,
            "amount_paise": paise,
            "transaction_date": on,
            **extra,
        },
    )


def _balance(client: TestClient, account_id: int) -> int:
    body = client.get(f"/api/v1/accounts/{account_id}/balance").json()
    return body["balance_paise"]


def test_every_transaction_route_needs_a_session(client: TestClient) -> None:
    assert client.post(TRANSACTIONS, json={}).status_code == 401
    assert client.get(TRANSACTIONS).status_code == 401
    assert client.get(f"{TRANSACTIONS}/1").status_code == 401
    assert client.patch(f"{TRANSACTIONS}/1", json={}).status_code == 401
    assert client.delete(f"{TRANSACTIONS}/1").status_code == 401


def test_an_expense_is_recorded_and_moves_the_balance(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = _expense(client, account_id, 500_00, merchant="Blinkit")

    assert response.status_code == 201
    body = response.json()
    assert body["transaction_date"] == "2026-10-01"
    assert body["merchant"] == "Blinkit"
    assert body["source"] == "manual"
    assert len(body["postings"]) == 1
    assert body["postings"][0]["amount_paise"] == -500_00
    assert body["postings"][0]["kind"] == "expense"
    assert body["postings"][0]["account_id"] == account_id
    assert _balance(client, account_id) == OPENING_PAISE - 500_00


def test_income_is_recorded_with_the_other_sign(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "income",
            "account_id": account_id,
            "amount_paise": 75_000_00,
            "transaction_date": "2026-10-02",
            "note": "salary",
        },
    )

    assert response.status_code == 201
    assert response.json()["postings"][0]["amount_paise"] == 75_000_00
    assert _balance(client, account_id) == OPENING_PAISE + 75_000_00


def test_a_transfer_writes_two_postings_that_sum_to_zero(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    savings = _account(db, user, name="SBI")
    current = _account(db, user, name="Central Bank", opening_paise=0)

    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "transfer",
            "from_account_id": savings,
            "to_account_id": current,
            "amount_paise": 40_000_00,
            "transaction_date": "2026-10-03",
        },
    )

    assert response.status_code == 201
    postings = response.json()["postings"]
    assert len(postings) == 2
    assert sum(posting["amount_paise"] for posting in postings) == 0
    assert _balance(client, savings) == OPENING_PAISE - 40_000_00
    assert _balance(client, current) == 40_000_00


def test_an_amount_that_is_not_positive_is_refused(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    assert _expense(client, account_id, 0).status_code == 422
    assert _expense(client, account_id, -1).status_code == 422


def test_an_unknown_kind_is_refused(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "moonlight",
            "account_id": account_id,
            "amount_paise": 500_00,
            "transaction_date": "2026-10-01",
        },
    )

    assert response.status_code == 422


def test_a_transfer_needs_both_accounts(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "transfer",
            "from_account_id": account_id,
            "amount_paise": 500_00,
            "transaction_date": "2026-10-01",
        },
    )

    assert response.status_code == 422


def test_a_transfer_to_the_same_account_is_refused(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "transfer",
            "from_account_id": account_id,
            "to_account_id": account_id,
            "amount_paise": 500_00,
            "transaction_date": "2026-10-01",
        },
    )

    assert response.status_code == 400
    assert "two different accounts" in response.json()["detail"]


def test_a_date_before_the_account_opened_is_refused(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = _expense(client, account_id, 500_00, on="2026-03-31")

    assert response.status_code == 400
    assert "2026-04-01" in response.json()["detail"]


def test_an_unknown_account_is_refused(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)

    assert _expense(client, 999, 500_00).status_code == 404


def test_a_soft_deleted_account_is_refused(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    soft_delete_account(db, user.id, account_id)

    assert _expense(client, account_id, 500_00).status_code == 404


def test_the_list_is_newest_first(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _expense(client, account_id, 100_00, on="2026-10-01")
    _expense(client, account_id, 200_00, on="2026-10-03")
    _expense(client, account_id, 300_00, on="2026-10-02")

    body = client.get(TRANSACTIONS).json()

    assert [item["transaction_date"] for item in body] == [
        "2026-10-03",
        "2026-10-02",
        "2026-10-01",
    ]
    assert [item["postings"][0]["amount_paise"] for item in body] == [-200_00, -300_00, -100_00]


def test_the_list_can_be_filtered_by_account(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    savings = _account(db, user, name="SBI")
    current = _account(db, user, name="Central Bank")
    _expense(client, savings, 100_00)
    _expense(client, current, 200_00)

    body = client.get(TRANSACTIONS, params={"account_id": current}).json()

    assert len(body) == 1
    assert body[0]["postings"][0]["account_id"] == current


def test_the_list_can_be_filtered_by_date_range(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _expense(client, account_id, 100_00, on="2026-10-01")
    _expense(client, account_id, 200_00, on="2026-10-15")
    _expense(client, account_id, 300_00, on="2026-10-31")

    from_to = client.get(TRANSACTIONS, params={"from": "2026-10-15", "to": "2026-10-15"}).json()
    only_from = client.get(TRANSACTIONS, params={"from": "2026-10-15"}).json()
    only_to = client.get(TRANSACTIONS, params={"to": "2026-10-01"}).json()

    assert len(from_to) == 1  # both ends inclusive
    assert len(only_from) == 2
    assert len(only_to) == 1


def test_the_list_can_be_filtered_by_kind(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    savings = _account(db, user, name="SBI")
    current = _account(db, user, name="Central Bank")
    _expense(client, savings, 100_00)
    _expense(client, current, 200_00)
    client.post(
        TRANSACTIONS,
        json={
            "kind": "transfer",
            "from_account_id": savings,
            "to_account_id": current,
            "amount_paise": 500_00,
            "transaction_date": "2026-10-04",
        },
    )

    expenses = client.get(TRANSACTIONS, params={"kind": "expense"}).json()
    transfers = client.get(TRANSACTIONS, params={"kind": "transfer"}).json()

    assert len(expenses) == 2
    assert len(transfers) == 1
    assert len(transfers[0]["postings"]) == 2


def test_the_list_is_paginated(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    for day in range(1, 6):
        _expense(client, account_id, day * 100_00, on=f"2026-10-0{day}")

    first = client.get(TRANSACTIONS, params={"limit": 2, "offset": 0}).json()
    second = client.get(TRANSACTIONS, params={"limit": 2, "offset": 2}).json()
    beyond = client.get(TRANSACTIONS, params={"limit": 2, "offset": 10}).json()

    assert [item["transaction_date"] for item in first] == ["2026-10-05", "2026-10-04"]
    assert [item["transaction_date"] for item in second] == ["2026-10-03", "2026-10-02"]
    assert beyond == []


def test_a_limit_beyond_the_cap_is_refused(client: TestClient, user: User) -> None:
    _sign_in(client)

    assert client.get(TRANSACTIONS, params={"limit": 500}).status_code == 422


def test_a_transaction_can_be_read_back(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    created = _expense(client, account_id, 500_00, merchant="Blinkit").json()

    response = client.get(f"{TRANSACTIONS}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_an_unknown_transaction_is_not_found(client: TestClient, user: User) -> None:
    _sign_in(client)

    assert client.get(f"{TRANSACTIONS}/999").status_code == 404
    assert client.patch(f"{TRANSACTIONS}/999", json={"note": "x"}).status_code == 404
    assert client.delete(f"{TRANSACTIONS}/999").status_code == 404


def test_the_date_merchant_and_note_can_be_edited(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    created = _expense(client, account_id, 500_00).json()

    response = client.patch(
        f"{TRANSACTIONS}/{created['id']}",
        json={"transaction_date": "2026-10-05", "merchant": "BigBasket", "note": "weekly shop"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["transaction_date"] == "2026-10-05"
    assert body["merchant"] == "BigBasket"
    assert body["note"] == "weekly shop"
    assert body["postings"][0]["amount_paise"] == -500_00


def test_the_amount_can_be_edited_when_there_is_one_posting(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    created = _expense(client, account_id, 500_00).json()

    response = client.patch(f"{TRANSACTIONS}/{created['id']}", json={"amount_paise": 750_00})

    assert response.status_code == 200
    assert response.json()["postings"][0]["amount_paise"] == -750_00
    assert _balance(client, account_id) == OPENING_PAISE - 750_00


def test_the_amount_of_a_transfer_cannot_be_edited(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    savings = _account(db, user, name="SBI")
    current = _account(db, user, name="Central Bank")
    created = client.post(
        TRANSACTIONS,
        json={
            "kind": "transfer",
            "from_account_id": savings,
            "to_account_id": current,
            "amount_paise": 500_00,
            "transaction_date": "2026-10-01",
        },
    ).json()

    response = client.patch(f"{TRANSACTIONS}/{created['id']}", json={"amount_paise": 750_00})

    assert response.status_code == 400
    assert "delete it and record it again" in response.json()["detail"]


def test_editing_the_date_before_the_account_opened_is_refused(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    created = _expense(client, account_id, 500_00).json()

    response = client.patch(
        f"{TRANSACTIONS}/{created['id']}", json={"transaction_date": "2026-03-31"}
    )

    assert response.status_code == 400


def test_a_soft_deleted_transaction_disappears_and_puts_the_balance_back(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    created = _expense(client, account_id, 500_00).json()

    assert client.delete(f"{TRANSACTIONS}/{created['id']}").status_code == 204

    assert client.get(f"{TRANSACTIONS}/{created['id']}").status_code == 404
    assert client.get(TRANSACTIONS).json() == []
    assert _balance(client, account_id) == OPENING_PAISE
    kept = db.get(Transaction, created["id"])
    assert kept is not None
    assert kept.deleted_at is not None
    assert all(posting.deleted_at is not None for posting in db.scalars(select(Posting)))


def test_another_users_transaction_is_not_found(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    other = create_user(db, "other@example.com", PASSPHRASE)
    theirs_account = _account(db, other)
    theirs = record_expense(db, other.id, theirs_account, 500_00, date(2026, 10, 1))

    assert client.get(f"{TRANSACTIONS}/{theirs.id}").status_code == 404
    assert client.patch(f"{TRANSACTIONS}/{theirs.id}", json={"note": "x"}).status_code == 404
    assert client.delete(f"{TRANSACTIONS}/{theirs.id}").status_code == 404
    # Their account is not the owner's either, so recording against it fails too.
    assert _expense(client, theirs_account, 500_00).status_code == 404


def test_every_amount_is_whole_paise(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    body = _expense(client, account_id, 12_34_567_89).json()

    assert body["postings"][0]["amount_paise"] == -12_34_567_89
    assert isinstance(body["postings"][0]["amount_paise"], int)
    assert _balance(client, account_id) == OPENING_PAISE - 12_34_567_89
