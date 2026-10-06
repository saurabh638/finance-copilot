"""What was spent under each category, with the children rolled into the groups.

The report answers one question the user asks every month: where did the money
go? It counts expenditure only, and a group's figure includes everything filed
under it, so the branches and the leaves agree at the top.
"""

from datetime import date
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.auth import create_user
from app.services.categories import CategoryKind, create_category, seed_defaults

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
OPENED = date(2026, 4, 1)
OPENING_PAISE = 1_00_000_00

SPEND = "/api/v1/categories/spend"
TRANSACTIONS = "/api/v1/transactions"


def _sign_in(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})
    assert response.status_code == 200


def _account(db: Session, user: User) -> int:
    account = create_account(
        db,
        user.id,
        AccountCreate(
            name="SBI",
            type=AccountType.SAVINGS,
            capture_mode=CaptureMode.STATEMENT_IMPORT,
            opening_balance_paise=OPENING_PAISE,
            opening_date=OPENED,
        ),
    )
    return account.id


def _expense(client: TestClient, account_id: int, paise: int, on: str, **extra: object) -> None:
    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "expense",
            "account_id": account_id,
            "amount_paise": paise,
            "transaction_date": on,
            **extra,
        },
    )
    assert response.status_code == 201


def _tree(db: Session, user: User) -> tuple[int, int, int]:
    """A group, one child of it, and a second group of its own."""
    group = create_category(db, user.id, "Food", kind=CategoryKind.EXPENSE).id
    child = create_category(db, user.id, "Groceries", kind=CategoryKind.EXPENSE, parent_id=group).id
    other = create_category(db, user.id, "Travel", kind=CategoryKind.EXPENSE).id
    return group, child, other


def _report(client: TestClient, query: str = "") -> dict[str, Any]:
    response = client.get(f"{SPEND}{query}")
    assert response.status_code == 200
    return response.json()


def _rows(client: TestClient, query: str = "") -> dict[str, dict[str, Any]]:
    return {row["name"]: row for row in _report(client, query)["rows"]}


def test_spending_needs_a_session(client: TestClient) -> None:
    assert client.get(SPEND).status_code == 401


def test_an_empty_tree_reports_nothing_rather_than_failing(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)

    assert _report(client) == {"rows": [], "uncategorised_paise": 0, "total_paise": 0}


def test_uncategorised_spending_is_reported_apart_from_the_tree(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _tree(db, user)
    _expense(client, account_id, 30_000, "2026-10-04")

    report = _report(client)

    assert report["uncategorised_paise"] == 30_000
    assert _rows(client)["Groceries"]["direct_paise"] == 0


def test_the_total_is_the_rows_plus_what_is_in_no_row(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _, child, other = _tree(db, user)
    _expense(client, account_id, 30_000, "2026-10-04", category_id=child)
    _expense(client, account_id, 20_000, "2026-10-05", category_id=other)
    _expense(client, account_id, 10_000, "2026-10-06")

    report = _report(client)
    filed = sum(row["direct_paise"] for row in report["rows"])

    assert filed == 50_000
    assert report["uncategorised_paise"] == 10_000
    assert report["total_paise"] == 60_000


def test_the_period_narrows_the_uncategorised_figure_too(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _tree(db, user)
    _expense(client, account_id, 10_000, "2026-09-30")
    _expense(client, account_id, 20_000, "2026-10-05")

    report = _report(client, "?from=2026-10-01&to=2026-10-31")

    assert report["uncategorised_paise"] == 20_000
    assert report["total_paise"] == 20_000


def test_an_uncategorised_income_is_not_spending_either(
    client: TestClient, db: Session, user: User
) -> None:
    """Money arriving with no category is still money arriving."""
    _sign_in(client)
    account_id = _account(db, user)
    _tree(db, user)
    unfiled = client.post(
        TRANSACTIONS,
        json={
            "kind": "income",
            "account_id": account_id,
            "amount_paise": 9_00_000_00,
            "transaction_date": "2026-10-05",
        },
    )
    assert unfiled.status_code == 201

    report = _report(client)

    assert report["uncategorised_paise"] == 0
    assert report["total_paise"] == 0


def test_every_expense_category_is_a_row_even_with_nothing_spent(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    seed_defaults(db, user.id)

    rows = _rows(client)

    assert rows["Groceries"]["direct_paise"] == 0
    assert rows["Groceries"]["total_paise"] == 0
    assert rows["Groceries"]["parent_id"] == rows["Food & groceries"]["id"]


def test_spending_under_a_child_is_counted_in_the_child_and_the_group(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    group, child, _ = _tree(db, user)
    _expense(client, account_id, 30_000, "2026-10-04", category_id=child)

    rows = _rows(client)

    assert rows["Groceries"]["id"] == child
    assert rows["Groceries"]["parent_id"] == group
    assert rows["Groceries"]["kind"] == CategoryKind.EXPENSE.value
    assert rows["Groceries"]["direct_paise"] == 30_000
    assert rows["Groceries"]["total_paise"] == 30_000
    assert rows["Food"]["direct_paise"] == 0
    assert rows["Food"]["total_paise"] == 30_000


def test_spending_filed_under_the_group_itself_adds_to_its_children(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    group, child, _ = _tree(db, user)
    _expense(client, account_id, 10_000, "2026-10-04", category_id=group)
    _expense(client, account_id, 30_000, "2026-10-05", category_id=child)

    rows = _rows(client)

    assert rows["Food"]["direct_paise"] == 10_000
    assert rows["Food"]["total_paise"] == 40_000


def test_a_split_is_counted_under_each_of_its_parts(
    client: TestClient, db: Session, user: User
) -> None:
    """The report reads the postings, so each part lands where it was filed."""
    _sign_in(client)
    account_id = _account(db, user)
    _, child, other = _tree(db, user)
    _expense(
        client,
        account_id,
        50_000,
        "2026-10-04",
        parts=[
            {"amount_paise": 30_000, "category_id": child},
            {"amount_paise": 20_000, "category_id": other},
        ],
    )

    rows = _rows(client)

    assert rows["Groceries"]["direct_paise"] == 30_000
    assert rows["Food"]["total_paise"] == 30_000
    assert rows["Travel"]["total_paise"] == 20_000


def test_uncategorised_spending_stays_out_of_the_trees_rows(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _tree(db, user)
    _expense(client, account_id, 30_000, "2026-10-04")

    rows = _rows(client)

    assert rows["Food"]["total_paise"] == 0
    assert rows["Groceries"]["total_paise"] == 0
    assert set(rows) == {"Food", "Groceries", "Travel"}
    # It is reported, but apart from the tree: there is no category to file it under.
    assert _report(client)["uncategorised_paise"] == 30_000


def test_income_and_write_offs_are_not_spending(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _tree(db, user)
    salary = create_category(db, user.id, "Salary", kind=CategoryKind.INCOME).id
    response = client.post(
        TRANSACTIONS,
        json={
            "kind": "income",
            "account_id": account_id,
            "amount_paise": 9_00_000_00,
            "transaction_date": "2026-10-04",
            "category_id": salary,
        },
    )
    assert response.status_code == 201
    check = client.post(
        f"/api/v1/accounts/{account_id}/balance-checks",
        json={
            "account_id": account_id,
            "stated_balance_paise": OPENING_PAISE - 250_00,
            "on": "2026-10-05",
            "adjust": True,
        },
    )
    assert check.status_code == 201

    rows = _rows(client)

    assert "Salary" not in rows
    assert rows["Food"]["total_paise"] == 0
    assert rows["Groceries"]["total_paise"] == 0


def test_the_period_narrows_the_report_at_both_ends(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _, child, _ = _tree(db, user)
    _expense(client, account_id, 10_000, "2026-09-30", category_id=child)
    _expense(client, account_id, 20_000, "2026-10-01", category_id=child)
    _expense(client, account_id, 30_000, "2026-10-31", category_id=child)
    _expense(client, account_id, 40_000, "2026-11-01", category_id=child)

    rows = _rows(client, "?from=2026-10-01&to=2026-10-31")

    assert rows["Groceries"]["direct_paise"] == 50_000


def test_the_period_may_be_left_open_at_either_end(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _, child, _ = _tree(db, user)
    _expense(client, account_id, 10_000, "2026-09-30", category_id=child)
    _expense(client, account_id, 20_000, "2026-10-01", category_id=child)

    assert _rows(client, "?from=2026-10-01")["Groceries"]["direct_paise"] == 20_000
    assert _rows(client, "?to=2026-09-30")["Groceries"]["direct_paise"] == 10_000


def test_a_deleted_transaction_leaves_the_report(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _, child, _ = _tree(db, user)
    _expense(client, account_id, 30_000, "2026-10-04", category_id=child)
    listed = client.get(TRANSACTIONS).json()
    assert client.delete(f"{TRANSACTIONS}/{listed[0]['id']}").status_code == 204

    rows = _rows(client)

    assert rows["Groceries"]["total_paise"] == 0
    assert rows["Food"]["total_paise"] == 0


def test_another_users_spending_is_not_in_the_report(
    client: TestClient, db: Session, user: User
) -> None:
    """Their tree, their movements: neither appears in this report."""
    _sign_in(client)
    other = create_user(db, "someone@example.com", "another-passphrase")
    other_account = _account(db, other)
    theirs = create_category(
        db, other.id, "Their travel", kind=CategoryKind.EXPENSE
    ).id  # A session of their own, so the recording goes through the same routes.
    with TestClient(client.app) as theirs_only:
        sign_in = theirs_only.post(
            "/api/v1/auth/login",
            json={"email": "someone@example.com", "password": "another-passphrase"},
        )
        assert sign_in.status_code == 200
        posted = theirs_only.post(
            TRANSACTIONS,
            json={
                "kind": "expense",
                "account_id": other_account,
                "amount_paise": 30_000,
                "transaction_date": "2026-10-04",
                "category_id": theirs,
            },
        )
        assert posted.status_code == 201

    mine = create_category(db, user.id, "Travel", kind=CategoryKind.EXPENSE).id
    _expense(client, _account(db, user), 500_00, "2026-10-04", category_id=mine)

    rows = _rows(client)

    assert "Their travel" not in rows
    assert rows["Travel"]["total_paise"] == 500_00
    assert _report(client)["uncategorised_paise"] == 0
