from __future__ import annotations

import unittest
from decimal import Decimal

from src.invoice import allocate_discount


class AllocateDiscountTests(unittest.TestCase):
    def test_allocations_reconcile_rounding_remainder(self):
        allocations = allocate_discount(
            [Decimal("10.00"), Decimal("10.00"), Decimal("10.00")],
            Decimal("0.10"),
        )
        self.assertEqual(sum(allocations), Decimal("0.10"))
        self.assertEqual(allocations, [Decimal("0.04"), Decimal("0.03"), Decimal("0.03")])

    def test_preserves_proportional_allocation_without_remainder(self):
        self.assertEqual(
            allocate_discount([Decimal("30.00"), Decimal("70.00")], Decimal("10.00")),
            [Decimal("3.00"), Decimal("7.00")],
        )

    def test_reconciles_uneven_lines_with_stable_largest_remainder(self):
        allocations = allocate_discount(
            [Decimal("9.99"), Decimal("4.01"), Decimal("1.00")],
            Decimal("1.01"),
        )
        self.assertEqual(sum(allocations), Decimal("1.01"))
        self.assertEqual(allocations, [Decimal("0.67"), Decimal("0.27"), Decimal("0.07")])

    def test_zero_total_returns_cent_precision_zeroes(self):
        self.assertEqual(
            allocate_discount([Decimal("0"), Decimal("0")], Decimal("0")),
            [Decimal("0.00"), Decimal("0.00")],
        )

    def test_rejects_negative_money(self):
        with self.assertRaises(ValueError):
            allocate_discount([Decimal("10.00")], Decimal("-1.00"))


if __name__ == "__main__":
    unittest.main()
