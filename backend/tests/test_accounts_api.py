"""API-level account tests: the auth guard, CRUD, and soft delete over HTTP."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Account, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.auth import create_user

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"

PAYLOAD: dict[str, object] = {
    "name": "SBI",
    "type": "savings",
    "capture_mode": "statement_import",
    "opening_balance_paise": 1_23_456_78,
    "opening_date": "2026-04-01",
}


def _sign_in(client: TestClient) -> None:
    """Log the owner in, so the session cookie is on the client."""
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})
    assert response.status_code == 200


def _create(client: TestClient, **overrides: object) -> dict[str, object]:
    """Create an account over HTTP and return the response body."""
    response = client.post("/api/v1/accounts", json={**PAYLOAD, **overrides})
    assert response.status_code == 201
    return response.json()


def test_accounts_reject_anonymous(client: TestClient) -> None:
    assert client.get("/api/v1/accounts").status_code == 401
    assert client.post("/api/v1/accounts", json=PAYLOAD).status_code == 401
    assert client.get("/api/v1/accounts/1").status_code == 401
    assert client.patch("/api/v1/accounts/1", json={"name": "x"}).status_code == 401
    assert client.delete("/api/v1/accounts/1").status_code == 401


def test_create_returns_201_and_keeps_the_exact_paise(client: TestClient, user: User) -> None:
    _sign_in(client)

    body = _create(client)

    assert body["id"] == 1
    assert body["name"] == "SBI"
    assert body["type"] == "savings"
    assert body["opening_balance_paise"] == 1_23_456_78
    assert body["parent_id"] is None
    assert body["statement_day"] is None
    assert body["created_at"] is not None


def test_create_rejects_a_pot_with_an_unknown_parent(client: TestClient, user: User) -> None:
    _sign_in(client)

    response = client.post(
        "/api/v1/accounts",
        json={**PAYLOAD, "type": "pot", "parent_id": 999},
    )

    assert response.status_code == 400
    assert "999" in response.json()["detail"]


def test_create_rejects_a_payload_the_database_rules_forbid(client: TestClient, user: User) -> None:
    _sign_in(client)

    response = client.post("/api/v1/accounts", json={**PAYLOAD, "statement_day": 5})

    assert response.status_code == 422


def test_list_returns_only_the_users_live_accounts(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    _create(client, name="SBI")
    _create(client, name="HDFC")

    other = create_user(db, "other@example.com", PASSPHRASE)
    create_account(db, other.id, AccountCreate(**{**PAYLOAD, "name": "Not mine"}))

    response = client.get("/api/v1/accounts")

    assert response.status_code == 200
    assert [account["name"] for account in response.json()] == ["SBI", "HDFC"]


def test_list_honours_limit_and_offset(client: TestClient, user: User) -> None:
    _sign_in(client)
    for name in ("A", "B", "C"):
        _create(client, name=name)

    response = client.get("/api/v1/accounts", params={"limit": 2, "offset": 1})

    assert response.status_code == 200
    assert [account["name"] for account in response.json()] == ["B", "C"]


def test_get_returns_404_for_an_unknown_account(client: TestClient, user: User) -> None:
    _sign_in(client)

    assert client.get("/api/v1/accounts/999").status_code == 404


def test_patch_applies_only_the_fields_given(client: TestClient, user: User) -> None:
    _sign_in(client)
    created = _create(client)

    response = client.patch(f"/api/v1/accounts/{created['id']}", json={"name": "SBI salary"})

    assert response.status_code == 200
    assert response.json()["name"] == "SBI salary"
    assert response.json()["opening_balance_paise"] == 1_23_456_78


def test_patch_never_changes_the_type(client: TestClient, user: User) -> None:
    _sign_in(client)
    created = _create(client)

    response = client.patch(f"/api/v1/accounts/{created['id']}", json={"type": "cash"})

    assert response.status_code == 200
    assert response.json()["type"] == "savings"


def test_patch_of_an_unknown_account_is_404(client: TestClient, user: User) -> None:
    _sign_in(client)

    assert client.patch("/api/v1/accounts/999", json={"name": "x"}).status_code == 404


def test_delete_soft_deletes_and_cannot_be_repeated(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    created = _create(client)

    assert client.delete(f"/api/v1/accounts/{created['id']}").status_code == 204
    assert client.get(f"/api/v1/accounts/{created['id']}").status_code == 404
    assert client.get("/api/v1/accounts").json() == []
    assert client.delete(f"/api/v1/accounts/{created['id']}").status_code == 404

    kept = db.get(Account, created["id"])
    assert kept is not None
    assert kept.deleted_at is not None
