"""What a write-off files itself under.

A write-off is money the ledger cannot explain, so it belongs under the tree's
own names for that. Money short is spending that went unrecorded; money found is
income that went unrecorded. Both have to keep working when the user renames or
removes those names, because a balance check must always be recordable.
"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccountType, CaptureMode, Posting, PostingKind, User
from app.schemas.account import AccountCreate
from app.services.accounts import create_account
from app.services.categories import (
    UNACCOUNTED,
    UNRECORDED_INCOME,
    get_category,
    list_categories,
    remove_category,
    seed_defaults,
    update_category,
)

EMAIL = "owner@example.com"
PASSPHRASE = "s3cret-passphrase"
OPENED = date(2026, 4, 1)
OPENING_PAISE = 1_00_000_00

CHECKS = "/api/v1/accounts/{account_id}/balance-checks"


def _sign_in(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSPHRASE})
    assert response.status_code == 200


def _account(db: Session, user: User, opening_paise: int = OPENING_PAISE) -> int:
    account = create_account(
        db,
        user.id,
        AccountCreate(
            name="SBI",
            type=AccountType.SAVINGS,
            capture_mode=CaptureMode.STATEMENT_IMPORT,
            opening_balance_paise=opening_paise,
            opening_date=OPENED,
        ),
    )
    return account.id


def _check(client: TestClient, account_id: int, stated_paise: int) -> dict[str, object]:
    """State a balance, have the difference written off, and return the write-off."""
    response = client.post(
        CHECKS.format(account_id=account_id),
        json={
            "account_id": account_id,
            "stated_balance_paise": stated_paise,
            "on": "2026-10-05",
            "adjust": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    adjustment_id = body["adjustment_transaction_id"]
    assert isinstance(adjustment_id, int)
    written_off = client.get(f"/api/v1/transactions/{adjustment_id}").json()
    return written_off  # type: ignore[no-any-return]


def _category_id(db: Session, user: User, name: str) -> int:
    return get_category(db, user.id, _named(db, user, name)).id


def _named(db: Session, user: User, name: str) -> int:
    for category in list_categories(db, user.id):
        if category.name == name:
            return category.id
    raise AssertionError(f"{name} is not in the tree")


def test_money_short_is_filed_under_unaccounted_for_spending(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    seed_defaults(db, user.id)

    write_off = _check(client, account_id, OPENING_PAISE - 250_00)

    assert write_off["postings"][0]["category_id"] == _category_id(db, user, UNACCOUNTED)


def test_money_found_is_filed_under_unrecorded_income(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    seed_defaults(db, user.id)

    write_off = _check(client, account_id, OPENING_PAISE + 250_00)

    assert write_off["postings"][0]["category_id"] == _category_id(db, user, UNRECORDED_INCOME)


def test_the_write_off_still_lands_on_the_stated_balance(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    seed_defaults(db, user.id)

    _check(client, account_id, OPENING_PAISE - 250_00)

    balance = client.get(f"/api/v1/accounts/{account_id}/balance").json()
    assert balance["balance_paise"] == OPENING_PAISE - 250_00


def test_a_write_off_is_never_refused_for_want_of_a_name(
    client: TestClient, db: Session, user: User
) -> None:
    """The tree is empty, so there is nothing to file under: record it anyway."""
    _sign_in(client)
    account_id = _account(db, user)

    write_off = _check(client, account_id, OPENING_PAISE - 250_00)

    assert write_off["postings"][0]["category_id"] is None
    posting = db.scalars(select(Posting).where(Posting.kind == PostingKind.ADJUSTMENT)).one()
    assert posting.category_id is None


def test_a_renamed_name_means_the_write_off_goes_unfiled(
    client: TestClient, db: Session, user: User
) -> None:
    """The name is the user's to change, so a renamed one is no longer ours."""
    _sign_in(client)
    account_id = _account(db, user)
    seed_defaults(db, user.id)
    update_category(db, user.id, _named(db, user, UNACCOUNTED), name="Unexplained spending")

    write_off = _check(client, account_id, OPENING_PAISE - 250_00)

    assert write_off["postings"][0]["category_id"] is None


def test_a_removed_name_means_the_write_off_goes_unfiled(
    client: TestClient, db: Session, user: User
) -> None:
    _sign_in(client)
    account_id = _account(db, user)
    seed_defaults(db, user.id)
    remove_category(db, user.id, _named(db, user, UNRECORDED_INCOME))

    write_off = _check(client, account_id, OPENING_PAISE + 250_00)

    assert write_off["postings"][0]["category_id"] is None
