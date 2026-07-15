# Exact demo prompt

Fix the invoice discount allocation defect. Reproduce the reconciliation failure before editing product code. Preserve the public `allocate_discount(line_totals, discount)` interface, use decimal arithmetic, change only `src/invoice.py`, and prove that every non-negative allocation sums exactly to the requested invoice discount. Stop for the required approval, resume without repeating completed side effects, run the full verifier, review the final diff, and prepare a clean PR-ready commit with an independent completion audit.
