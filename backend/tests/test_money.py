"""Tests for app.core.money.

Written before the implementation (CODING_STANDARDS section 5: money code is
test-first). These express the intended behaviour, not the current output.
"""

import pytest

from app.core.money import (
    InvalidMoneyError,
    add_paise,
    format_paise,
    negate_paise,
    parse_paise,
    split_paise,
    subtract_paise,
)


@pytest.mark.parametrize(
    ("text", "expected_paise"),
    [
        ("0", 0),
        ("0.00", 0),
        ("0.01", 1),
        ("500", 50_000),
        ("500.5", 50_050),
        ("500.50", 50_050),
        ("₹500", 50_000),
        ("₹ 500", 50_000),
        ("  500  ", 50_000),
        ("1,23,456.78", 12_345_678),
        ("₹1,23,456.78", 12_345_678),
        ("5,00,000", 50_000_000),
        ("-500", -50_000),
        ("-₹1,000", -100_000),
        ("- ₹1,000", -100_000),
        ("-0.01", -1),
    ],
)
def test_parse_paise_reads_text_into_integer_paise(text: str, expected_paise: int) -> None:
    assert parse_paise(text) == expected_paise


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "abc",
        "500.999",  # more than two decimals: reject, never round silently
        "1,2,3",  # malformed grouping
        "500,",
        ",500",
        "500.",
        ".50",
        "1.2.3",
        "₹",
        "-",
        "+500",
        "Rs 500",  # only the rupee symbol is accepted
        "INR 500",
        "5 00",
    ],
)
def test_parse_paise_rejects_invalid_text(text: str) -> None:
    with pytest.raises(InvalidMoneyError):
        parse_paise(text)


def test_parse_paise_rejects_a_float_argument() -> None:
    """Money is never parsed from a float, only from text."""
    with pytest.raises(TypeError):
        parse_paise(500.5)  # type: ignore[arg-type]  # deliberately a float


@pytest.mark.parametrize(
    ("paise", "expected"),
    [
        (0, "₹0.00"),
        (1, "₹0.01"),
        (50, "₹0.50"),
        (100, "₹1.00"),
        (50_000, "₹500.00"),
        (12_345_678, "₹1,23,456.78"),
        (100_000_000, "₹10,00,000.00"),  # ten lakh
        (1_000_000_000, "₹1,00,00,000.00"),  # one crore
        (-50_000, "-₹500.00"),
        (-12_345_678, "-₹1,23,456.78"),
    ],
)
def test_format_paise_uses_indian_grouping(paise: int, expected: str) -> None:
    assert format_paise(paise) == expected


def test_parse_paise_at_lakh_and_crore_boundaries() -> None:
    assert parse_paise("1,00,000") == 10_000_000  # one lakh
    assert parse_paise("1,00,00,000") == 1_000_000_000  # one crore
    assert parse_paise("99,99,999") == 999_999_900
    assert format_paise(10_000_000) == "₹1,00,000.00"
    assert format_paise(1_000_000_000) == "₹1,00,00,000.00"


def test_format_then_parse_round_trips() -> None:
    for paise in (0, 1, 50, 100, 50_000, 12_345_678, -50_000, 1_000_000_000):
        assert parse_paise(format_paise(paise)) == paise


def test_add_paise_sums_integers_only() -> None:
    assert add_paise(100, 250) == 350
    assert add_paise(100, -50) == 50
    assert add_paise() == 0
    assert isinstance(add_paise(1, 2), int)


def test_subtract_paise_can_go_negative() -> None:
    assert subtract_paise(500, 200) == 300
    assert subtract_paise(200, 500) == -300


def test_negate_paise_flips_the_sign() -> None:
    assert negate_paise(500) == -500
    assert negate_paise(-500) == 500
    assert negate_paise(0) == 0


def test_split_paise_gives_remainder_to_the_first_parts() -> None:
    assert split_paise(100, 3) == [34, 33, 33]
    assert split_paise(100, 4) == [25, 25, 25, 25]
    assert split_paise(0, 3) == [0, 0, 0]
    assert split_paise(100, 1) == [100]
    assert split_paise(-100, 3) == [-33, -33, -34]


def test_split_paise_never_loses_or_creates_paise() -> None:
    for total in range(-20, 21):
        for parts in range(1, 7):
            pieces = split_paise(total, parts)
            assert len(pieces) == parts
            assert sum(pieces) == total


def test_split_paise_handles_large_amounts_exactly() -> None:
    total = 999_999_999_999
    assert sum(split_paise(total, 7)) == total


def test_split_paise_rejects_fewer_than_one_part() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        split_paise(100, 0)


def test_money_values_are_always_integers() -> None:
    assert isinstance(parse_paise("500.50"), int)
    assert isinstance(split_paise(100, 3)[0], int)
    assert isinstance(negate_paise(5), int)
