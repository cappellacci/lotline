### LB-fragment · 2026-11-14 · ADU model · What would adding housing age, and rescoring on the checked rows, look like?

- **Outputs:** D-087 (proposed) in `docs/analysis_plan.md`, branch `ws/adu-age-term` (built on `ws/adu-owner-share`, #418).
- **Answer:** a method entry, written before any fit. Form A″ = D-084's Form A′ × exp(β_a z_age), with housing age
  standardized on D-083's 57 places (center 0.2045, scale 0.1669). Forms A, A′ and A″ are refitted on the rule rows
  after #419. The decision is two steps under D-084's rule: A′ against A, then A″ against the base in use.
- **HANDOFF:** proposes D-087 (provisional number); Ben to accept or amend.
- **What Claude did:** asked by Ben ("Draft it"); found D-084 already run (#418) and its outlook that age added
  nothing on the old rows, and wrote that evidence into the entry; fixed the center and scale from
  `reports/adu-covariate-screen/factors.csv`. Nothing fitted or scored.

### LB-fragment · 2026-11-14 · ADU model · Does housing age, or owner share, earn a place in Form A on the checked rows?

- **Outputs:**
  - `reports/adu-age-term/` (README, fits, tiers, tests, summary);
  - results page https://claude.ai/artifact/34Yor5h8wn51dDAT3PoXaf;
  - D-087 accepted, built and run (Result note in `docs/analysis_plan.md`);
  - code: `src/lotline/model/adu_terms.py`, `joint_refit.GlobalsA` (vector β), `tests/model/test_adu_terms.py`,
    `config/params/adu_age.yaml`, `scripts/dev/adu_age_refit.py`, `scripts/dev/adu_age_page.py`;
  - PR #426.
- **Answer:** under D-084's rule, fixed before the run, Form A stays in both steps.
  - A′ and A″ each beat A's held-out log score by more than 2 SE.
  - But each passes 1 of tests A–B, against A's 2. The gap is one place, College Station.
  - Age adds nothing held-out on top of owner share.
  - Within states, age carries the signal and owner share does not.
- **HANDOFF:** none added. The PR asks Ben whether to accept the outcome (keep A, leave #418 unadopted).
- **What Claude did:**
  - Built the two-term fitter, with hand-worked tests that reproduce D-084's one-term fits.
  - Ran a `--smoke` code-path check, then the full run (1 h 40 min, offline, St. Paul held out).
  - Wrote the README and the results page from the run's own CSVs.
  - Checked: the decision lines and log-score gains were recomputed by hand from `logscores_tier1.csv`. The
    College Station check was run after the result and is labeled so.
