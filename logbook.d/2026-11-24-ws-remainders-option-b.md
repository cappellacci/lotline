### LB-NNN · 2026-11-24 · ENGINE · Where should county remainders borrow their rules from?

- **Question:** with D-102's populations, county remainders borrowed rule priors and doses from cities their
  size. Ben chose that they borrow from coded county remainders (option b), and from the smallest band where
  too few are coded.
- **Outputs:**
  - #488's rule-6 commits, carried onto main;
  - `adu.remainder_priors` and `apply_priors`, `mm.dose_pools` and `remainder_pool_key`;
  - tests in `tests/model/test_scenario_adu.py` and `tests/model/test_scenario_mm.py`;
  - dated deviation in `docs/analysis_plan.md` (2026-11-24);
  - jurisdictions and place_inputs rebuilt offline for six states, with a backup.
- **What Claude did and how it was checked:**
  - Hand-worked tests for both models.
  - Measured all six states one at a time: Oregon missing middle +5% instead of −42%, Oregon ADU −8%, NC
    ADU −3%, the rest within 1%.
  - A first version without the smallest-band fallback still gave Oregon −42%: only Oregon's ADU rules have
    5 or more coded remainders. That finding was taken to Ben, who chose the smallest band.
  - Done here, not in the WS-SCALE or MM sessions (both idle), because Ben runs one thread at a time.
