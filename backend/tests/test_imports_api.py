"""Reading a statement in through the API: the preview, the commit, and the undo.

The fixture file totals -549.75, so a statement that opens at ₹1,000.00 closes at
₹450.25. The accounts are set up so the ledger can be made to agree or disagree on
purpose: the interesting refusals are the ones that stop a bad file being written.
"""

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AccountType,
    CaptureMode,
    ImportStatus,
    Transaction,
    TransactionSource,
    User,
)
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.auth import create_user
from app.services.transactions import balance

FIXTURE = Path(__file__).parent / "fixtures" / "generic_statement.csv"
STATEMENT = FIXTURE.read_text()

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
OPENED = date(2026, 4, 1)

# What the fixture adds up to: -450.00 -1250.50 +1250.00 -99.25.
STATEMENT_TOTAL = -54_975
OPENING = 1_00_000
CLOSING = OPENING + STATEMENT_TOTAL

IMPORTS = "/api/v1/imports"


def _sign_in(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})
    assert response.status_code == 200


def _account(db: Session, user: User, name: str = "SBI", opening: int = OPENING) -> int:
    account = create_account(
        db,
        user.id,
        AccountCreate.model_validate(
            {
                "name": name,
                "type": AccountType.SAVINGS,
                "capture_mode": CaptureMode.STATEMENT_IMPORT,
                "opening_balance_paise": opening,
                "opening_date": OPENED,
            }
        ),
    )
    return account.id


def _upload(
    client: TestClient,
    account_id: int,
    *,
    text: str = STATEMENT,
    opening: int | None = OPENING,
    closing: int | None = CLOSING,
    parser: str | None = None,
) -> object:
    fields = {"account_id": str(account_id)}
    if opening is not None:
        fields["opening_paise"] = str(opening)
    if closing is not None:
        fields["closing_paise"] = str(closing)
    if parser is not None:
        fields["parser"] = parser
    return client.post(
        IMPORTS,
        data=fields,
        files={"file": ("statement.csv", text.encode(), "text/csv")},
    )


def test_a_statement_is_read_and_held_without_writing_anything(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = _upload(client, account_id)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "previewed"
    assert body["account_id"] == account_id
    assert body["parser"] == "generic"
    assert body["row_count"] == 4
    assert body["opening_paise"] == OPENING
    assert body["closing_paise"] == CLOSING
    assert len(body["to_add"]) == 4
    assert body["duplicates"] == []
    # Held, not written: the ledger has nothing and the balance has not moved.
    assert db.scalars(select(Transaction)).all() == []
    assert balance(db, user.id, account_id).balance_paise == OPENING


def test_the_rows_carry_their_dates_amounts_and_words(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    body = _upload(client, account_id).json()

    first = body["to_add"][0]
    assert first["posted_on"] == "2026-09-01"
    assert first["value_on"] == "2026-09-01"
    assert first["amount_paise"] == -45_000
    assert first["narration"] == "UPI/ Swiggy"
    assert len(first["fingerprint"]) == 64


def test_a_statement_that_does_not_add_up_is_refused_before_anything_is_stored(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = _upload(client, account_id, closing=CLOSING + 1)

    assert response.status_code == 400
    assert "does not add up" in response.json()["detail"]
    assert db.scalars(select(Transaction)).all() == []


def test_a_statement_the_ledger_disagrees_with_is_refused_and_says_by_how_much(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    # The account really holds ₹2,000.00, so these rows would not reach ₹450.25.
    account_id = _account(db, user, opening=2_00_000)

    response = _upload(client, account_id)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "the ledger holds" in detail
    assert "₹2,000.00" in detail


def test_a_statement_without_balances_is_refused_when_the_request_has_none_either(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = _upload(client, account_id, opening=None, closing=None)

    assert response.status_code == 400
    assert "opened and closed" in response.json()["detail"]


def test_a_reader_that_does_not_exist_is_refused_by_name(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = _upload(client, account_id, parser="sbi_savings")

    assert response.status_code == 400
    assert "sbi_savings" in response.json()["detail"]


def test_a_file_that_is_not_the_layout_is_refused_by_row(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = _upload(client, account_id, text="date,amount,narration\n01/09/2026,-450.00,x\n")

    assert response.status_code == 400
    assert "row 2" in response.json()["detail"]


def test_two_rows_that_cannot_be_told_apart_are_refused(
    client: TestClient, db: Session, user: User
) -> None:
    # The same payment listed twice. Importing one and dropping the other would be a
    # guess, so the file is refused with both row numbers named.
    _sign_in(client)
    account_id = _account(db, user)
    text = (
        "date,amount,narration\n"
        "2026-09-01,-449.75,UPI/ Swiggy\n"
        "2026-09-01,-449.75,UPI/ Swiggy\n"
        "2026-09-02,-100.00,UPI/ Zomato\n"
    )

    response = _upload(client, account_id, text=text, closing=OPENING - 99_950)

    assert response.status_code == 400
    assert "rows 1 and 2" in response.json()["detail"]


def test_committing_writes_the_movements_through_the_ledger(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    batch_id = _upload(client, account_id).json()["id"]

    response = client.post(f"{IMPORTS}/{batch_id}/commit")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "committed"
    assert body["committed_at"] is not None
    assert body["to_add"] == []

    written = list(db.scalars(select(Transaction).order_by(Transaction.transaction_date)))
    assert len(written) == 4
    assert {row.source for row in written} == {TransactionSource.IMPORT}
    assert all(row.import_batch_id == batch_id for row in written)
    assert all(row.fingerprint is not None for row in written)
    assert written[0].posted_date == date(2026, 9, 1)
    assert written[0].raw_narration == "UPI/ Swiggy"
    # No merchant is invented from the narration: naming it is M16's job.
    assert written[0].merchant is None
    assert balance(db, user.id, account_id).balance_paise == CLOSING


def test_a_committed_statement_cannot_be_committed_again(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    batch_id = _upload(client, account_id).json()["id"]
    client.post(f"{IMPORTS}/{batch_id}/commit")

    response = client.post(f"{IMPORTS}/{batch_id}/commit")

    assert response.status_code == 409
    assert "committed" in response.json()["detail"]


def test_reading_the_same_statement_again_finds_it_already_recorded(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    first = _upload(client, account_id).json()["id"]
    client.post(f"{IMPORTS}/{first}/commit")

    second = _upload(client, account_id).json()

    assert second["to_add"] == []
    assert len(second["duplicates"]) == 4
    assert balance(db, user.id, account_id).balance_paise == CLOSING


def test_committing_nothing_new_leaves_the_ledger_alone(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    first = _upload(client, account_id).json()["id"]
    client.post(f"{IMPORTS}/{first}/commit")
    second = _upload(client, account_id).json()["id"]

    response = client.post(f"{IMPORTS}/{second}/commit")

    assert response.status_code == 200
    assert response.json()["status"] == "committed"
    assert len(db.scalars(select(Transaction)).all()) == 4
    assert balance(db, user.id, account_id).balance_paise == CLOSING


def test_reversing_removes_exactly_what_that_statement_wrote(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    batch_id = _upload(client, account_id).json()["id"]
    client.post(f"{IMPORTS}/{batch_id}/commit")

    response = client.post(f"{IMPORTS}/{batch_id}/reverse")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "reversed"
    assert body["reversed_at"] is not None
    assert balance(db, user.id, account_id).balance_paise == OPENING
    live = db.scalars(select(Transaction).where(Transaction.deleted_at.is_(None))).all()
    assert live == []


def test_a_reversed_statement_can_be_read_again(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    batch_id = _upload(client, account_id).json()["id"]
    client.post(f"{IMPORTS}/{batch_id}/commit")
    client.post(f"{IMPORTS}/{batch_id}/reverse")

    again = _upload(client, account_id).json()

    assert len(again["to_add"]) == 4
    assert again["duplicates"] == []


def test_a_statement_cannot_be_reversed_twice(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    batch_id = _upload(client, account_id).json()["id"]

    assert client.post(f"{IMPORTS}/{batch_id}/reverse").status_code == 200
    twice = client.post(f"{IMPORTS}/{batch_id}/reverse")

    assert twice.status_code == 409
    assert "already been reversed" in twice.json()["detail"]


def test_a_preview_that_was_never_committed_can_be_put_away(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    batch_id = _upload(client, account_id).json()["id"]

    response = client.post(f"{IMPORTS}/{batch_id}/reverse")

    assert response.status_code == 200
    assert response.json()["status"] == "reversed"
    assert db.scalars(select(Transaction)).all() == []


def test_the_statements_are_listed_newest_first(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    _upload(client, account_id)
    second = _upload(client, account_id).json()["id"]

    listed = client.get(IMPORTS).json()

    assert [row["id"] for row in listed] == [second, second - 1]


def test_one_statement_can_be_read_back(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    batch_id = _upload(client, account_id).json()["id"]

    body = client.get(f"{IMPORTS}/{batch_id}").json()

    assert body["id"] == batch_id
    assert len(body["to_add"]) == 4


def test_a_statement_belongs_to_the_account_it_was_read_for(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = _upload(client, account_id + 999)

    assert response.status_code == 404


def test_another_users_statement_is_invisible(client: TestClient, db: Session, user: User) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    batch_id = _upload(client, account_id).json()["id"]

    create_user(db, "someone@example.com", "another-passphrase")
    client.post("/api/v1/auth/logout")
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": "someone@example.com", "password": "another-passphrase"},
    )
    assert signed_in.status_code == 200

    assert client.get(f"{IMPORTS}/{batch_id}").status_code == 404
    assert client.get(IMPORTS).json() == []
    assert client.post(f"{IMPORTS}/{batch_id}/commit").status_code == 404
    assert client.post(f"{IMPORTS}/{batch_id}/reverse").status_code == 404


def test_removing_one_imported_movement_offers_that_row_again(
    client: TestClient, db: Session, user: User
) -> None:
    # The fingerprint index is partial and live-only, so deleting a movement releases
    # exactly its row: the next reading of the same statement offers it back.
    _sign_in(client)
    account_id = _account(db, user)
    batch_id = _upload(client, account_id).json()["id"]
    client.post(f"{IMPORTS}/{batch_id}/commit")

    first = db.scalars(select(Transaction).order_by(Transaction.transaction_date)).first()
    assert first is not None
    client.delete(f"/api/v1/transactions/{first.id}")

    again = _upload(client, account_id).json()

    assert len(again["to_add"]) == 1
    assert again["to_add"][0]["narration"] == "UPI/ Swiggy"


def test_uploading_a_file_that_is_not_text_is_refused(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    response = client.post(
        IMPORTS,
        data={"account_id": str(account_id), "opening_paise": "0", "closing_paise": "0"},
        files={"file": ("statement.csv", b"\xff\xfe\x00binary", "text/csv")},
    )

    assert response.status_code == 400
    assert "not UTF-8" in response.json()["detail"]


@pytest.mark.parametrize("path", [IMPORTS, f"{IMPORTS}/1/commit", f"{IMPORTS}/1/reverse"])
def test_every_import_route_needs_a_session(client: TestClient, path: str) -> None:
    assert client.post(path).status_code == 401


def test_the_status_of_a_batch_is_the_enums_own(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)

    body = _upload(client, account_id).json()

    assert body["status"] == ImportStatus.PREVIEWED.value
