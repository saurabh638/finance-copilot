"""The daily job, and the command that runs the same thing by hand.

The timer itself is only a trigger: what it calls is `accrue_all`, which the CLI
calls too and these tests call directly. So the tests check the work, and then
check that a scheduler could be built to do it - not that a background thread ran.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import cli
from app.config import get_settings
from app.jobs.scheduler import (
    JOB_HOUR,
    JOB_ID,
    accounts_with_a_rate,
    accrue_all,
    build_scheduler,
    shutdown_scheduler,
    start_scheduler,
)
from app.models import Account, AccountType, CaptureMode, InterestCredit, RateFrequency, User
from app.schemas.account import AccountCreate
from app.schemas.interest_rate import InterestRateCreate
from app.services.accounts import create_account
from app.services.interest_rates import create_rate, list_rates, soft_delete_rate

OPENED = date(2026, 4, 1)
LAKH = 1_00_000_00
OCTOBER = 60_301  # ₹1,00,000 at 7.1% for 31 days, hand-worked


def _account(db: Session, user: User) -> Account:
    return create_account(
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


def _rate(db: Session, user: User, account: Account) -> None:
    create_rate(
        db,
        user.id,
        account.id,
        InterestRateCreate(
            rate=Decimal("7.1"),
            from_date=date(2026, 10, 1),
            frequency=RateFrequency.MONTHLY,
        ),
    )


def test_the_job_works_out_every_finished_period(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account)

    made = accrue_all(through=date(2026, 10, 31))

    assert made == 1
    (row,) = db.scalars(select(InterestCredit)).all()
    assert row.computed_paise == OCTOBER


def test_the_job_running_twice_works_out_nothing_new(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account)
    accrue_all(through=date(2026, 10, 31))

    assert accrue_all(through=date(2026, 10, 31)) == 0


def test_the_job_leaves_an_account_with_no_rate_alone(db: Session, user: User) -> None:
    _account(db, user)

    assert accrue_all(through=date(2026, 10, 31)) == 0
    assert accounts_with_a_rate() == []


def test_the_job_does_not_touch_a_removed_rate(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account)

    (rate,) = list_rates(db, user.id, account.id, limit=10, offset=0)
    soft_delete_rate(db, user.id, account.id, rate.id)

    assert accrue_all(through=date(2026, 10, 31)) == 0


def test_the_scheduler_carries_the_daily_job_and_is_not_started() -> None:
    scheduler = build_scheduler()

    job = scheduler.get_job(JOB_ID)

    assert job is not None
    assert job.func is accrue_all
    assert JOB_HOUR == 1
    assert scheduler.running is False


def test_the_scheduler_stays_out_of_the_way_when_it_is_switched_off() -> None:
    settings = get_settings()

    assert settings.scheduler_enabled is False
    assert start_scheduler() is None
    # Safe when it never started.
    shutdown_scheduler()


def test_the_scheduler_really_starts_when_it_is_switched_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    get_settings.cache_clear()

    try:
        started = start_scheduler()

        assert started is not None
        assert started.running is True
        job = started.get_job(JOB_ID)
        assert job is not None
        assert job.next_run_time is not None
    finally:
        shutdown_scheduler()
        # The environment is put back and the cache cleared, so the rest of the
        # suite sees the settings it started with, timer off.
        get_settings.cache_clear()


def test_the_accrue_command_works_interest_out_by_hand(
    db: Session, user: User, capsys: pytest.CaptureFixture[str]
) -> None:
    account = _account(db, user)
    _rate(db, user, account)

    code = cli.main(["accrue", "--through", "2026-10-31"])

    assert code == 0
    assert "Worked out 1 period" in capsys.readouterr().out
    assert db.scalars(select(InterestCredit)).one().computed_paise == OCTOBER

    assert cli.main(["accrue", "--through", "2026-10-31"]) == 0
    assert "Nothing new to work out." in capsys.readouterr().out
