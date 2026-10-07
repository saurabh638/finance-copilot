"""The one job that runs without being asked, and the code it shares with the CLI.

Interest has to be worked out even on a day nobody opens the app, so it runs on a
timer inside the backend process: that is what ARCHITECTURE.md asks for, and at
this size a queue would be a second thing to run and watch.

The timer's whole body is `accrue_all`, which the `accrue` CLI command calls too.
So the thing that runs at one in the morning is the same thing that can be run by
hand before the gate, and the same thing the tests call directly: no logic lives
in the scheduler itself.
"""

from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Account, InterestRate
from app.services.interest import propose

JOB_ID = "accrue-interest"

# One in the morning: a bank's day has closed, and nobody is halfway through
# recording something that would change what the balance was.
JOB_HOUR = 1


def accounts_with_a_rate() -> list[tuple[int, int]]:
    """Every live account that has a live rate, as (account id, owner id).

    A rate record is what makes interest possible, so an account without one is
    not the job's business and is left alone.
    """
    with SessionLocal() as db:
        rows = db.execute(
            select(InterestRate.account_id, Account.user_id)
            .join(Account, Account.id == InterestRate.account_id)
            .where(
                InterestRate.deleted_at.is_(None),
                Account.deleted_at.is_(None),
            )
            .distinct()
        ).all()
    return [(account_id, user_id) for account_id, user_id in rows]


def accrue_all(*, through: date | None = None) -> int:
    """Work out interest for every account that has a rate, up to a day.

    Returns how many periods were proposed, which is what makes the result worth
    printing. Running it twice proposes nothing new, so a restart, a reload or two
    schedulers at once cannot double up.
    """
    day = date.today() if through is None else through
    made = 0

    for account_id, user_id in accounts_with_a_rate():
        with SessionLocal() as db:
            made += len(propose(db, user_id, account_id, through=day))
    return made


def build_scheduler() -> BackgroundScheduler:
    """A scheduler with the daily job registered, and not yet started."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        accrue_all,
        trigger="cron",
        hour=JOB_HOUR,
        id=JOB_ID,
        replace_existing=True,
        # The job may well take longer than its own trigger interval on a slow
        # morning; running two copies of it would be pointless work.
        max_instances=1,
        coalesce=True,
    )
    return scheduler


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler | None:
    """Start the timer, unless the settings say not to.

    Tests switch it off, because a suite that starts a background job has a second
    writer to a database it is trying to keep still.
    """
    global _scheduler

    if not get_settings().scheduler_enabled:
        return None

    if _scheduler is None:
        _scheduler = build_scheduler()
        _scheduler.start()
    return _scheduler


def shutdown_scheduler() -> None:
    """Stop the timer if it is running. Safe to call when it never started."""
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
