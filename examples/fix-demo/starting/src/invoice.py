from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def allocate_discount(line_totals: list[Decimal], discount: Decimal) -> list[Decimal]:
    """Allocate an invoice discount proportionally at cent precision."""
    if not line_totals:
        return []
    if discount < 0 or any(line < 0 for line in line_totals):
        raise ValueError("line totals and discount must be non-negative")
    total = sum(line_totals, Decimal("0"))
    if total == 0:
        return [Decimal("0.00") for _ in line_totals]
    return [(discount * line / total).quantize(CENT, rounding=ROUND_HALF_UP) for line in line_totals]
