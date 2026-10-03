"""Pure money handling: integer paise only, never floats.

One rupee is 100 paise, and every amount is a whole number of paise. This module
is the single place that parses, adds, formats and splits money. It performs no
I/O and never imports from models, db, services or api.
"""

import re

RUPEE_SYMBOL = "₹"
_PAISE_PER_RUPEE = 100

# Integer part is either plain digits or comma-separated groups, where the first
# group has 1-3 digits and later groups have 2-3 (so Indian and Western grouping
# both parse). At most two decimal places: more is rejected, never rounded.
_AMOUNT_PATTERN = re.compile(r"^(?:\d+|\d{1,3}(?:,\d{2,3})*)(?:\.\d{1,2})?$")


class InvalidMoneyError(ValueError):
    """Raised when text cannot be read as a money amount."""


def parse_paise(text: str) -> int:
    """Parse a money amount from text into integer paise.

    Accepts forms like ``500``, ``500.5``, ``1,23,456.78``, ``₹1,23,456.78``
    and a leading ``-``. Rejects anything else: non-text input, more than two
    decimal places, malformed grouping and unknown currency prefixes.
    """
    if not isinstance(text, str):
        raise TypeError("money must be parsed from text, never from a float or number")

    cleaned = text.strip()
    sign = 1
    if cleaned.startswith("-"):
        sign = -1
        cleaned = cleaned[1:].lstrip()

    if cleaned.startswith(RUPEE_SYMBOL):
        cleaned = cleaned[len(RUPEE_SYMBOL) :].strip()

    if not _AMOUNT_PATTERN.match(cleaned):
        raise InvalidMoneyError(f"not a valid money amount: {text!r}")

    rupees_text, _, fraction_text = cleaned.partition(".")
    fraction = fraction_text.ljust(2, "0") if fraction_text else "00"
    rupees = int(rupees_text.replace(",", ""))
    return sign * (rupees * _PAISE_PER_RUPEE + int(fraction))


def add_paise(*amounts_paise: int) -> int:
    """Sum integer paise amounts; returns 0 when called with no arguments."""
    return sum(amounts_paise)


def subtract_paise(minuend_paise: int, subtrahend_paise: int) -> int:
    """Return ``minuend_paise - subtrahend_paise``; the result may be negative."""
    return minuend_paise - subtrahend_paise


def negate_paise(amount_paise: int) -> int:
    """Return ``amount_paise`` with the opposite sign."""
    return -amount_paise


def format_paise(paise: int) -> str:
    """Format integer paise as Indian-grouped text, e.g. ``₹1,23,456.78``.

    Negative amounts carry a leading minus before the symbol, e.g. ``-₹500.00``.
    """
    sign = "-" if paise < 0 else ""
    rupees, fraction = divmod(abs(paise), _PAISE_PER_RUPEE)
    return f"{sign}{RUPEE_SYMBOL}{_group_indian(rupees)}.{fraction:02d}"


def split_paise(total_paise: int, parts: int) -> list[int]:
    """Split an amount into ``parts`` whole paise that sum back to the total.

    The remainder goes to the first parts, so ``100`` into 3 gives
    ``[34, 33, 33]``. ``parts`` must be at least 1.
    """
    if parts < 1:
        raise ValueError(f"parts must be at least 1, got {parts}")

    base, remainder = divmod(total_paise, parts)
    return [base + 1 if index < remainder else base for index in range(parts)]


def _group_indian(rupees: int) -> str:
    """Group a non-negative integer Indian-style (last three, then twos)."""
    digits = str(rupees)
    if len(digits) <= 3:
        return digits

    head, tail = digits[:-3], digits[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    groups.append(tail)
    return ",".join(groups)
