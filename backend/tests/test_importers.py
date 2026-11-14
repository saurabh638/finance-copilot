"""Reading a plain statement, and refusing the files that are not one.

The framework's own reader is tested against a fixture on disk as well as against
text written here, so a change to how files are read meets the same file every time.
"""

from datetime import date
from pathlib import Path

import pytest

from app.importers.base import Side, StatementError, in_ledger_terms
from app.importers.generic import GenericCsvParser

FIXTURE = Path(__file__).parent / "fixtures" / "generic_statement.csv"

HEADER = "date,amount,narration\n"


def read(text: str) -> object:
    return GenericCsvParser().read(text)


def test_a_statement_is_read_row_by_row() -> None:
    statement = GenericCsvParser().read(FIXTURE.read_text())

    assert [(row.posted_on, row.amount_paise) for row in statement.rows] == [
        (date(2026, 9, 1), -45_000),
        (date(2026, 9, 3), -1_25_050),
        (date(2026, 9, 7), 1_25_000),
        (date(2026, 9, 12), -9_925),
    ]


def test_the_narration_is_kept_as_the_file_wrote_it() -> None:
    statement = GenericCsvParser().read(FIXTURE.read_text())

    assert statement.rows[0].narration == "UPI/ Swiggy"


def test_the_two_dates_are_the_same_when_a_file_has_only_one() -> None:
    statement = GenericCsvParser().read(FIXTURE.read_text())

    assert statement.rows[0].posted_on == statement.rows[0].value_on


def test_a_plain_file_offers_no_balances() -> None:
    statement = GenericCsvParser().read(FIXTURE.read_text())

    assert statement.opening_paise is None
    assert statement.closing_paise is None


def test_the_columns_may_be_in_any_order() -> None:
    text = "narration,amount,date\nUPI/ Swiggy,-450.00,2026-09-01\n"

    statement = GenericCsvParser().read(text)

    assert statement.rows[0].narration == "UPI/ Swiggy"
    assert statement.rows[0].amount_paise == -45_000


def test_a_comma_inside_a_narration_is_part_of_it() -> None:
    text = HEADER + '2026-09-01,-450.00,"SWIGGY, BANGALORE"\n'

    statement = GenericCsvParser().read(text)

    assert statement.rows[0].narration == "SWIGGY, BANGALORE"


def test_a_blank_line_is_not_a_row() -> None:
    text = HEADER + "2026-09-01,-450.00,UPI/ Swiggy\n\n2026-09-02,-100.00,UPI/ Zomato\n"

    statement = GenericCsvParser().read(text)

    assert len(statement.rows) == 2


def test_a_file_with_no_rows_is_refused() -> None:
    with pytest.raises(StatementError, match="no rows"):
        read(HEADER)


def test_a_file_without_the_columns_is_refused_and_says_which_is_missing() -> None:
    with pytest.raises(StatementError, match="no amount"):
        read("date,narration\n2026-09-01,UPI/ Swiggy\n")


def test_a_row_that_is_not_a_date_is_refused_by_its_number() -> None:
    with pytest.raises(StatementError, match="row 2"):
        read(HEADER + "01/09/2026,-450.00,UPI/ Swiggy\n")


def test_a_row_that_is_not_an_amount_is_refused_by_its_number() -> None:
    with pytest.raises(StatementError, match="row 3"):
        read(HEADER + "2026-09-01,-450.00,UPI/ Swiggy\n2026-09-02,four hundred,UPI/ Zomato\n")


def test_a_row_of_nothing_is_refused() -> None:
    with pytest.raises(StatementError, match="not a movement"):
        read(HEADER + "2026-09-01,0.00,Something free\n")


def test_a_statement_that_prints_what_is_owed_is_the_other_way_round() -> None:
    text = HEADER + "2026-09-01,-450.00,UPI/ Swiggy\n"

    statement = GenericCsvParser(side=Side.OWED).read(text)

    assert statement.rows[0].amount_paise == 45_000


@pytest.mark.parametrize(
    ("paise", "side", "expected"),
    [
        (-45_000, Side.HELD, -45_000),
        (45_000, Side.HELD, 45_000),
        (-45_000, Side.OWED, 45_000),
        (45_000, Side.OWED, -45_000),
    ],
)
def test_a_figure_is_turned_into_the_ledgers_terms_once(
    paise: int, side: Side, expected: int
) -> None:
    assert in_ledger_terms(paise, side) == expected
