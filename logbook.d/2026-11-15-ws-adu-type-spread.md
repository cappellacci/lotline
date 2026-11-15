### LB-NNN · 2026-11-15 · ADU · Do core cities need their own spread of place luck? (D-094 result)

- **Question:** does a place-effect variance per type (core cities vs suburbs) predict held-out states better
  than A + place types? Ben accepted D-094 and asked for the run ("Accept D-094 and run it").
- **Outputs:**
  - `reports/adu-type-spread/` (fits, held-out scores, tiers, tests A, B and D, coverage, README, `results.html`);
    page https://claude.ai/artifact/1QRuqXpv5b1rrYFDPBszR9;
  - `src/lotline/model/adu_types.py` (`fit3_types(spread=True)`, `alphas`, `is_core`), `adu_screen.place_loglik`
    (α per place), `joint_refit.GlobalsA.alpha_core` / `place_alpha`, `adu_trend` (α by type in test D);
  - tests in `tests/model/test_adu_types.py`; `scripts/dev/adu_type_spread.py` and `_page.py`;
  - `docs/analysis_plan.md` D-094 status and result; fix to `scripts/dev/adu_range_coverage.decompose`.
- **Result:** core cities vary less in the fit (α 1.01 vs 2.45), but only with Minnesota in; held out, no gain
  (−0.1, 2 SE 2.9). D-088's rule keeps A + P. State ranges would narrow (NC ×24 → ×11) but without evidence of
  being more accurate. Nothing to config.
- **What Claude did:** drafted D-094, implemented the option, wrote hand-worked and recovery tests, ran the fits
  and tests offline, built the page.
- **How it was checked:**
  - λ = 0 reproduces A + P's likelihood and draws exactly (tests);
  - a planted α_core < α_sub is recovered;
  - A + P's fits match the D-088 rescoring run (θ 0.1997 per 1,000, α 1.698, core +1.839);
  - a bug in the width split (α_core left on) was found on reading the first run, fixed, and the run repeated
    with identical fits and decision;
  - ruff and the model tests pass.
