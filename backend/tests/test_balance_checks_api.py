"""API-level balance-check tests: the comparison, the write-off and the nudge.

Written before the service and the routes, as MILESTONES.md M9 requires. The
figure that matters throughout is the same one: after a write-off, the computed
balance must equal the stated balance exactly, with no paise gained or lost.
"""

from datetime import date

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, Posting, PostingKind, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account, soft_delete_account
from app.services.auth import create_user
from app.services.categories import seed_defaults

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
OPENED = date(2026, 4, 1)
OPENING_PAISE = 1_00_000_00  # ₹1,00,000.00
CHECKED_ON = "2026-10-05"

BALANCE_CHECKS = "/api/v1/accounts/{account_id}/balance-checks"


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


def _check(
    client: TestClient,
    account_id: int,
    stated_paise: int,
    *,
    adjust: bool,
    on: str = CHECKED_ON,
) -> object:
    return client.post(
        BALANCE_CHECKS.format(account_id=account_id),
        json={"on": on, "stated_balance_paise": stated_paise, "adjust": adjust},
    )


def _balance(client: TestClient, account_id: int) -> int:
    return client.get(f"/api/v1/accounts/{account_id}/balance").json()["balance_paise"]


def _share(client: TestClient, account_id: int, month: str) -> dict[str, object]:
    return client.get(f"/api/v1/accounts/{account_id}/adjustment-share?month={month}").json()


def _adjust(client: TestClient, account_id: int, check_id: int) -> Response:
    return client.post(f"/api/v1/accounts/{account_id}/balance-checks/{check_id}/adjust")


def _expense(client: TestClient, account_id: int, paise: int, on: str) -> None:
    response = client.post(
        "/api/v1/transactions",
        json={
            "kind": "expense",
            "account_id": account_id,
            "amount_paise": paise,
            "transaction_date": on,
        },
    )
    assert response.status_code == 201


def test_a_balance_check_needs_a_session(client: TestClient) -> None:
    assert client.post(BALANCE_CHECKS.format(account_id=1), json={}).status_code == 401
    assert client.get(BALANCE_CHECKS.format(account_id=1)).status_code == 401
    assert client.get("/api/v1/accounts/1/adjustment-share").status_code == 401


def test_a_matching_balance_records_the_check_and_writes_nothing_off(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = _check(client, account_id, OPENING_PAISE, adjust=True)

    assert response.status_code == 201
    body = response.json()
    assert body["computed_balance_paise"] == OPENING_PAISE
    assert body["stated_balance_paise"] == OPENING_PAISE
    assert body["difference_paise"] == 0
    assert body["adjustment_transaction_id"] is None
    assert body["warning"] is False
    assert client.get("/api/v1/transactions").json() == []


def test_money_short_is_written_off_downwards_and_lands_on_the_stated_balance(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    stated = OPENING_PAISE - 500_00  # ₹500 is missing

    body = _check(client, account_id, stated, adjust=True).json()

    assert body["difference_paise"] == -500_00
    assert body["adjustment_transaction_id"] is not None
    assert _balance(client, account_id) == stated


def test_money_found_is_written_off_upwards_and_lands_on_the_stated_balance(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    stated = OPENING_PAISE + 25_00_000  # ₹25,000 arrived unrecorded

    body = _check(client, account_id, stated, adjust=True).json()

    assert body["difference_paise"] == 25_00_000
    assert _balance(client, account_id) == stated


def test_the_write_off_is_a_visible_posting_of_its_own_kind(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    stated = OPENING_PAISE - 500_00

    body = _check(client, account_id, stated, adjust=True).json()

    listed = client.get("/api/v1/transactions").json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["adjustment_transaction_id"]
    # No note: the wording is the category the write-off was filed under.
    assert listed[0]["note"] is None
    assert listed[0]["postings"][0]["kind"] == "adjustment"
    assert listed[0]["postings"][0]["amount_paise"] == -500_00

    posting = db.scalars(select(Posting).where(Posting.kind == PostingKind.ADJUSTMENT)).one()
    assert posting.amount_paise == -500_00


def test_a_write_off_is_worded_by_its_category_and_not_by_a_note(
    client: TestClient, db: Session, user: User
) -> None:
    """M10 files a write-off, so the wording lives there and nowhere else."""
    _sign_in(client)
    account_id = _account(db, user)
    seed_defaults(db, user.id)

    _check(client, account_id, OPENING_PAISE + 1_00_000, adjust=True)

    written = client.get("/api/v1/transactions").json()[0]
    filing = {row["id"]: row["name"] for row in client.get("/api/v1/categories").json()}
    assert filing[written["postings"][0]["category_id"]] == "Unrecorded income"
    assert written["note"] is None


def test_a_check_that_is_not_written_off_changes_nothing(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    body = _check(client, account_id, OPENING_PAISE - 500_00, adjust=False).json()

    assert body["difference_paise"] == -500_00
    assert body["adjustment_transaction_id"] is None
    assert client.get("/api/v1/transactions").json() == []
    assert _balance(client, account_id) == OPENING_PAISE


def test_a_large_write_off_is_flagged_but_never_refused(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    large = _check(client, account_id, OPENING_PAISE + 1_00_001, adjust=True)
    small = _check(client, account_id, OPENING_PAISE + 1_00_000, adjust=False)

    assert large.status_code == 201
    assert large.json()["warning"] is True
    assert large.json()["threshold_paise"] == 1_00_000
    # The nudge is advice, not a rule: exactly at the threshold is not above it.
    assert small.json()["warning"] is False


def test_a_write_off_is_flagged_in_either_direction(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    body = _check(client, account_id, OPENING_PAISE - 5_00_000, adjust=True).json()

    assert body["warning"] is True


def test_a_credit_card_balance_can_be_checked_and_written_off(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user, name="SBI Card", opening_paise=-10_000_00)
    stated = -9_500_00  # less is owed than the ledger thinks

    body = _check(client, account_id, stated, adjust=True).json()

    assert body["difference_paise"] == 500_00
    assert _balance(client, account_id) == stated


def test_a_check_before_the_account_opened_is_refused(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = _check(client, account_id, OPENING_PAISE, adjust=False, on="2026-03-31")

    assert response.status_code == 400
    assert "opened on 2026-04-01" in response.json()["detail"]
    assert client.get(BALANCE_CHECKS.format(account_id=account_id)).json() == []


def test_a_check_on_an_account_that_is_not_there_answers_404(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)

    assert _check(client, 999, OPENING_PAISE, adjust=True).status_code == 404
    assert client.get(BALANCE_CHECKS.format(account_id=999)).status_code == 404
    assert client.get("/api/v1/accounts/999/adjustment-share").status_code == 404


def test_a_check_on_a_removed_account_answers_404(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    soft_delete_account(db, user.id, account_id)

    assert _check(client, account_id, OPENING_PAISE, adjust=True).status_code == 404


def test_another_users_account_is_not_visible(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    other = create_user(db, "someone@example.com", "another-passphrase")
    account_id = _account(db, other, name="Not yours")

    assert _check(client, account_id, OPENING_PAISE, adjust=True).status_code == 404


def test_the_checks_are_kept_most_recent_first(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _check(client, account_id, OPENING_PAISE - 500_00, adjust=False, on="2026-10-04")
    _check(client, account_id, OPENING_PAISE, adjust=False, on="2026-10-05")

    checks = client.get(BALANCE_CHECKS.format(account_id=account_id)).json()

    assert [check["checked_on"] for check in checks] == ["2026-10-05", "2026-10-04"]
    assert checks[0]["difference_paise"] == 0
    assert checks[1]["difference_paise"] == -500_00
    assert checks[1]["computed_balance_paise"] == OPENING_PAISE


def test_the_check_keeps_every_paise_of_a_large_figure(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    stated = 12_34_567_89

    body = _check(client, account_id, stated, adjust=True).json()

    assert body["difference_paise"] == stated - OPENING_PAISE
    assert _balance(client, account_id) == stated


def test_a_check_needs_a_date_a_balance_and_a_decision(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    missing_all = client.post(BALANCE_CHECKS.format(account_id=account_id), json={})
    no_decision = client.post(
        BALANCE_CHECKS.format(account_id=account_id),
        json={"on": CHECKED_ON, "stated_balance_paise": 1},
    )

    assert missing_all.status_code == 422
    assert no_decision.status_code == 422


def test_the_share_of_spending_counts_only_expenses(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    other_id = _account(db, user, name="Central Bank")
    _expense(client, account_id, 20_00_000, on="2026-10-02")  # ₹20,000 spent
    _expense(client, account_id, 5_00_000, on="2026-10-03")
    client.post(
        "/api/v1/transactions",
        json={
            "kind": "income",
            "account_id": account_id,
            "amount_paise": 1_00_000_00,
            "transaction_date": "2026-10-04",
        },
    )
    client.post(
        "/api/v1/transactions",
        json={
            "kind": "transfer",
            "from_account_id": account_id,
            "to_account_id": other_id,
            "amount_paise": 50_00_000,
            "transaction_date": "2026-10-04",
        },
    )
    _check(client, account_id, OPENING_PAISE, adjust=True)

    share = _share(client, account_id, "2026-10-01")

    # ₹25,000 of spending was written off, so the whole month's spend is unaccounted.
    assert share["spend_paise"] == 25_00_000
    assert share["adjustments_paise"] == 25_00_000
    assert share["share_percent"] == 100


def test_a_share_of_a_month_with_no_spending_is_zero(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    share = _share(client, account_id, "2026-10-01")

    assert share["spend_paise"] == 0
    assert share["adjustments_paise"] == 0
    assert share["share_percent"] == 0


def test_last_months_spending_is_not_counted_this_month(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _expense(client, account_id, 9_00_000, on="2026-09-30")

    september = _share(client, account_id, "2026-09-01")
    october = _share(client, account_id, "2026-10-01")

    assert september["spend_paise"] == 9_00_000
    assert october["spend_paise"] == 0


# --- writing off a check that was made earlier ---


def test_a_recorded_check_can_be_written_off_later(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    stated = OPENING_PAISE - 500_00
    check = _check(client, account_id, stated, adjust=False).json()
    assert check["adjustment_transaction_id"] is None

    response = _adjust(client, account_id, check["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["difference_paise"] == -500_00
    assert body["adjustment_transaction_id"] is not None
    assert _balance(client, account_id) == stated
    # The write-off is dated the day the balance was checked, not the day it was
    # written off, so the ledger reads as it did when the user looked.
    written_off = client.get("/api/v1/transactions?kind=adjustment").json()
    assert [t["transaction_date"] for t in written_off] == [CHECKED_ON]
    assert written_off[0]["note"] is None


def test_a_check_cannot_be_written_off_twice(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    check = _check(client, account_id, OPENING_PAISE - 500_00, adjust=False).json()
    _adjust(client, account_id, check["id"])

    again = _adjust(client, account_id, check["id"])

    assert again.status_code == 409
    assert "already" in again.json()["detail"]
    assert len(client.get("/api/v1/transactions?kind=adjustment").json()) == 1
    assert _balance(client, account_id) == OPENING_PAISE - 500_00


def test_a_matching_check_has_nothing_to_write_off(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    check = _check(client, account_id, OPENING_PAISE, adjust=False).json()

    response = _adjust(client, account_id, check["id"])

    assert response.status_code == 409
    assert "nothing to write off" in response.json()["detail"]
    assert client.get("/api/v1/transactions").json() == []


def test_only_your_own_checks_can_be_written_off(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    other = create_user(db, "someone@example.com", "another-passphrase")
    other_account_id = _account(db, other, name="Not yours")
    other_check = _check(client, other_account_id, OPENING_PAISE - 500_00, adjust=False)
    assert other_check.status_code == 404

    assert _adjust(client, 1, 1).status_code == 404
    assert _adjust(client, 999, 1).status_code == 404


def test_writing_off_a_check_that_is_not_there_answers_404(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    assert _adjust(client, account_id, 999).status_code == 404
