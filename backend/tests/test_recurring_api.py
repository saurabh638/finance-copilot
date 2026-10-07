"""What the check-in asks the API for: what is owed, and settling it.

The rules being pinned here are the ones the screen depends on being told the
truth about: an item is owed on its day, confirming writes one ordinary movement
dated that day, and a skip writes nothing at all.
"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, CategoryKind, PostingKind, RecurringFrequency, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.auth import create_user
from app.services.categories import create_category
from app.services.recurring import create_item

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
TODAY = date.today()
OPENED = date(2026, 4, 1)
OPENING_PAISE = 1_00_000_00
RENT_PAISE = 1_800_000  # ₹18,000.00

ITEMS = "/api/v1/recurring-items"
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


def _category(db: Session, user: User, name: str, kind: CategoryKind) -> int:
    return create_category(db, user.id, name, kind=kind).id


def _plan(client: TestClient, account_id: int, **overrides: object) -> dict[str, object]:
    """A monthly rent due on the 1st, unless the test says otherwise."""
    payload: dict[str, object] = {
        "name": "Rent",
        "kind": "expense",
        "amount_paise": RENT_PAISE,
        "account_id": account_id,
        "frequency": "monthly",
        "starts_on": OPENED.isoformat(),
        "day_of_month": 1,
        **overrides,
    }
    response = client.post(ITEMS, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_an_item_can_be_planned_and_read_back(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    made = _plan(client, account_id)

    assert made["name"] == "Rent"
    assert made["amount_paise"] == RENT_PAISE
    assert made["frequency"] == "monthly"
    assert made["day_of_month"] == 1
    assert made["is_active"] is True
    assert made["ends_on"] is None

    listed = client.get(ITEMS).json()
    assert [row["id"] for row in listed] == [made["id"]]


def test_a_rhythm_that_is_half_given_is_refused(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = client.post(
        ITEMS,
        json={
            "name": "Rent",
            "kind": "expense",
            "amount_paise": RENT_PAISE,
            "account_id": account_id,
            "frequency": "monthly",
            "starts_on": OPENED.isoformat(),
        },
    )

    assert response.status_code == 400
    assert "day of the month" in response.json()["detail"]


def test_a_weekly_item_needs_a_weekday(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = client.post(
        ITEMS,
        json={
            "name": "Household help",
            "kind": "expense",
            "amount_paise": 200_000,
            "account_id": account_id,
            "frequency": "weekly",
            "starts_on": OPENED.isoformat(),
            "weekday": 0,
        },
    )

    assert response.status_code == 201
    assert response.json()["weekday"] == 0
    assert response.json()["day_of_month"] is None


def test_an_unknown_account_is_a_404(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)

    response = client.post(
        ITEMS,
        json={
            "name": "Rent",
            "kind": "expense",
            "amount_paise": RENT_PAISE,
            "account_id": 999,
            "frequency": "monthly",
            "starts_on": OPENED.isoformat(),
            "day_of_month": 1,
        },
    )

    assert response.status_code == 404


def test_an_unknown_category_is_a_404(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = client.post(
        ITEMS,
        json={
            "name": "Rent",
            "kind": "expense",
            "amount_paise": RENT_PAISE,
            "account_id": account_id,
            "frequency": "monthly",
            "starts_on": OPENED.isoformat(),
            "day_of_month": 1,
            "category_id": 999,
        },
    )

    assert response.status_code == 404


def test_a_category_of_the_wrong_kind_is_a_400(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    salary = _category(db, user, "Salary", CategoryKind.INCOME)

    response = client.post(
        ITEMS,
        json={
            "name": "Rent",
            "kind": "expense",
            "amount_paise": RENT_PAISE,
            "account_id": account_id,
            "frequency": "monthly",
            "starts_on": OPENED.isoformat(),
            "day_of_month": 1,
            "category_id": salary,
        },
    )

    assert response.status_code == 400
    assert "Salary is for earning, not spending" in response.json()["detail"]


def test_what_is_owed_comes_with_the_day_it_is_owed_for(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _plan(client, account_id)

    response = client.get(f"{ITEMS}/due", params={"on": "2026-10-28"})

    assert response.status_code == 200
    (owed,) = response.json()
    assert owed["item"]["name"] == "Rent"
    assert owed["due_on"] == "2026-10-01"


def test_nothing_is_owed_before_the_day_arrives(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _plan(client, account_id, day_of_month=31)

    assert client.get(f"{ITEMS}/due", params={"on": "2026-10-30"}).json() == []
    assert len(client.get(f"{ITEMS}/due", params={"on": "2026-10-31"}).json()) == 1


def test_confirming_writes_one_movement_dated_the_day_it_was_owed(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries = _category(db, user, "Groceries", CategoryKind.EXPENSE)
    item = _plan(client, account_id, category_id=groceries)

    response = client.post(f"{ITEMS}/{item['id']}/confirm", params={"on": "2026-10-28"})

    assert response.status_code == 201, response.text
    written = response.json()
    assert written["due_on"] == "2026-10-01"

    recorded = client.get(TRANSACTIONS, params={"from": "2026-10-01", "to": "2026-10-31"}).json()
    assert [row["merchant"] for row in recorded] == ["Rent"]
    assert recorded[0]["id"] == written["transaction_id"]
    assert recorded[0]["transaction_date"] == "2026-10-01"
    assert recorded[0]["source"] == "recurring"
    assert recorded[0]["postings"][0]["amount_paise"] == -RENT_PAISE
    assert recorded[0]["postings"][0]["category_id"] == groceries

    assert client.get(f"{ITEMS}/due", params={"on": "2026-10-28"}).json() == []


def test_confirming_for_a_different_amount_uses_that_amount(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)

    response = client.post(
        f"{ITEMS}/{item['id']}/confirm",
        params={"on": "2026-10-02"},
        json={"amount_paise": 2_000_000},
    )

    assert response.status_code == 201
    recorded = client.get(TRANSACTIONS, params={"from": "2026-10-01", "to": "2026-10-31"}).json()
    assert recorded[0]["postings"][0]["amount_paise"] == -2_000_000
    assert client.get(ITEMS).json()[0]["amount_paise"] == RENT_PAISE


def test_confirming_the_same_period_twice_is_a_409_and_writes_nothing(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)
    client.post(f"{ITEMS}/{item['id']}/confirm", params={"on": "2026-10-02"})

    response = client.post(f"{ITEMS}/{item['id']}/confirm", params={"on": "2026-10-20"})

    assert response.status_code == 409
    assert "already recorded" in response.json()["detail"]
    assert len(client.get(TRANSACTIONS).json()) == 1


def test_confirming_something_that_is_not_due_is_a_409(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id, day_of_month=31)

    response = client.post(f"{ITEMS}/{item['id']}/confirm", params={"on": "2026-10-30"})

    assert response.status_code == 409
    assert client.get(TRANSACTIONS).json() == []


def test_skipping_settles_the_period_and_writes_nothing(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)

    response = client.post(f"{ITEMS}/{item['id']}/skip", params={"on": "2026-10-03"})

    assert response.status_code == 200
    assert response.json()["due_on"] == "2026-10-01"
    assert client.get(f"{ITEMS}/due", params={"on": "2026-10-05"}).json() == []
    assert client.get(TRANSACTIONS).json() == []


def test_skipping_twice_is_a_409(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)
    client.post(f"{ITEMS}/{item['id']}/skip", params={"on": "2026-10-03"})

    response = client.post(f"{ITEMS}/{item['id']}/skip", params={"on": "2026-10-03"})

    assert response.status_code == 409
    assert "was skipped" in response.json()["detail"]


def test_pausing_takes_the_item_out_of_what_is_owed_and_resuming_puts_it_back(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)

    paused = client.post(f"{ITEMS}/{item['id']}/pause")
    assert paused.status_code == 200
    assert paused.json()["is_active"] is False
    assert client.get(f"{ITEMS}/due", params={"on": "2026-10-05"}).json() == []

    resumed = client.post(f"{ITEMS}/{item['id']}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["is_active"] is True
    assert len(client.get(f"{ITEMS}/due", params={"on": "2026-10-05"}).json()) == 1


def test_a_paused_item_cannot_be_confirmed(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)
    client.post(f"{ITEMS}/{item['id']}/pause")

    response = client.post(f"{ITEMS}/{item['id']}/confirm", params={"on": "2026-10-05"})

    assert response.status_code == 409
    assert "paused" in response.json()["detail"]


def test_a_removed_item_is_not_listed_and_is_not_owed(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)

    assert client.delete(f"{ITEMS}/{item['id']}").status_code == 204
    assert client.get(ITEMS).json() == []
    assert client.get(f"{ITEMS}/due", params={"on": "2026-10-05"}).json() == []
    assert client.post(f"{ITEMS}/{item['id']}/confirm").status_code == 404


def test_changing_the_rhythm_moves_the_day_it_is_owed(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)

    response = client.patch(
        f"{ITEMS}/{item['id']}",
        json={"frequency": "monthly", "day_of_month": 5, "amount_paise": 1_900_000},
    )

    assert response.status_code == 200, response.text
    assert response.json()["day_of_month"] == 5
    assert response.json()["amount_paise"] == 1_900_000
    (owed,) = client.get(f"{ITEMS}/due", params={"on": "2026-10-06"}).json()
    assert owed["due_on"] == "2026-10-05"


def test_a_rhythm_change_without_a_frequency_is_a_400(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)

    response = client.patch(f"{ITEMS}/{item['id']}", json={"frequency": None})

    assert response.status_code == 400


def test_the_filing_is_cleared_by_sending_null(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    groceries = _category(db, user, "Groceries", CategoryKind.EXPENSE)
    item = _plan(client, account_id, category_id=groceries)

    cleared = client.patch(f"{ITEMS}/{item['id']}", json={"category_id": None})

    assert cleared.status_code == 200
    assert cleared.json()["category_id"] is None

    # A patch that says nothing about the filing leaves it alone.
    untouched = client.patch(f"{ITEMS}/{item['id']}", json={"name": "House rent"})
    assert untouched.json()["name"] == "House rent"
    assert untouched.json()["category_id"] is None


def test_a_nameless_patch_leaves_the_name_alone(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)

    response = client.patch(f"{ITEMS}/{item['id']}", json={"amount_paise": 2_100_000})

    assert response.status_code == 200
    assert response.json()["name"] == "Rent"
    assert response.json()["amount_paise"] == 2_100_000


def test_the_money_a_period_recorded_is_an_ordinary_movement(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)
    confirmed = client.post(f"{ITEMS}/{item['id']}/confirm", params={"on": "2026-10-02"}).json()

    corrected = client.patch(
        f"{TRANSACTIONS}/{confirmed['transaction_id']}", json={"amount_paise": 2_200_000}
    )

    assert corrected.status_code == 200
    assert corrected.json()["postings"][0]["amount_paise"] == -2_200_000
    # The period stays dealt with: correcting a figure does not un-confirm it.
    assert client.get(f"{ITEMS}/due", params={"on": "2026-10-05"}).json() == []


def test_removing_the_movement_makes_the_period_owed_again(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    item = _plan(client, account_id)
    confirmed = client.post(f"{ITEMS}/{item['id']}/confirm", params={"on": "2026-10-02"}).json()

    assert client.delete(f"{TRANSACTIONS}/{confirmed['transaction_id']}").status_code == 204
    (owed,) = client.get(f"{ITEMS}/due", params={"on": "2026-10-05"}).json()
    assert owed["due_on"] == "2026-10-01"


def test_another_users_item_is_a_404(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    other = create_user(db, "someone@example.com", "another-passphrase")
    account_id = _account(db, other)
    theirs = create_item(
        db,
        other.id,
        name="Rent",
        kind=PostingKind.EXPENSE,
        amount_paise=RENT_PAISE,
        account_id=account_id,
        frequency=RecurringFrequency.MONTHLY,
        starts_on=OPENED,
        day_of_month=1,
    )

    assert client.get(ITEMS).json() == []
    assert client.post(f"{ITEMS}/{theirs.id}/confirm").status_code == 404
    assert client.delete(f"{ITEMS}/{theirs.id}").status_code == 404


def test_the_endpoints_need_a_login(client: TestClient, db: Session, user: User) -> None:
    account_id = _account(db, user)
    body = {
        "name": "Rent",
        "kind": "expense",
        "amount_paise": RENT_PAISE,
        "account_id": account_id,
        "frequency": "monthly",
        "starts_on": OPENED.isoformat(),
        "day_of_month": 1,
    }

    assert client.get(ITEMS).status_code == 401
    assert client.post(ITEMS, json=body).status_code == 401
    assert client.get(f"{ITEMS}/due").status_code == 401
