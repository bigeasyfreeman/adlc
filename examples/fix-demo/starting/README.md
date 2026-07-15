# Invoice allocation service

`allocate_discount` distributes an invoice-level discount across line totals. The public contract requires cent precision, non-negative allocations, stable line ordering, and exact reconciliation to the invoice-level discount.
