"""API-level interest-rate tests: the auth guard, exact decimals and history."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.auth import create_user

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"

ACCOUNT: dict[str, object] = {
    "name": "SBI",
    "type": "savings",
    "capture_mode": "statement_import",
    "opening_balance_paise": 1_23_456_78,
    "opening_date": "2026-04-01",
}

RATE: dict[str, object] = {
    "rate": "7.1",
    "from_date": "2026-04-01",
    "frequency": "quarterly",
    "note": "before the repo cut",
}


def _sign_in(client: TestClient) -> None:
    """Log the owner in, so the session cookie is on the client."""
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})
    assert response.status_code == 200


def _account(client: TestClient, **overrides: object) -> dict[str, object]:
    """Create an account over HTTP and return the response body."""
    response = client.post("/api/v1/accounts", json={**ACCOUNT, **overrides})
    assert response.status_code == 201
    return response.json()


def _rate(client: TestClient, account_id: object, **overrides: object) -> dict[str, object]:
    """Record a rate over HTTP and return the response body."""
    response = client.post(
        f"/api/v1/accounts/{account_id}/interest-rates",
        json={**RATE, **overrides},
    )
    assert response.status_code == 201
    return response.json()


def _rates_path(account_id: object) -> str:
    return f"/api/v1/accounts/{account_id}/interest-rates"


def test_rates_reject_anonymous(client: TestClient) -> None:
    assert client.post(_rates_path(1), json=RATE).status_code == 401
    assert client.get(_rates_path(1)).status_code == 401
    assert client.delete(f"{_rates_path(1)}/1").status_code == 401


def test_create_returns_201_with_an_exact_decimal(client: TestClient, user: User) -> None:
    _sign_in(client)
    account = _account(client)

    body = _rate(client, account["id"])

    assert body["account_id"] == account["id"]
    assert body["rate"] == "7.1000"
    assert isinstance(body["rate"], str)
    assert body["from_date"] == "2026-04-01"
    assert body["frequency"] == "quarterly"
    assert body["note"] == "before the repo cut"


def test_history_keeps_both_rates_newest_first(client: TestClient, user: User) -> None:
    _sign_in(client)
    account = _account(client)
    _rate(client, account["id"])
    _rate(client, account["id"], rate="6.5", from_date="2026-07-01")

    response = client.get(_rates_path(account["id"]))

    assert response.status_code == 200
    assert [rate["rate"] for rate in response.json()] == ["6.5000", "7.1000"]
    assert [rate["from_date"] for rate in response.json()] == ["2026-07-01", "2026-04-01"]


def test_the_same_start_date_is_a_conflict(client: TestClient, user: User) -> None:
    _sign_in(client)
    account = _account(client)
    _rate(client, account["id"])

    response = client.post(_rates_path(account["id"]), json={**RATE, "rate": "6.5"})

    assert response.status_code == 409
    assert "2026-04-01" in response.json()["detail"]


def test_five_decimal_places_are_rejected_not_rounded(client: TestClient, user: User) -> None:
    _sign_in(client)
    account = _account(client)

    response = client.post(_rates_path(account["id"]), json={**RATE, "rate": "7.12345"})

    assert response.status_code == 422


def test_a_negative_rate_is_rejected(client: TestClient, user: User) -> None:
    _sign_in(client)
    account = _account(client)

    response = client.post(_rates_path(account["id"]), json={**RATE, "rate": "-0.5"})

    assert response.status_code == 422


def test_an_unknown_frequency_is_rejected(client: TestClient, user: User) -> None:
    _sign_in(client)
    account = _account(client)

    response = client.post(_rates_path(account["id"]), json={**RATE, "frequency": "fortnightly"})

    assert response.status_code == 422


def test_a_rate_on_an_unknown_account_is_404(client: TestClient, user: User) -> None:
    _sign_in(client)

    assert client.post(_rates_path(999), json=RATE).status_code == 404
    assert client.get(_rates_path(999)).status_code == 404
    assert client.delete(f"{_rates_path(999)}/1").status_code == 404


def test_another_users_account_is_404(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    other = create_user(db, "other@example.com", PASSPHRASE)
    theirs = create_account(db, other.id, AccountCreate.model_validate(ACCOUNT))

    assert client.post(_rates_path(theirs.id), json=RATE).status_code == 404


def test_another_accounts_rate_is_404(client: TestClient, user: User) -> None:
    _sign_in(client)
    first = _account(client)
    second = _account(client, name="HDFC")
    rate = _rate(client, first["id"])

    response = client.delete(f"{_rates_path(second['id'])}/{rate['id']}")

    assert response.status_code == 404


def test_delete_hides_the_rate_and_cannot_be_repeated(client: TestClient, user: User) -> None:
    _sign_in(client)
    account = _account(client)
    rate = _rate(client, account["id"])
    path = f"{_rates_path(account['id'])}/{rate['id']}"

    assert client.delete(path).status_code == 204
    assert client.get(_rates_path(account["id"])).json() == []
    assert client.delete(path).status_code == 404


def test_a_soft_deleted_rate_frees_its_start_date(client: TestClient, user: User) -> None:
    _sign_in(client)
    account = _account(client)
    mistaken = _rate(client, account["id"])
    client.delete(f"{_rates_path(account['id'])}/{mistaken['id']}")

    corrected = _rate(client, account["id"], rate="6.5")

    assert corrected["rate"] == "6.5000"


def test_list_honours_limit_and_offset(client: TestClient, user: User) -> None:
    _sign_in(client)
    account = _account(client)
    for day, rate in ((1, "7.1"), (2, "7.0"), (3, "6.9")):
        _rate(client, account["id"], rate=rate, from_date=f"2026-04-0{day}")

    response = client.get(_rates_path(account["id"]), params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    assert [item["rate"] for item in response.json()] == ["7.0000"]
