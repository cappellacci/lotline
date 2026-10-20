# Hand-coded development fees

One CSV per state (`<st>.csv`), validated by `lotline.config.load_fees` against the `fees` schema
(`docs/schemas.md`). Each row is one fee component for one building type in one jurisdiction and year,
copied from the city's **official fee schedule**, with `source` (the schedule's URL), `source_section`,
`source_quote` (verbatim, at most 300 characters) and, once an independent checker has re-opened the source,
`verified_by` and `verified_date`. Amounts are in the schedule's own dollars (`dollar_year`); convert per-meter
or per-square-foot fees to one dwelling unit in `amount_per_unit_usd`, with the assumption in `notes`.
Rows are written by `scripts/dev/ordinance_records.py` from verified city-ordinance records, or by hand
from a manual lookup using the same columns.

**Reading `amount_per_unit_usd`.** It is what one dwelling unit of a typical new project pays for that row. It is
blank when the fee does not fall on a typical infill home (rezoning, variance, escrow, subdivision-only, lots
never assessed), when it is charged on land area (per acre, per sq ft of plat), when a valuation bracket or size
band does not contain the prototype, or when a share of the permit fee has no converted permit fee beside it.
`amount_usd` always keeps the schedule's own number (blank for shares and rates). Rows coded `OTHER` apply to
any building type; their valuation-based amounts are worked out for the single-family prototype. `notes` names
the conversion rule for every row.

**Batch 1 (2026-10-20).** `mn.csv`, `nc.csv` and `tx.csv` come from `docs/research/ordinances/batch1-2026-10-20.json`
(15 of 23 cities have usable rows). Rebuild with `uv run python scripts/dev/ordinance_records.py`. No row is
checker-verified yet: `verified_by` is blank until the checker's verdicts are stored.
