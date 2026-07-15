from __future__ import annotations

from decimal import Decimal, ROUND_DOWN


CENT = Decimal("0.01")


def allocate_discount(line_totals: list[Decimal], discount: Decimal) -> list[Decimal]:
    """Allocate an invoice discount proportionally and reconcile every cent."""
    if not line_totals:
        return []
    if discount < 0 or any(line < 0 for line in line_totals):
        raise ValueError("line totals and discount must be non-negative")
    total = sum(line_totals, Decimal("0"))
    if total == 0:
        return [Decimal("0.00") for _ in line_totals]

    exact = [discount * line / total for line in line_totals]
    allocated = [amount.quantize(CENT, rounding=ROUND_DOWN) for amount in exact]
    remainder_cents = int((discount - sum(allocated, Decimal("0"))) / CENT)
    priority = sorted(range(len(exact)), key=lambda index: (exact[index] - allocated[index], -index), reverse=True)
    for index in priority[:remainder_cents]:
        allocated[index] += CENT
    return allocated
