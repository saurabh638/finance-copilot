"""Filing movements under categories: the rules as a client meets them.

A category is optional, and it has to mean the same thing as the movement: a
spending category on money coming in would make the totals lie.
"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, Posting, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.auth import create_user
from app.services.categories import CategoryKind, create_category, seed_defaults

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
OPENED = date(2026, 4, 1)
OPENING_PAISE = 1_00_000_00

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


def _expense(client: TestClient, account_id: int, **extra: object) -> object:
    return client.post(
        TRANSACTIONS,
        json={
            "kind": "expense",
            "account_id": account_id,
            "amount_paise": 50_000,
            "transaction_date": "2026-10-01",
            **extra,
        },
    )


def test_an_expense_can_be_filed_under_a_category(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries = create_category(db, user.id, "Groceries", kind=CategoryKind.EXPENSE).id

    response = _expense(client, account_id, category_id=groceries)

    assert response.status_code == 201
    assert response.json()["postings"][0]["category_id"] == groceries
    posting = db.scalars(select(Posting)).one()
    assert posting.category_id == groceries


def test_a_movement_may_be_left_uncategorised(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = _expense(client, account_id)

    assert response.status_code == 201
    assert response.json()["postings"][0]["category_id"] is None


def test_an_income_can_be_filed_under_an_income_category(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    salary = create_category(db, user.id, "Salary", kind=CategoryKind.INCOME).id

    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "income",
            "account_id": account_id,
            "amount_paise": 9_00_000_00,
            "transaction_date": "2026-10-01",
            "category_id": salary,
        },
    )

    assert response.status_code == 201
    assert response.json()["postings"][0]["category_id"] == salary


def test_a_spending_category_cannot_be_put_on_money_coming_in(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries = create_category(db, user.id, "Groceries", kind=CategoryKind.EXPENSE).id

    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "income",
            "account_id": account_id,
            "amount_paise": 50_000,
            "transaction_date": "2026-10-01",
            "category_id": groceries,
        },
    )

    assert response.status_code == 400
    assert "Groceries is for spending" in response.json()["detail"]


def test_an_earning_category_cannot_be_put_on_spending(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    salary = create_category(db, user.id, "Salary", kind=CategoryKind.INCOME).id

    response = _expense(client, account_id, category_id=salary)

    assert response.status_code == 400
    assert "Salary is for earning" in response.json()["detail"]


def test_a_write_off_category_cannot_be_used_by_hand(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    seed_defaults(db, user.id)
    write_off = create_category(db, user.id, "Left over", kind=CategoryKind.ADJUSTMENT).id

    response = _expense(client, account_id, category_id=write_off)

    assert response.status_code == 400
    assert "Left over is for write-offs" in response.json()["detail"]


def test_a_category_that_is_not_there_answers_404(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    assert _expense(client, account_id, category_id=999).status_code == 404


def test_another_users_category_cannot_be_used(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    other = create_user(db, "someone@example.com", "another-passphrase")
    theirs = create_category(db, other.id, "Theirs", kind=CategoryKind.EXPENSE).id

    assert _expense(client, account_id, category_id=theirs).status_code == 404


def test_a_transfer_never_carries_a_category(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    from_account = _account(db, user)
    to_account = _account(db, user, name="Central Bank")
    groceries = create_category(db, user.id, "Groceries", kind=CategoryKind.EXPENSE).id

    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "transfer",
            "from_account_id": from_account,
            "to_account_id": to_account,
            "amount_paise": 50_000,
            "transaction_date": "2026-10-01",
            "category_id": groceries,
        },
    )

    assert response.status_code == 201
    # A transfer moves money without spending it, so it is filed under nothing.
    assert [posting["category_id"] for posting in response.json()["postings"]] == [None, None]


def test_a_movement_can_be_filed_under_a_category_later(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries = create_category(db, user.id, "Groceries", kind=CategoryKind.EXPENSE).id
    transaction_id = _expense(client, account_id).json()["id"]

    response = client.patch(f"{TRANSACTIONS}/{transaction_id}", json={"category_id": groceries})

    assert response.status_code == 200
    assert response.json()["postings"][0]["category_id"] == groceries


def test_filing_can_be_undone_with_an_explicit_null(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries = create_category(db, user.id, "Groceries", kind=CategoryKind.EXPENSE).id
    transaction_id = _expense(client, account_id, category_id=groceries).json()["id"]

    response = client.patch(f"{TRANSACTIONS}/{transaction_id}", json={"category_id": None})

    assert response.status_code == 200
    assert response.json()["postings"][0]["category_id"] is None


def test_changing_a_filing_to_the_wrong_kind_is_refused(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    salary = create_category(db, user.id, "Salary", kind=CategoryKind.INCOME).id
    transaction_id = _expense(client, account_id).json()["id"]

    response = client.patch(f"{TRANSACTIONS}/{transaction_id}", json={"category_id": salary})

    assert response.status_code == 400
    assert "Salary is for earning" in response.json()["detail"]


def test_a_leaving_a_field_out_leaves_the_filing_alone(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries = create_category(db, user.id, "Groceries", kind=CategoryKind.EXPENSE).id
    transaction_id = _expense(client, account_id, category_id=groceries).json()["id"]

    response = client.patch(f"{TRANSACTIONS}/{transaction_id}", json={"note": "milk"})

    assert response.json()["postings"][0]["category_id"] == groceries


def test_a_transfers_filing_cannot_be_changed(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    from_account = _account(db, user)
    to_account = _account(db, user, name="Central Bank")
    groceries = create_category(db, user.id, "Groceries", kind=CategoryKind.EXPENSE).id
    transaction_id = client.post(
        TRANSACTIONS,
        json={
            "kind": "transfer",
            "from_account_id": from_account,
            "to_account_id": to_account,
            "amount_paise": 50_000,
            "transaction_date": "2026-10-01",
        },
    ).json()["id"]

    response = client.patch(f"{TRANSACTIONS}/{transaction_id}", json={"category_id": groceries})

    assert response.status_code == 400
    assert "one posting" in response.json()["detail"]
