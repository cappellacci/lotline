# Hand-coded development fees

One CSV per state (`<st>.csv`), validated by `lotline.config.load_fees` against the `fees` schema
(`docs/schemas.md`). Each row is one fee component for one building type in one jurisdiction and year,
copied from the city's **official fee schedule**, with `source` (the schedule's URL), `source_section`,
`source_quote` (verbatim, at most 300 characters) and, once an independent checker has re-opened the source,
`verified_by` and `verified_date`. Amounts are in the schedule's own dollars (`dollar_year`); convert per-meter
or per-square-foot fees to one dwelling unit in `amount_per_unit_usd`, with the assumption in `notes`.
Rows are written by `scripts/dev/ordinance_records.py` from verified city-ordinance records, or by hand
from a manual lookup using the same columns.
