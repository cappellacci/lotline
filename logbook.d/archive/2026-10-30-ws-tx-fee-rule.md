### LB-NNN · 2026-10-30 · Policy analysis: one per-home fee where Texas fees vary by area or plat date
- **Question:** which fee row stands for a typical new home when the amount depends on the lot's area, basin,
  density tier or plat date, so the fee scenario can use local fees for San Antonio and Fort Worth?
- **What I did:**
  - Coded Ben's rule (2026-10-30). The median row of an area, basin or tier group is central. The newest plat
    cohort is central for plat-date groups. Only the central row carries `amount_per_unit_usd`; the group's low
    and high go in its notes.
  - Wrote `scripts/dev/tx_fee_rule_2026_10_30.py` (rerun-safe), the rule in `config/fees/README.md`, and
    `tests/states/tx/test_fee_rule.py`, with hand-worked totals.
  - Opened issue #247 for WS-CORE: a per-place fee range in the scenario, and the newest-year-per-component
    rule.
- **Inputs:** `config/fees/tx.csv`.
- **Outputs:** `config/fees/tx.csv` (26 rows), `scripts/dev/tx_fee_rule_2026_10_30.py`,
  `tests/states/tx/test_fee_rule.py`, `config/fees/README.md`, `docs/build/tx-readiness.md`, ordinances README,
  issue #247.
- **Findings:**
  - Local fee totals (`local_fees`):
    - San Antonio $6,981 (was the Handbook $50,000): middle-elevation water $4,908 plus Upper Medina wastewater
      $2,073, the basin nearest the median of six, $2,078.
    - Fort Worth $5,828 (was $50,000).
    - Austin $6,763 (was $19,054). #244 had given all three parkland density tiers a per-home amount, so they
      were summed.
    - Houston $4,383 and Dallas $931 (tap and inspection only), unchanged.
  - Austin's 2023 water and wastewater impact fees (about $7,700 for the newest cohort) are still left out by
    the scenario's newest-year-per-component rule, so its total is a floor (#247).
- **Decisions:** Ben 2026-10-30: the median area or newest plat cohort is central, and the rest is the range.
  Proposed for HANDOFF.
- **AI:** Claude wrote the script, rule text and tests, and checked the totals with `local_fees` before and
  after. Texas, fee and model tests pass (451).
- **Open / next:** #247 (WS-CORE); a confirmed Dallas statement on impact fees.
