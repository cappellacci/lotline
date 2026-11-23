### LB-NNN · 2026-11-23 · VALIDATION · V6b: does the fee model's response stay in the published range, and how far apart are real fees and the benchmark?

- **Question:** the validation plan's V6b (issue #49). How many lots cross feasibility with the $25,000
  benchmark cut and with real local fees, and is the five-year response inside 0-12% (houses) and 0-18% (2-4
  units)?
- **Outputs:** `scripts/dev/v6b_fee_threshold.py`; `reports/v6b/V6b-fee-threshold.md` and
  `reports/v6b/<ST>.json`; results note in `docs/analysis_plan.md` (2026-11-23).
- **What Claude did and how it was checked:**
  - Wrote the script on the engine's own functions (`fees.feasibility_change`, `fees.simulate`), so it adds
    no model arithmetic.
  - Ran the five development states one at a time (under 1 GB each).
  - Result: pass, 20 of 20 midpoints inside the range. Real fees cut by half move building 4-10 times less
    than the benchmark cut.
  - Lots crossing are countable only in Minnesota and Oregon, which have parcel rolls with vacant lots.
