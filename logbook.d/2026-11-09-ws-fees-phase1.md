### LB-NNN · 2026-11-09 · Build: fee levels by building type, ranges and still-in-force rows (D-066, #247)
- **Question:** What does each place really charge per new unit, by building type and in 2025 dollars? How
  should missing pieces be filled under D-065, without the Handbook's $50,000?
- **What I did:**
  - Added `src/lotline/model/fee_levels.py`. It applies, by building type, the newest schedule year per
    component plus older rows still in force; converts to 2025 dollars with CPI-U; carries low and high
    ranges; and fills missing permit and water/sewer charges from the median of coded places (state, then
    pooled), with the 25th–75th percentile as the range.
  - Schema 1.11 (Ben approved): `fees.in_force_through`, `amount_per_unit_low_usd` and
    `amount_per_unit_high_usd`, with a check that low ≤ central ≤ high. `scripts/dev/fee_ranges_2026_11_09.py`
    added the columns to every fee file and filled the Texas ranges and the Austin and Bend still-in-force rows.
  - `scenarios/fees.py`: the three D-065 scenarios (`handbook`, `local_half`, `local_25k`); the local fee is
    drawn within its range in each simulation draw; no $50,000 fallback. `scripts/dev/fee_dev_run.py` now
    uses the new fee levels.
  - `scripts/dev/fee_levels_table.py` writes `docs/research/fee-levels-vs-handbook.md`: every coded place and
    building type against $50,000.
- **Inputs:** `config/fees/*.csv`; CPI-U from the local data store (index only); #247; D-065; office-hours
  notes A4/A5.
- **Outputs:** `src/lotline/model/fee_levels.py`, `src/lotline/model/scenarios/fees.py`,
  `src/lotline/schemas.py` (1.11), `docs/schemas.md`, `config/fees/*.csv`, `config/fees/README.md`,
  `scripts/dev/fee_ranges_2026_11_09.py`, `scripts/dev/fee_levels_table.py`, `scripts/dev/fee_dev_run.py`,
  `docs/research/fee-levels-vs-handbook.md`, `docs/model_and_assumptions.md` (fees paragraph),
  `docs/analysis_plan.md` D-066; tests `tests/model/test_fee_levels.py`, `tests/model/test_fee_scenario.py`,
  `tests/core/test_fees_config.py`, `tests/states/tx/test_fee_rule.py`.
- **Findings:**
  - House fee medians in 2025 dollars: MN $9,148, NC $9,632, TX $9,461, OR $33,553. No coded place
    reaches $50,000.
  - The #247 fix moves Austin from $6,763 to $14,463 and Bend from $23,162 to $34,598 (nominal).
  - 23 of 39 coded places have no permit fee coded and take the pooled median (about $4,000), which is
    almost all Minnesota.
  - Eugene loses its Handbook fallback and drops to the pooled median, below its known lower bound
    (open in D-066).
- **Decisions:** D-066 (schema columns approved by Ben on 2026-11-09; the building-type fallbacks, CPI cap and
  P25–P75 fill range are for Ben to confirm). Proposed for HANDOFF in the PR.
- **AI:** Claude Code wrote the module, scripts, schema change and tests. Each rule has a hand-worked test;
  one hand value in a test (a P25) was wrong at first and corrected against numpy's linear percentile.
  Before and after comparison: no fee CSV value changed except the new columns and notes. No model was run.
- **Open / next:**
  - ~~Eugene (D-066 options a/b)~~ settled, see below.
  - Permit schedules for NC/OR/TX would replace the Minnesota-heavy prior.
  - Phase 2: SFD/duplex/fourplex pencil-out table and dose by building type.
- **Addendum (same day):** Ben chose D-066 option (a) for Eugene and confirmed the D-066 details (type fallbacks,
  CPI cap, P25–P75 fill range, 5-place minimum). `scripts/dev/eugene_fees_2026_11_09.py` prices six Eugene
  rows for a house: $17,507.88 central, $25,365.17 high (LID stormwater and upper-zone water). Checked by a
  hand-sum test in `tests/states/or/test_fees.py` (replaces the "stays on the Handbook prior" test), the OR and fee
  tests (117 passed), and `compliance_check.py` (0 FAIL). `docs/research/fee-levels-vs-handbook.md` regenerated.
