"""API-level category tests: the tree's rules as a client sees them."""

from datetime import date

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, Category, CategoryKind, Posting, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.auth import create_user
from app.services.transactions import record_expense

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"

CATEGORIES = "/api/v1/categories"


def _sign_in(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})
    assert response.status_code == 200


def _category(
    client: TestClient,
    name: str,
    kind: str | None = None,
    parent_id: int | None = None,
) -> Response:
    payload: dict[str, object] = {"name": name}
    if kind is not None:
        payload["kind"] = kind
    if parent_id is not None:
        payload["parent_id"] = parent_id
    return client.post(CATEGORIES, json=payload)


def _branch(client: TestClient, name: str = "Coffee", kind: str = "expense") -> int:
    response = _category(client, name, kind)
    assert response.status_code == 201
    return response.json()["id"]


def _filed_movement(db: Session, user: User, category_id: int) -> None:
    """A movement with a posting filed under the category, for the in-use rule."""
    account = create_account(
        db,
        user.id,
        AccountCreate(
            name="SBI",
            type=AccountType.SAVINGS,
            capture_mode=CaptureMode.STATEMENT_IMPORT,
            opening_balance_paise=10_000_00,
            opening_date=date(2026, 4, 1),
        ),
    )
    record_expense(db, user.id, account.id, 5_000, date(2026, 10, 1))
    posting = db.scalars(select(Posting)).one()
    posting.category_id = category_id
    db.commit()


def test_categories_need_a_session(client: TestClient) -> None:
    assert client.get(CATEGORIES).status_code == 401
    assert client.post(CATEGORIES, json={"name": "Coffee"}).status_code == 401
    assert client.patch(f"{CATEGORIES}/1", json={"name": "Tea"}).status_code == 401
    assert client.delete(f"{CATEGORIES}/1").status_code == 401
    assert client.post(f"{CATEGORIES}/defaults").status_code == 401


def test_an_empty_tree_is_empty(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)

    assert client.get(CATEGORIES).json() == []


def test_a_branch_and_its_child_come_back_as_one_tree(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    coffee = _branch(client, "Coffee")

    child = _category(client, "Latte", parent_id=coffee)

    assert child.status_code == 201
    assert child.json() == {
        "id": child.json()["id"],
        "name": "Latte",
        "parent_id": coffee,
        "kind": "expense",
    }
    listed = client.get(CATEGORIES).json()
    assert [row["name"] for row in listed] == ["Coffee", "Latte"]


def test_spending_and_earning_stay_apart(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    income = _branch(client, "Pocket money", "income")

    disagreeing = _category(client, "Latte", "expense", parent_id=income)
    child = _category(client, "Latte", parent_id=income)
    too_deep = _category(client, "Extra shot", parent_id=child.json()["id"])

    assert disagreeing.status_code == 400
    assert "parent's kind" in disagreeing.json()["detail"]
    assert too_deep.status_code == 400
    assert "two levels" in too_deep.json()["detail"]


def test_a_top_level_category_needs_a_kind(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)

    response = _category(client, "Coffee")

    assert response.status_code == 400
    assert "kind" in response.json()["detail"]


def test_a_name_cannot_be_used_twice_in_the_same_place(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    coffee = _branch(client, "Coffee")
    tea = _branch(client, "Tea")
    _category(client, "Latte", parent_id=coffee)

    at_top = _category(client, "Coffee", "expense")
    under_the_same_branch = _category(client, "Latte", parent_id=coffee)
    # The same name under a different branch is a different place, and is fine.
    elsewhere = _category(client, "Latte", parent_id=tea)

    assert at_top.status_code == 400
    assert "already" in at_top.json()["detail"]
    assert under_the_same_branch.status_code == 400
    assert elsewhere.status_code == 201


def test_a_missing_name_is_a_validation_error(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)

    assert client.post(CATEGORIES, json={"kind": "expense"}).status_code == 422
    assert client.post(CATEGORIES, json={"name": "", "kind": "expense"}).status_code == 422


def test_a_category_can_be_renamed_and_moved(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    coffee = _branch(client, "Coffee")
    child = _category(client, "Latte", parent_id=coffee).json()["id"]

    renamed = client.patch(f"{CATEGORIES}/{child}", json={"name": "Filter coffee"})
    moved = client.patch(f"{CATEGORIES}/{child}", json={"parent_id": None})

    assert renamed.json()["name"] == "Filter coffee"
    assert renamed.json()["parent_id"] == coffee
    assert moved.json()["parent_id"] is None
    assert moved.json()["kind"] == "expense"


def test_patching_one_field_leaves_the_others_alone(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    coffee = _branch(client, "Coffee")
    child = _category(client, "Latte", parent_id=coffee).json()["id"]

    renamed = client.patch(f"{CATEGORIES}/{child}", json={"name": "Flat white"})

    assert renamed.json()["name"] == "Flat white"
    assert renamed.json()["parent_id"] == coffee


def test_a_category_that_is_not_there_answers_404(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    _branch(client)

    assert client.patch(f"{CATEGORIES}/999", json={"name": "Tea"}).status_code == 404
    assert client.delete(f"{CATEGORIES}/999").status_code == 404


def test_another_users_categories_are_not_visible(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    other = create_user(db, "someone@example.com", "another-passphrase")
    theirs = _category_for(db, other)

    assert client.get(CATEGORIES).json() == []
    assert client.patch(f"{CATEGORIES}/{theirs}", json={"name": "Tea"}).status_code == 404


def _category_for(db: Session, owner: User) -> int:
    made = Category(user_id=owner.id, name="Theirs", parent_id=None, kind=CategoryKind.EXPENSE)
    db.add(made)
    db.commit()
    return made.id


def test_an_unused_category_can_be_removed(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    coffee = _branch(client)

    response = client.delete(f"{CATEGORIES}/{coffee}")

    assert response.status_code == 204
    assert client.get(CATEGORIES).json() == []


def test_a_branch_with_children_cannot_be_removed(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    coffee = _branch(client)
    _category(client, "Latte", parent_id=coffee)

    response = client.delete(f"{CATEGORIES}/{coffee}")

    assert response.status_code == 409
    assert "Latte" in response.json()["detail"]
    assert len(client.get(CATEGORIES).json()) == 2


def test_a_category_holding_movements_cannot_be_removed(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    coffee = _branch(client)
    _filed_movement(db, user, coffee)

    response = client.delete(f"{CATEGORIES}/{coffee}")

    assert response.status_code == 409
    assert "1 movement" in response.json()["detail"]


def test_the_default_set_can_be_added_once(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)

    first = client.post(f"{CATEGORIES}/defaults")
    second = client.post(f"{CATEGORIES}/defaults")

    assert first.status_code == 200
    assert len(first.json()["created"]) == len(client.get(CATEGORIES).json())
    # Running it again fills nothing in, so an edited tree is never undone.
    assert second.json()["created"] == []


def test_the_default_set_includes_the_two_write_off_names(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    client.post(f"{CATEGORIES}/defaults")

    listed = client.get(CATEGORIES).json()
    names = {row["name"] for row in listed}
    adjustments = {row["name"] for row in listed if row["kind"] == "adjustment"}

    assert names >= {"Unaccounted for spending", "Unrecorded income"}
    assert adjustments == {"Unaccounted for spending", "Unrecorded income"}
