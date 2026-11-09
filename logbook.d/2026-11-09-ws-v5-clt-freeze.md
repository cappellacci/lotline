### LB-NNN · 2026-11-09 · Validation: V5 Charlotte blind forecast frozen
- **Question:** before seeing any outcome, what does Lotline predict Mecklenburg County built in 2-4 unit
  buildings in 2023-2025, after Charlotte's UDO allowed duplexes and triplexes on 169,314 N1 lots?
- **What I did:**
  - Pre-registered the method as D-071 in `docs/analysis_plan.md` (committed 6f26963, before any code or run):
    BPS 37119 2-4 unit buildings 2023-2025, flat 2020-2022 baseline plus the D-054/D-055 missing-middle hazard
    on N1 lots × the six-town eligible-share prior; pass = observed within P10-P90.
  - Wrote `src/lotline/validation/v5.py`, `scripts/dev/v5_clt_predict.py` and `tests/core/test_v5.py` (10
    hand-worked tests on synthetic inputs), then froze from commit 77e8710.
- **Inputs:** pre-UDO roll (vintage 2023-05-31), `config/params/v5_charlotte.yaml`, BPS 37119 through the
  holdout filter (to 2022), Charlotte ACS rent ending 2022, `mm_hazard.yaml`, `config/reforms/nc.csv`.
- **Outputs:** `results/frozen/V5-NC-CHARLOTTE.json`; D-071.
- **Findings:** P10 89, P50 104, P90 172 buildings (mean 137); the baseline alone is about 99. The median
  sits near the baseline and the tail comes from Charlotte's place multiplier (α 8.4).
- **Decisions:** D-071 (method). Proposed for HANDOFF: V5 frozen 2026-11-09, ahead of the Nov 17 target.
- **AI:** Claude Code wrote the entry, code, tests and freeze. Checked: tests by hand (ramp, mean of draws,
  dose of the coded UDO row), dry run against a hand estimate (about 21 added buildings at θ's median, 36 at
  its mean; draws gave 38.6), `compliance_check.py` 0 FAIL. No Charlotte or Mecklenburg outcome from
  2023-06-01 was read.
- **Open / next:** merge; then, on Ben's go-ahead, release the holdout, write `scripts/dev/v5_clt_score.py`
  and score (#45).
