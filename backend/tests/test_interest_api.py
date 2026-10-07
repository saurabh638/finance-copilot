"""What the interest endpoints promise, over HTTP.

Thin tests by design: the arithmetic and the posting rules are settled in
`tests/test_interest.py` and `tests/test_interest_service.py`. What is checked here
is the translation - which status a refusal becomes, and that a confirmation comes
back with both figures and a movement behind it.
"""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, RateFrequency, User
from app.schemas.account import AccountCreate
from app.schemas.interest_rate import InterestRateCreate
from app.services.accounts import create_account
from app.services.auth import create_user
from app.services.interest_rates import create_rate

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
OPENED = date(2026, 4, 1)
LAKH = 1_00_000_00
OCTOBER = 60_301  # ₹1,00,000 at 7.1% for 31 days, hand-worked

ACCOUNTS = "/api/v1/accounts"
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
            opening_balance_paise=LAKH,
            opening_date=OPENED,
        ),
    )
    return account.id


def _rate(
    db: Session,
    user: User,
    account_id: int,
    *,
    from_date: date = date(2026, 10, 1),
    frequency: RateFrequency = RateFrequency.MONTHLY,
) -> None:
    create_rate(
        db,
        user.id,
        account_id,
        InterestRateCreate(rate=Decimal("7.1"), from_date=from_date, frequency=frequency),
    )


def test_a_period_can_be_worked_out_read_and_credited(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _rate(db, user, account_id)

    proposed = client.post(
        f"{ACCOUNTS}/{account_id}/interest/propose", json={"through": "2026-10-31"}
    )

    assert proposed.status_code == 200, proposed.text
    (period,) = proposed.json()
    assert period["period_start"] == "2026-10-01"
    assert period["period_end"] == "2026-10-31"
    assert period["computed_paise"] == OCTOBER
    assert Decimal(period["rate_percent"]) == Decimal("7.1000")
    assert period["credited_paise"] is None

    waiting = client.get(f"{ACCOUNTS}/{account_id}/interest").json()
    assert waiting["credited_paise"] == 0
    assert waiting["uncredited_paise"] == OCTOBER
    assert [row["id"] for row in waiting["proposals"]] == [period["id"]]
    assert waiting["history"] == []

    confirmed = client.post(
        f"{ACCOUNTS}/{account_id}/interest/{period['id']}/confirm",
        json={"on": "2026-11-02"},
    )

    assert confirmed.status_code == 200, confirmed.text
    credited = confirmed.json()
    assert credited["credited_paise"] == OCTOBER
    assert credited["confirmed_on"] == "2026-11-02"

    after = client.get(f"{ACCOUNTS}/{account_id}/interest").json()
    assert after["credited_paise"] == OCTOBER
    assert after["uncredited_paise"] == 0
    assert after["proposals"] == []
    assert [row["id"] for row in after["history"]] == [period["id"]]

    ledger = client.get(TRANSACTIONS, params={"from": "2026-10-01", "to": "2026-10-31"}).json()
    assert len(ledger) == 1
    assert ledger[0]["id"] == credited["transaction_id"]
    assert ledger[0]["transaction_date"] == "2026-10-31"
    assert ledger[0]["postings"][0]["kind"] == "interest"
    assert ledger[0]["postings"][0]["amount_paise"] == OCTOBER
    assert ledger[0]["postings"][0]["category_id"] is None

    balance = client.get(f"{ACCOUNTS}/{account_id}/balance").json()
    assert balance["balance_paise"] == LAKH + OCTOBER


def test_the_banks_figure_is_what_is_posted(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _rate(db, user, account_id)
    (period,) = client.post(
        f"{ACCOUNTS}/{account_id}/interest/propose", json={"through": "2026-10-31"}
    ).json()

    confirmed = client.post(
        f"{ACCOUNTS}/{account_id}/interest/{period['id']}/confirm",
        json={"credited_paise": 60_500, "on": "2026-11-02"},
    ).json()

    assert confirmed["computed_paise"] == OCTOBER
    assert confirmed["credited_paise"] == 60_500
    assert client.get(f"{ACCOUNTS}/{account_id}/balance").json()["balance_paise"] == LAKH + 60_500


def test_working_out_the_same_period_twice_proposes_it_once(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _rate(db, user, account_id)
    asked = {"through": "2026-10-31"}

    assert len(client.post(f"{ACCOUNTS}/{account_id}/interest/propose", json=asked).json()) == 1
    assert client.post(f"{ACCOUNTS}/{account_id}/interest/propose", json=asked).json() == []


def test_a_day_is_not_worked_out_until_it_has_finished(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _rate(db, user, account_id)

    response = client.post(
        f"{ACCOUNTS}/{account_id}/interest/propose", json={"through": "2026-10-30"}
    )

    assert response.status_code == 200
    assert response.json() == []


def test_crediting_a_period_twice_is_a_409(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _rate(db, user, account_id)
    (period,) = client.post(
        f"{ACCOUNTS}/{account_id}/interest/propose", json={"through": "2026-10-31"}
    ).json()
    client.post(f"{ACCOUNTS}/{account_id}/interest/{period['id']}/confirm")

    again = client.post(f"{ACCOUNTS}/{account_id}/interest/{period['id']}/confirm")

    assert again.status_code == 409
    assert "already credited" in again.json()["detail"]


def test_a_credited_period_cannot_be_thrown_away(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _rate(db, user, account_id)
    (period,) = client.post(
        f"{ACCOUNTS}/{account_id}/interest/propose", json={"through": "2026-10-31"}
    ).json()
    client.post(f"{ACCOUNTS}/{account_id}/interest/{period['id']}/confirm")

    refused = client.delete(f"{ACCOUNTS}/{account_id}/interest/{period['id']}")

    assert refused.status_code == 409
    assert "remove its movement instead" in refused.json()["detail"]


def test_a_proposal_can_be_thrown_away_and_worked_out_again(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _rate(db, user, account_id)
    (period,) = client.post(
        f"{ACCOUNTS}/{account_id}/interest/propose", json={"through": "2026-10-31"}
    ).json()

    assert client.delete(f"{ACCOUNTS}/{account_id}/interest/{period['id']}").status_code == 204
    assert client.get(f"{ACCOUNTS}/{account_id}/interest").json()["proposals"] == []

    again = client.post(
        f"{ACCOUNTS}/{account_id}/interest/propose", json={"through": "2026-10-31"}
    ).json()
    assert [row["computed_paise"] for row in again] == [OCTOBER]


def test_a_yearly_rate_is_a_400_with_the_reason(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _rate(db, user, account_id, from_date=date(2026, 1, 1), frequency=RateFrequency.YEARLY)

    refused = client.post(
        f"{ACCOUNTS}/{account_id}/interest/propose", json={"through": "2026-12-31"}
    )

    assert refused.status_code == 400
    assert "has no crediting period" in refused.json()["detail"]


def test_an_account_with_no_rate_simply_has_nothing_to_propose(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = client.post(
        f"{ACCOUNTS}/{account_id}/interest/propose", json={"through": "2026-10-31"}
    )

    assert response.status_code == 200
    assert response.json() == []


def test_an_unknown_account_and_an_unknown_period_are_404s(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    assert client.get(f"{ACCOUNTS}/999/interest").status_code == 404
    assert client.post(f"{ACCOUNTS}/{account_id}/interest/999/confirm").status_code == 404
    assert client.delete(f"{ACCOUNTS}/{account_id}/interest/999").status_code == 404


def test_working_out_interest_for_another_users_account_is_a_404(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    other = create_user(db, "someone@example.com", "another-passphrase")
    account_id = _account(db, other)

    assert client.get(f"{ACCOUNTS}/{account_id}/interest").status_code == 404
    assert client.post(f"{ACCOUNTS}/{account_id}/interest/propose").status_code == 404


def test_the_interest_endpoints_need_a_login(client: TestClient) -> None:
    assert client.get(f"{ACCOUNTS}/1/interest").status_code == 401
    assert client.post(f"{ACCOUNTS}/1/interest/propose").status_code == 401
