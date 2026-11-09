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

**Fees that vary by area, basin, tier or plat date (Ben, 2026-10-30).** Only one row of such a group carries
`amount_per_unit_usd`. The other rows keep their schedule amounts with `amount_per_unit_usd` blank, and the
central row's `notes` give the group's low and high as the range.
- **Areas, basins and density tiers:** the median row is central. With an even count, the central value is the
  median of the amounts, carried by the row nearest it, the lower one on a tie.
- **Plat-date cohorts:** the newest cohort is central, because most new homes go on recently platted lots; the
  older cohorts are the low end.
- **Texas cases** (`scripts/dev/tx_fee_rule_2026_10_30.py`): SAWS water by elevation area and wastewater by
  basin; Austin parkland by density tier; Austin water and wastewater impact fees by plat date; Fort Worth by
  plat cohort.
- The central row also carries the group's range in `amount_per_unit_low_usd` and `amount_per_unit_high_usd`
  (schema 1.11, #247; written by `scripts/dev/fee_ranges_2026_11_09.py`). The fee scenario uses the central
  value as its central fee and draws within the range in each simulation draw (D-066).

**Older rows still in force (`in_force_through`, schema 1.11, #247).** For each place and fee component the
engine counts the newest schedule year. A row from an older year counts too when its `in_force_through` reaches
that newest year: set it when a schedule from another agency, or an impact-fee ordinance, is still current next
to newer rows of the same component (Austin's 2023 water and wastewater impact fees; Bend Park & Recreation
District's FY 2025-26 park SDC). Leave it blank when a newer schedule replaced the row.

**How the engine reads these files.** `src/lotline/model/fee_levels.py` (D-065, D-066): per building type (a
duplex or fourplex uses its own rows, then `OTHER` rows, then the place's house rows), in 2025 dollars, and with
missing permit and water/sewer charges filled from the median of coded places. The result for every coded place
is in `docs/research/fee-levels-vs-handbook.md` (`scripts/dev/fee_levels_table.py`).

**Batch 1 (2026-10-20).** `mn.csv`, `nc.csv` and `tx.csv` come from `docs/research/ordinances/batch1-2026-10-20.json`
(15 of 23 cities have usable rows). Rebuild with `uv run python scripts/dev/ordinance_records.py`. No row is
checker-verified yet: `verified_by` is blank until the checker's verdicts are stored.
