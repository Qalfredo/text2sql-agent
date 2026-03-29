# Example database notes

## Metric definitions

- `gross_revenue` should be interpreted before refunds unless a table-level note says otherwise.
- Customer activity metrics should filter out test accounts when a boolean such as `is_test` exists.

## Join guidance

- Prefer joining fact tables to dimensions on stable surrogate keys.
- When both UTC and local timestamps exist, use UTC for cross-region reporting unless the question explicitly asks for local time.
