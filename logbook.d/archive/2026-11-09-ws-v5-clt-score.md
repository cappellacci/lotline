### LB-NNN · 2026-11-09 · Validation: V5 Charlotte unblinded and scored (pass)
- **Question:** did the frozen V5 range (#353, D-071) contain what Mecklenburg County actually built?
- **What I did:**
  - After #353 merged (017960c) and Ben asked, released `V5-NC-CHARLOTTE` in `config/states/nc.yaml`
    (`released_on`, `released_note`).
  - Wrote `scripts/dev/v5_clt_score.py`, which regenerates the frozen draws (checked identical) before
    reading BPS 37119 for 2023-2025.
  - Added scoring functions to `src/lotline/validation/v5.py`, with 3 more hand-worked tests.
- **Inputs:** `results/frozen/V5-NC-CHARLOTTE.json`; Census BPS raw files (2023-2025 complete, 12 months
  reported).
- **Outputs:** `reports/v5-charlotte/README.md`, `reports/v5-charlotte/score.json`; results under D-071.
- **Findings:**
  - Pass: 119 buildings observed against a P10-P90 of 89-172 (median 104, 77th percentile, "useful"). CRPS
    10.1 against 14.5 for no reform.
  - Homes: inside (256 against 213-402).
  - County-wide count, one case; one-unit building fell by almost half over the window.
- **Decisions:** proposed for HANDOFF: V5 scored and released 2026-11-09 (pass).
- **AI:** Claude Code wrote the scorer and report; checked by the regeneration guard, the tests, and the BPS
  months-reported column.
- **Open / next:** rebuild NC processed tables (`lotline fetch`) so Charlotte's and Mecklenburg's post-2023
  rows enter the results page, D-070's observed floor and the historical_floor guardrail.
