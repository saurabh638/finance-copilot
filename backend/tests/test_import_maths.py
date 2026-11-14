"""What an imported row *is*, and whether a statement adds up.

Both are pure work over values, so they are tested here rather than through a
database or a file: the rest of the import path is only plumbing around these two
answers.
"""

import re
from datetime import date

import pytest

from app.core.imports import (
    fingerprint,
    normalise_narration,
    reconcile,
)

ACCOUNT = 7
DAY = date(2026, 9, 14)


def test_a_narration_is_folded_to_its_words() -> None:
    assert normalise_narration("  UPI/  Swiggy   ORDER \n") == "upi/ swiggy order"


def test_the_same_words_in_another_case_are_the_same_words() -> None:
    assert normalise_narration("SWIGGY") == normalise_narration("swiggy")


def test_a_narration_that_is_only_space_has_no_words() -> None:
    assert normalise_narration("   \t\n ") == ""


def test_a_row_has_one_identity() -> None:
    first = fingerprint(ACCOUNT, DAY, -45_000, "UPI/ Swiggy")
    second = fingerprint(ACCOUNT, DAY, -45_000, "UPI/ Swiggy")

    assert first == second
    assert re.fullmatch(r"[0-9a-f]{64}", first) is not None


def test_case_and_spacing_do_not_make_a_new_row() -> None:
    assert fingerprint(ACCOUNT, DAY, -45_000, "UPI/ Swiggy") == fingerprint(
        ACCOUNT, DAY, -45_000, "  upi/   SWIGGY "
    )


@pytest.mark.parametrize(
    "other",
    [
        fingerprint(ACCOUNT + 1, DAY, -45_000, "UPI/ Swiggy"),
        fingerprint(ACCOUNT, date(2026, 9, 15), -45_000, "UPI/ Swiggy"),
        fingerprint(ACCOUNT, DAY, -45_001, "UPI/ Swiggy"),
        fingerprint(ACCOUNT, DAY, 45_000, "UPI/ Swiggy"),
        fingerprint(ACCOUNT, DAY, -45_000, "UPI/ Zomato"),
    ],
    ids=["another account", "another day", "one paise", "the other direction", "another shop"],
)
def test_anything_that_changes_a_row_changes_its_identity(other: str) -> None:
    assert other != fingerprint(ACCOUNT, DAY, -45_000, "UPI/ Swiggy")


def test_a_statement_that_adds_up_has_no_difference() -> None:
    result = reconcile(opening_paise=1_00_000, rows_paise=-25_000, closing_paise=75_000)

    assert result.file_difference_paise == 0
    assert result.adds_up


def test_a_statement_one_paise_out_does_not_add_up() -> None:
    result = reconcile(opening_paise=1_00_000, rows_paise=-25_000, closing_paise=75_001)

    assert result.file_difference_paise == -1
    assert not result.adds_up


def test_the_ledger_is_not_asked_when_it_is_not_given() -> None:
    result = reconcile(opening_paise=1_00_000, rows_paise=-25_000, closing_paise=75_000)

    assert result.ledger_difference_paise is None
    assert result.ledger_agrees is None


def test_the_ledger_agrees_when_its_balance_and_the_rows_reach_the_closing_figure() -> None:
    result = reconcile(
        opening_paise=1_00_000,
        rows_paise=-25_000,
        closing_paise=75_000,
        ledger_balance_paise=1_00_000,
    )

    assert result.ledger_difference_paise == 0
    assert result.ledger_agrees is True


def test_the_ledger_disagreeing_does_not_hide_that_the_file_adds_up() -> None:
    # The two checks answer different questions: the file's own arithmetic can be
    # perfect while the ledger is missing movements the statement already has.
    result = reconcile(
        opening_paise=1_00_000,
        rows_paise=-25_000,
        closing_paise=75_000,
        ledger_balance_paise=90_000,
    )

    assert result.adds_up
    assert result.ledger_difference_paise == -10_000
    assert result.ledger_agrees is False


def test_a_card_statement_owed_rather_than_held_is_the_same_arithmetic_negated() -> None:
    # A card prints what is owed, so both the rows and the closing figure are the
    # other way round. Nothing about the check changes.
    result = reconcile(opening_paise=-50_000, rows_paise=-10_000, closing_paise=-60_000)

    assert result.adds_up


def test_a_statement_read_twice_asks_the_ledger_about_nothing() -> None:
    # Every row is already recorded, so the balance should already be the closing
    # figure; counting the rows again would refuse a file that is perfectly fine.
    result = reconcile(
        opening_paise=1_00_000,
        rows_paise=-25_000,
        closing_paise=75_000,
        ledger_balance_paise=75_000,
        rows_the_ledger_is_missing_paise=0,
    )

    assert result.adds_up
    assert result.ledger_agrees is True


def test_only_the_rows_the_ledger_is_missing_count_towards_the_closing_figure() -> None:
    # The file lists two rows, the ledger already holds one of them.
    result = reconcile(
        opening_paise=1_00_000,
        rows_paise=-25_000,
        closing_paise=75_000,
        ledger_balance_paise=87_500,
        rows_the_ledger_is_missing_paise=-12_500,
    )

    assert result.adds_up
    assert result.ledger_agrees is True
