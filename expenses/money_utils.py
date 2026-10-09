"""Safe money conversion between Decimal, display strings, and MongoDB Decimal128."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from bson.decimal128 import Decimal128


TWOPLACES = Decimal("0.01")


def decimal_from_input(value: str | Decimal | float | int) -> Decimal:
    if isinstance(value, Decimal):
        d = value
    else:
        d = Decimal(str(value).strip())
    if d <= 0:
        raise ValueError("Amount must be greater than zero.")
    return d.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def to_decimal128(amount: Decimal) -> Decimal128:
    return Decimal128(amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP))


def from_stored(value: Any) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal128):
        return value.to_decimal().quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if isinstance(value, Decimal):
        return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    try:
        return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def format_money(amount: Decimal) -> str:
    return f"{amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP):,.2f}"
