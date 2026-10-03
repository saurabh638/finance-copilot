"""API-level auth tests: public routes, login, logout, and the anonymous guard."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.auth import create_user

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"


def test_health_is_public(client: TestClient) -> None:
    assert client.get("/api/v1/health").status_code == 200


def test_me_rejects_anonymous(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_rejects_anonymous(client: TestClient) -> None:
    assert client.post("/api/v1/auth/logout").status_code == 401


def test_login_sets_an_httponly_cookie(client: TestClient, db: Session) -> None:
    create_user(db, EMAIL, PASSPHRASE)

    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "email": EMAIL}
    set_cookie = response.headers["set-cookie"]
    assert "finance_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_login_rejects_a_wrong_password(client: TestClient, db: Session) -> None:
    create_user(db, EMAIL, PASSPHRASE)

    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "wrong"})

    assert response.status_code == 401


def test_login_rejects_an_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": PASSPHRASE},
    )

    assert response.status_code == 401


def test_me_returns_the_user_after_login(client: TestClient, db: Session) -> None:
    create_user(db, EMAIL, PASSPHRASE)
    client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json() == {"id": 1, "email": EMAIL}


def test_logout_ends_the_session(client: TestClient, db: Session) -> None:
    create_user(db, EMAIL, PASSPHRASE)
    client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_login_is_rate_limited_after_repeated_failures(client: TestClient, db: Session) -> None:
    create_user(db, EMAIL, PASSPHRASE)

    for _ in range(5):
        attempt = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "wrong"})
        assert attempt.status_code == 401

    blocked = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})

    assert blocked.status_code == 429


def test_a_successful_login_clears_earlier_failures(client: TestClient, db: Session) -> None:
    create_user(db, EMAIL, PASSPHRASE)
    client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "wrong"})

    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})

    assert response.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200
