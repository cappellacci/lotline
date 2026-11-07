### LB-NNN · 2026-11-07 · `missing-middle` · Lubbock second coder, the five-year-rate range, the scenario module's definition

- **Question:** after D-059, what was Lubbock's missing-middle rule really; how should the scenario carry the
  θ–ramp ridge; and what should `model/scenarios/mm.py` compute?
- **Outputs:**
  - `docs/research/ordinances/tx-second-coder-lubbock-2026-11-07.csv` and `.md`: second-coder row for
    `TX-4845000-missing_middle-2023`. Partly agrees: the 2023 cells hold; old R-2 (two-family) already allowed
    duplexes and maps to MDR; the SF-2 gain is limited by the block-face rule. `tx.csv` not edited.
  - `docs/analysis_plan.md` **D-062** (proposed, not run): put the scenario's range on the five-year rate
    r5 = θ × mean ramp share, because θ's interval is profiled over every half-way point while V9 and the
    scenario hold the ramp at 0.5 (top draws give ~0.85 per 1,000 a year against 0.04–0.10 at either peak).
  - `docs/analysis_plan.md` **D-063** (proposed, no code): the Handbook missing-middle scenario: added
    buildings ~ Poisson(h_t × u × E × (1 − current dose) × F(PCR)/F(1)), with four choices for Ben.
- **What Claude did and how it was checked:** a fresh-context Claude subagent did the second coding from web
  sources (Zoneomics mirror of Ch. 39, Lubbock staff reports); the first coder was also Claude, so this is not
  a human second coder; sources and unverified points are listed. The m(half) values in D-062 were computed by
  hand from `hazard.ramp`. No model run, no data read, no holdout touched.
