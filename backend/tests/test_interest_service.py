"""Tests for app.services.interest, against the real test database.

The promises being checked are the ones about money: which periods are proposed,
what each one earned, that a proposal is a snapshot rather than a running figure,
and that confirming it posts exactly one interest posting for the figure the user
says the bank paid.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    AccountType,
    CaptureMode,
    InterestCredit,
    Posting,
    PostingKind,
    RateFrequency,
    User,
)
from app.schemas.account import AccountCreate
from app.schemas.interest_rate import InterestRateCreate
from app.services.accounts import AccountNotFoundError, create_account
from app.services.auth import create_user
from app.services.categories import spend_by_category
from app.services.interest import (
    InterestConflictError,
    InterestNotFoundError,
    InvalidInterestError,
    confirm,
    drop,
    history,
    proposals,
    propose,
    summary,
)
from app.services.interest_rates import create_rate
from app.services.transactions import balance, record_expense

OPENED = date(2026, 4, 1)
LAKH = 1_00_000_00  # ₹1,00,000.00
SEVEN_ONE = "7.1"

# Hand-worked from the stated convention: ₹1,00,000 at 7.1% is 710,000 paise a
# year, so a day is 710,000/365 and a 31-day month is 710,000 x 31/365.
DAY_PAISE = 1_945
HALF_OCTOBER = 29_178  # 15 days
LATE_OCTOBER_AT_8 = 35_068  # 16 days at 8%
OCTOBER = 60_301  # 31 days
A_QUARTER = 178_959  # 92 days, October to December
SEVENTEEN_DAYS = 33_068  # 15 to 31 October
SMALLER_BALANCE = 24_899  # 16 days on ₹80,000
NOVEMBER = 58_708  # 30 days on the lakh plus October's credit
NOVEMBER_AT_THE_BANK = 58_709  # the same, after a ₹60,500 credit


def _account(db: Session, user: User, opening_paise: int = LAKH) -> Account:
    return create_account(
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


def _rate(
    db: Session,
    user: User,
    account: Account,
    *,
    rate: str = SEVEN_ONE,
    from_date: date,
    frequency: RateFrequency = RateFrequency.MONTHLY,
) -> None:
    create_rate(
        db,
        user.id,
        account.id,
        InterestRateCreate(
            rate=Decimal(rate),
            from_date=from_date,
            frequency=frequency,
        ),
    )


def _propose(db: Session, user: User, account: Account, through: date) -> list[object]:
    return propose(db, user.id, account.id, through=through)


def test_a_month_is_proposed_once_the_month_has_ended(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))

    assert _propose(db, user, account, date(2026, 10, 30)) == []

    made = _propose(db, user, account, date(2026, 10, 31))

    assert len(made) == 1
    assert (made[0].period_start, made[0].period_end) == (date(2026, 10, 1), date(2026, 10, 31))
    assert made[0].computed_paise == OCTOBER
    assert made[0].rate_percent == Decimal("7.1000")
    assert made[0].credited_paise is None
    assert made[0].transaction_id is None


def test_a_quarter_is_proposed_once_the_quarter_has_ended(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1), frequency=RateFrequency.QUARTERLY)

    made = _propose(db, user, account, date(2026, 12, 31))

    assert [(row.period_start, row.period_end, row.computed_paise) for row in made] == [
        (date(2026, 10, 1), date(2026, 12, 31), A_QUARTER)
    ]


def test_proposing_twice_proposes_once(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    _propose(db, user, account, date(2026, 10, 31))

    assert _propose(db, user, account, date(2026, 10, 31)) == []
    assert db.scalars(select(InterestCredit)).all() != []


def test_a_rate_change_makes_two_proposals_that_cover_the_month(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    _rate(db, user, account, rate="8", from_date=date(2026, 10, 16))

    made = _propose(db, user, account, date(2026, 10, 31))

    assert [(row.period_start, row.period_end, row.computed_paise) for row in made] == [
        (date(2026, 10, 1), date(2026, 10, 15), HALF_OCTOBER),
        (date(2026, 10, 16), date(2026, 10, 31), LATE_OCTOBER_AT_8),
    ]
    days = sum((row.period_end - row.period_start).days + 1 for row in made)
    assert days == 31


def test_a_movement_changes_what_a_proposal_earns(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    # ₹20,000 leaves on the 16th, so the month earns on the full lakh for 15 days
    # and on ₹80,000 for the rest — and it is still one proposal, because the bank
    # credits one figure for the month rather than one per movement.
    record_expense(db, user.id, account.id, 20_000_00, date(2026, 10, 16))

    made = _propose(db, user, account, date(2026, 10, 31))

    assert len(made) == 1
    assert made[0].computed_paise == HALF_OCTOBER + SMALLER_BALANCE


def test_a_month_with_several_movements_is_still_one_proposal(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    record_expense(db, user.id, account.id, 500_00, date(2026, 10, 6))
    record_expense(db, user.id, account.id, 250_00, date(2026, 10, 6))
    record_expense(db, user.id, account.id, 2_500_00, date(2026, 10, 6))

    made = _propose(db, user, account, date(2026, 10, 31))

    assert [(row.period_start, row.period_end) for row in made] == [
        (date(2026, 10, 1), date(2026, 10, 31))
    ]


def test_a_daily_rate_proposes_every_finished_day(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1), frequency=RateFrequency.DAILY)

    made = _propose(db, user, account, date(2026, 10, 3))

    assert [(row.period_start, row.computed_paise) for row in made] == [
        (date(2026, 10, 1), DAY_PAISE),
        (date(2026, 10, 2), DAY_PAISE),
        (date(2026, 10, 3), DAY_PAISE),
    ]


def test_the_first_period_starts_the_day_the_rate_does(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 15))

    made = _propose(db, user, account, date(2026, 10, 31))

    # From the 15th to the 31st is 17 days.
    assert [(row.period_start, row.computed_paise) for row in made] == [
        (date(2026, 10, 15), SEVENTEEN_DAYS)
    ]


def test_an_empty_account_earns_nothing_and_proposes_nothing(db: Session, user: User) -> None:
    account = _account(db, user, opening_paise=0)
    _rate(db, user, account, from_date=date(2026, 10, 1))

    assert _propose(db, user, account, date(2026, 10, 31)) == []


def test_an_account_with_no_rate_proposes_nothing(db: Session, user: User) -> None:
    account = _account(db, user)

    assert _propose(db, user, account, date(2026, 10, 31)) == []


def test_a_yearly_rate_is_refused_loudly(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 1, 1), frequency=RateFrequency.YEARLY)

    with pytest.raises(InvalidInterestError):
        _propose(db, user, account, date(2026, 12, 31))


def test_confirming_posts_one_interest_posting_for_the_proposed_figure(
    db: Session, user: User
) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (proposal,) = _propose(db, user, account, date(2026, 10, 31))

    confirmed = confirm(db, user.id, account.id, proposal.id, on=date(2026, 11, 2))

    assert confirmed.credited_paise == OCTOBER
    assert confirmed.confirmed_on == date(2026, 11, 2)

    (posting,) = db.scalars(select(Posting))
    assert posting.kind is PostingKind.INTEREST
    assert posting.amount_paise == OCTOBER
    assert posting.category_id is None

    transaction = posting.transaction_id
    assert confirmed.transaction_id == transaction
    assert balance(db, user.id, account.id).balance_paise == LAKH + OCTOBER


def test_confirming_posts_the_banks_figure_and_keeps_both(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (proposal,) = _propose(db, user, account, date(2026, 10, 31))

    confirmed = confirm(
        db, user.id, account.id, proposal.id, credited_paise=60_500, on=date(2026, 11, 2)
    )

    # The ledger's own figure is kept beside the bank's, so the convention can be
    # seen to be wrong rather than being overwritten.
    assert confirmed.computed_paise == OCTOBER
    assert confirmed.credited_paise == 60_500
    assert balance(db, user.id, account.id).balance_paise == LAKH + 60_500


def test_confirming_a_period_twice_is_refused(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (proposal,) = _propose(db, user, account, date(2026, 10, 31))
    confirm(db, user.id, account.id, proposal.id, on=date(2026, 11, 2))

    with pytest.raises(InterestConflictError):
        confirm(db, user.id, account.id, proposal.id, on=date(2026, 11, 3))

    assert len(db.scalars(select(Posting)).all()) == 1


def test_an_interest_credit_cannot_be_for_nothing(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (proposal,) = _propose(db, user, account, date(2026, 10, 31))

    with pytest.raises(InvalidInterestError):
        confirm(db, user.id, account.id, proposal.id, credited_paise=0, on=date(2026, 11, 2))


def test_a_confirmed_period_is_not_proposed_again(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (proposal,) = _propose(db, user, account, date(2026, 10, 31))
    confirm(db, user.id, account.id, proposal.id, on=date(2026, 11, 2))

    made = _propose(db, user, account, date(2026, 11, 30))

    # Only November is new: October's money is already on the ledger, and it is
    # part of the balance November earns on.
    assert [(row.period_start, row.period_end) for row in made] == [
        (date(2026, 11, 1), date(2026, 11, 30))
    ]
    assert len(db.scalars(select(InterestCredit)).all()) == 2


def test_a_credited_period_cannot_be_dropped(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (proposal,) = _propose(db, user, account, date(2026, 10, 31))
    confirm(db, user.id, account.id, proposal.id, on=date(2026, 11, 2))

    with pytest.raises(InterestConflictError):
        drop(db, user.id, account.id, proposal.id)


def test_a_dropped_proposal_can_be_worked_out_again(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (proposal,) = _propose(db, user, account, date(2026, 10, 31))

    drop(db, user.id, account.id, proposal.id)

    assert proposals(db, user.id, account.id) == []
    assert [row.computed_paise for row in _propose(db, user, account, date(2026, 10, 31))] == [
        OCTOBER
    ]


def test_interest_is_not_spending(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (proposal,) = _propose(db, user, account, date(2026, 10, 31))
    confirm(db, user.id, account.id, proposal.id, on=date(2026, 11, 2))

    report = spend_by_category(db, user.id, date(2026, 10, 1), date(2026, 12, 31))

    assert report.total_paise == 0
    assert report.uncategorised_paise == 0


def test_interest_that_was_credited_earns_interest_in_the_next_period(
    db: Session, user: User
) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (october,) = _propose(db, user, account, date(2026, 10, 31))
    confirm(db, user.id, account.id, october.id, on=date(2026, 11, 2))

    (november,) = _propose(db, user, account, date(2026, 11, 30))

    # 30 days on the lakh plus October's credit.
    assert november.computed_paise == NOVEMBER


def test_a_movement_added_later_does_not_rewrite_a_proposal(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (proposal,) = _propose(db, user, account, date(2026, 10, 31))

    record_expense(db, user.id, account.id, 50_000_00, date(2026, 10, 20))

    assert proposals(db, user.id, account.id)[0].computed_paise == proposal.computed_paise


def test_the_summary_separates_what_is_promised_from_what_is_credited(
    db: Session, user: User
) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (october,) = _propose(db, user, account, date(2026, 10, 31))
    confirm(db, user.id, account.id, october.id, credited_paise=60_500, on=date(2026, 11, 2))
    _propose(db, user, account, date(2026, 11, 30))

    found = summary(db, user.id, account.id)

    assert found.credited_paise == 60_500
    assert found.uncredited_paise == NOVEMBER_AT_THE_BANK
    assert [row.period_start for row in found.proposals] == [date(2026, 11, 1)]
    assert [row.period_start for row in found.history] == [date(2026, 10, 1)]


def test_the_history_is_newest_first(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (october,) = _propose(db, user, account, date(2026, 10, 31))
    confirm(db, user.id, account.id, october.id, on=date(2026, 11, 2))
    (november,) = _propose(db, user, account, date(2026, 11, 30))
    confirm(db, user.id, account.id, november.id, on=date(2026, 12, 1))

    assert [row.period_start for row in history(db, user.id, account.id)] == [
        date(2026, 11, 1),
        date(2026, 10, 1),
    ]


def test_another_users_interest_is_invisible(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))
    (proposal,) = _propose(db, user, account, date(2026, 10, 31))
    other = create_user(db, "someone@example.com", "another-passphrase")

    # The account is not theirs, so nothing about it is theirs either.
    for call in (
        lambda: proposals(db, other.id, account.id),
        lambda: summary(db, other.id, account.id),
        lambda: confirm(db, other.id, account.id, proposal.id, on=date(2026, 11, 2)),
        lambda: drop(db, other.id, account.id, proposal.id),
    ):
        with pytest.raises(AccountNotFoundError):
            call()


def test_a_period_that_does_not_exist_is_refused(db: Session, user: User) -> None:
    account = _account(db, user)
    _rate(db, user, account, from_date=date(2026, 10, 1))

    with pytest.raises(InterestNotFoundError):
        confirm(db, user.id, account.id, 999_999, on=date(2026, 11, 2))

    with pytest.raises(InterestNotFoundError):
        drop(db, user.id, account.id, 999_999)
