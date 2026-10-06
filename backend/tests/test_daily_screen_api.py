"""What the daily screen asks the API for: names to offer, and the run of days.

The chips are only as good as the history behind them, so the rules are pinned
here: which movements count, what a suggestion remembers, and what ends a run.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.auth import create_user
from app.services.categories import CategoryKind, create_category
from app.services.transactions import record_expense

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
OPENED = date(2026, 4, 1)
# Inside the account's life, and outside the window a name is offered for.
LONG_AGO = date(2026, 4, 2)
OPENING_PAISE = 1_00_000_00

TRANSACTIONS = "/api/v1/transactions"
SUGGESTIONS = f"{TRANSACTIONS}/suggestions"
STREAK = f"{TRANSACTIONS}/streak"


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


def _spend(
    client: TestClient,
    account_id: int,
    merchant: str | None,
    on: date = TODAY,
    *,
    paise: int = 50_000,
    category_id: int | None = None,
    kind: str = "expense",
) -> None:
    response = client.post(
        TRANSACTIONS,
        json={
            "kind": kind,
            "account_id": account_id,
            "amount_paise": paise,
            "transaction_date": on.isoformat(),
            "merchant": merchant,
            **({} if category_id is None else {"category_id": category_id}),
        },
    )
    assert response.status_code == 201, response.text


def _suggestions(client: TestClient, query: str = "") -> list[dict[str, object]]:
    response = client.get(f"{SUGGESTIONS}{query}")
    assert response.status_code == 200
    return response.json()


def _streak(client: TestClient) -> dict[str, object]:
    response = client.get(STREAK)
    assert response.status_code == 200
    return response.json()


def test_the_chips_need_a_session(client: TestClient) -> None:
    assert client.get(SUGGESTIONS).status_code == 401
    assert client.get(STREAK).status_code == 401


def test_nothing_recorded_offers_nothing(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)

    assert _suggestions(client) == []


def test_a_name_is_offered_with_how_it_was_recorded_last(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries = create_category(db, user.id, "Groceries", kind=CategoryKind.EXPENSE).id
    _spend(client, account_id, "Blinkit", TODAY, paise=40_000, category_id=groceries)

    offered = _suggestions(client)

    assert offered == [
        {
            "merchant": "Blinkit",
            "times_used": 1,
            "last_used": TODAY.isoformat(),
            "account_id": account_id,
            "category_id": groceries,
            "amount_paise": 40_000,
        }
    ]


def test_the_same_name_twice_is_one_suggestion_that_says_so(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _spend(client, account_id, "Blinkit", TODAY - timedelta(days=3), paise=30_000)
    _spend(client, account_id, "Blinkit", TODAY, paise=45_000)

    offered = _suggestions(client)

    assert len(offered) == 1
    assert offered[0]["times_used"] == 2
    assert offered[0]["last_used"] == TODAY.isoformat()
    # What it remembers is the last time, so one tap records what happened most
    # recently rather than an average of everything.
    assert offered[0]["amount_paise"] == 45_000


def test_the_names_used_most_come_first(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    for day in range(3):
        _spend(client, account_id, "Blinkit", TODAY - timedelta(days=day))
    _spend(client, account_id, "Swiggy", TODAY)
    _spend(client, account_id, "Swiggy", YESTERDAY)

    assert [row["merchant"] for row in _suggestions(client)] == ["Blinkit", "Swiggy"]


def test_a_name_the_user_stopped_using_is_not_offered(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _spend(client, account_id, "Old shop", LONG_AGO)
    _spend(client, account_id, "Blinkit", TODAY)

    assert [row["merchant"] for row in _suggestions(client)] == ["Blinkit"]


def test_a_movement_with_no_merchant_offers_no_name(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _spend(client, account_id, None, TODAY)

    assert _suggestions(client) == []


def test_a_name_is_offered_once_however_many_accounts_it_used(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    first = _account(db, user)
    second = _account(db, user, name="Central Bank")
    _spend(client, first, "Blinkit", TODAY - timedelta(days=2))
    _spend(client, second, "Blinkit", TODAY)

    offered = _suggestions(client)

    assert len(offered) == 1
    assert offered[0]["account_id"] == second


def test_a_split_remembers_the_account_but_no_single_category(
    client: TestClient, db: Session, user: User
) -> None:
    """A split has several categories, so offering one of them would be a guess."""
    _sign_in(client)
    account_id = _account(db, user)
    groceries = create_category(db, user.id, "Groceries", kind=CategoryKind.EXPENSE).id
    other = create_category(db, user.id, "Travel", kind=CategoryKind.EXPENSE).id
    posted = client.post(
        TRANSACTIONS,
        json={
            "kind": "expense",
            "account_id": account_id,
            "amount_paise": 50_000,
            "transaction_date": TODAY.isoformat(),
            "merchant": "Big Bazaar",
            "parts": [
                {"amount_paise": 30_000, "category_id": groceries},
                {"amount_paise": 20_000, "category_id": other},
            ],
        },
    )
    assert posted.status_code == 201

    offered = _suggestions(client)

    assert offered[0]["account_id"] == account_id
    assert offered[0]["category_id"] is None
    assert offered[0]["amount_paise"] == 50_000


def test_a_removed_movement_is_not_history(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _spend(client, account_id, "Blinkit", TODAY)
    listed = client.get(TRANSACTIONS).json()
    assert client.delete(f"{TRANSACTIONS}/{listed[0]['id']}").status_code == 204

    assert _suggestions(client) == []


def test_the_limit_caps_what_is_offered(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    for index in range(4):
        for _ in range(index + 1):
            _spend(client, account_id, f"Shop {index}", TODAY)

    offered = _suggestions(client, "?limit=2")

    assert len(offered) == 2
    assert [row["merchant"] for row in offered] == ["Shop 3", "Shop 2"]


def test_another_users_history_is_not_offered(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    other = create_user(db, "someone@example.com", "another-passphrase")
    theirs = _account(db, other, name="Theirs")
    # Recorded through the service: this session has no business reaching it.
    record_expense(db, other.id, theirs, 50_000, TODAY, merchant="Their shop")

    assert _suggestions(client) == []


def test_a_run_of_days_is_counted(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    for day in range(3):
        _spend(client, account_id, "Blinkit", TODAY - timedelta(days=day))

    assert _streak(client) == {"days": 3, "today_recorded": True}


def test_a_run_that_ended_yesterday_is_not_broken(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _spend(client, account_id, "Blinkit", YESTERDAY)
    _spend(client, account_id, "Blinkit", TODAY - timedelta(days=2))

    assert _streak(client) == {"days": 2, "today_recorded": False}


def test_a_run_that_ended_two_days_ago_is_over(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _spend(client, account_id, "Blinkit", TODAY - timedelta(days=2))

    assert _streak(client) == {"days": 0, "today_recorded": False}
