"""One amount, several categories: a ₹500 shop of ₹300 groceries and ₹200 soap.

The user states one figure, because that is what the statement says, and files it
under as many categories as it really was. The parts must be exactly that figure:
the ledger counts the money once, and the balance must move by the total.
"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, Posting, PostingKind, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.auth import create_user
from app.services.categories import CategoryKind, create_category

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
OPENED = date(2026, 4, 1)
OPENING_PAISE = 1_00_000_00

TRANSACTIONS = "/api/v1/transactions"


def _sign_in(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})
    assert response.status_code == 200


def _account(db: Session, user: User, name: str = "SBI") -> int:
    account = create_account(
        db,
        user.id,
        AccountCreate(
            name=name,
            type=AccountType.SAVINGS,
            capture_mode=CaptureMode.STATEMENT_IMPORT,
            opening_balance_paise=OPENING_PAISE,
            opening_date=OPENED,
        ),
    )
    return account.id


def _split_expense(client: TestClient, account_id: int, **extra: object) -> object:
    return client.post(
        TRANSACTIONS,
        json={
            "kind": "expense",
            "account_id": account_id,
            "amount_paise": 500_00,
            "transaction_date": "2026-10-01",
            **extra,
        },
    )


def _two_categories(db: Session, user: User) -> tuple[int, int]:
    return (
        create_category(db, user.id, "Groceries", kind=CategoryKind.EXPENSE).id,
        create_category(db, user.id, "Household", kind=CategoryKind.EXPENSE).id,
    )


def test_a_split_expense_files_each_part_and_moves_the_total(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries, household = _two_categories(db, user)

    response = _split_expense(
        client,
        account_id,
        parts=[
            {"amount_paise": 300_00, "category_id": groceries},
            {"amount_paise": 200_00, "category_id": household},
        ],
    )

    assert response.status_code == 201
    body = response.json()
    assert [(p["amount_paise"], p["category_id"]) for p in body["postings"]] == [
        (-300_00, groceries),
        (-200_00, household),
    ]
    assert all(posting["kind"] == PostingKind.EXPENSE.value for posting in body["postings"])


def test_a_split_leaves_the_balance_exactly_where_the_total_says(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries, household = _two_categories(db, user)

    _split_expense(
        client,
        account_id,
        parts=[
            {"amount_paise": 300_00, "category_id": groceries},
            {"amount_paise": 200_00, "category_id": household},
        ],
    )

    balance = client.get(f"/api/v1/accounts/{account_id}/balance").json()
    assert balance["balance_paise"] == OPENING_PAISE - 500_00
    assert len(db.scalars(select(Posting)).all()) == 2


def test_a_split_income_files_each_part_as_money_arriving(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    salary = create_category(db, user.id, "Salary", kind=CategoryKind.INCOME).id
    interest = create_category(db, user.id, "Interest", kind=CategoryKind.INCOME).id

    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "income",
            "account_id": account_id,
            "amount_paise": 500_00,
            "transaction_date": "2026-10-01",
            "parts": [
                {"amount_paise": 400_00, "category_id": salary},
                {"amount_paise": 100_00, "category_id": interest},
            ],
        },
    )

    assert response.status_code == 201
    assert [posting["amount_paise"] for posting in response.json()["postings"]] == [
        400_00,
        100_00,
    ]


def test_parts_that_do_not_add_up_to_the_total_are_refused(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries, household = _two_categories(db, user)

    response = _split_expense(
        client,
        account_id,
        parts=[
            {"amount_paise": 300_00, "category_id": groceries},
            {"amount_paise": 199_99, "category_id": household},
        ],
    )

    assert response.status_code == 400
    assert "add up to" in response.json()["detail"]


def test_one_part_is_not_a_split(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries, _ = _two_categories(db, user)

    response = _split_expense(
        client, account_id, parts=[{"amount_paise": 500_00, "category_id": groceries}]
    )

    assert response.status_code == 400
    assert "two parts" in response.json()["detail"]


def test_a_part_cannot_be_filed_under_the_wrong_kind_of_category(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries, _ = _two_categories(db, user)
    salary = create_category(db, user.id, "Salary", kind=CategoryKind.INCOME).id

    response = _split_expense(
        client,
        account_id,
        parts=[
            {"amount_paise": 300_00, "category_id": groceries},
            {"amount_paise": 200_00, "category_id": salary},
        ],
    )

    assert response.status_code == 400
    assert "Salary is for earning" in response.json()["detail"]


def test_a_part_with_a_category_that_is_not_there_answers_404(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries, _ = _two_categories(db, user)

    response = _split_expense(
        client,
        account_id,
        parts=[
            {"amount_paise": 300_00, "category_id": groceries},
            {"amount_paise": 200_00, "category_id": 999},
        ],
    )

    assert response.status_code == 404


def test_a_split_and_a_single_category_together_are_refused(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries, household = _two_categories(db, user)

    response = _split_expense(
        client,
        account_id,
        category_id=groceries,
        parts=[
            {"amount_paise": 300_00, "category_id": groceries},
            {"amount_paise": 200_00, "category_id": household},
        ],
    )

    assert response.status_code == 400
    assert "not both" in response.json()["detail"]


def test_a_part_of_nothing_is_refused_before_anything_runs(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries, household = _two_categories(db, user)

    response = _split_expense(
        client,
        account_id,
        parts=[
            {"amount_paise": 500_00, "category_id": groceries},
            {"amount_paise": 0, "category_id": household},
        ],
    )

    assert response.status_code == 422


def test_a_transfer_still_refuses_to_be_split(client: TestClient, db: Session, user: User) -> None:
    """A transfer is two sides of one move; there is nothing to file it under."""
    _sign_in(client)
    from_account = _account(db, user)
    to_account = _account(db, user, name="Central Bank")
    groceries, _ = _two_categories(db, user)

    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "transfer",
            "from_account_id": from_account,
            "to_account_id": to_account,
            "amount_paise": 500_00,
            "transaction_date": "2026-10-01",
            "parts": [{"amount_paise": 300_00, "category_id": groceries}],
        },
    )

    # Unknown fields are ignored, as they are everywhere else in this API, so a
    # transfer with parts is simply a transfer.
    assert response.status_code == 201
    assert [posting["category_id"] for posting in response.json()["postings"]] == [None, None]


def test_an_unknown_category_elsewhere_cannot_be_reached_through_a_split(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries, _ = _two_categories(db, user)
    other = create_user(db, "someone@example.com", "another-passphrase")
    theirs = create_category(db, other.id, "Theirs", kind=CategoryKind.EXPENSE).id

    response = _split_expense(
        client,
        account_id,
        parts=[
            {"amount_paise": 300_00, "category_id": groceries},
            {"amount_paise": 200_00, "category_id": theirs},
        ],
    )

    assert response.status_code == 404
