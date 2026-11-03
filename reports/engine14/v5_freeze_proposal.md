# V5 freezes: proposed method and file format (for Ben's decision)

*Thread 14, task 4. Drafted 2026-11-03. Nothing here is frozen and no prediction has been computed. The freeze
must be on `main` by **Tue Nov 17** (`holdout.check_unblind` accepts only a frozen file added in a commit on
`main`). No held-out row was read for this note; it uses only `reports/nc/V5-charlotte-inputs.md`,
`reports/mn/V5-stpaul-inputs.md`, the validation plan (V5) and the analysis plan.*

## Why this is a proposal, not a freeze

1. **The method is a pre-registration choice.** `results/frozen/` doesn't exist yet. No code makes a V5
   prediction, and the validation plan says *what* to predict but not *how*. The method must be fixed before
   any number is computed, so it needs your sign-off first.
2. **The effect to use is open.** The handoff says to use "whatever D-024 estimate or prior is on `main`".
   Today `main` has only October's "no credible estimate" (`reports/mm-d024*`) and no missing-middle effect
   prior in `config/params/`. The four-state D-024 run (results PR, this thread) may change that, depending on
   its checks.
3. **Charlotte waits on Nov 10** (option a, Mecklenburg's archived roll, or option b, the town prior).

## Proposed method (the same for both tests)

Prediction = **baseline** (what the eligible lots would have produced without the reform) × **(1 + effect)**,
with the uncertainty from every input carried by simulation.

| Piece | Charlotte (V5-NC-CHARLOTTE) | St. Paul (V5-MN-STPAUL) |
|---|---|---|
| Outcome | 2–4 unit homes permitted on N1 lots, 2023-06-01 → 2025-12-31 | 2–4 unit (`DTQ`) homes permitted on H1/H2 lots, 2024–2026; 5+ (`MF5`) reported alongside, not scored |
| Eligible lots | 169,314 N1 lots × (`n1_sf_share` + `n1_vacant_share`), drawn over the YAML ranges (≈144k central; option (a) counts replace the shares) | 55,269 (H1 37,695 + H2 17,574), fixed |
| Baseline rate | City 2–4 unit homes per eligible lot per year, mean of the last 5 pre-window years: 2018–2022, BPS 37119 `units_2 + units_3_4` (county level, see note) over the city's rule 1.1 denominator | 2019–2023, Met Council `DTQ` units for 2758000 over its rule 1.1 denominator |
| Baseline range | Lowest and highest of those 5 years, plus Poisson noise on the counts | Same |
| Effect | The D-024 estimate on `main` at freeze (ATT on the log scale, with its bootstrap interval), or, if D-024 still has no credible estimate, a stated prior: **0 (no effect) as the central value, with D-024's interval as the range**, labelled as such | Same |
| Annual inputs | Capped at 2022 | Capped at 2023 |
| Simulation | 10,000 draws, seed fixed in the file; report P10, P50, P90 for the total and each year | Same |
| Pass (validation plan, proposed) | Observed total within P10–P90; one case, presented as a demonstration | Same |

**Note on Charlotte's baseline.** BPS files Charlotte under Mecklenburg County (37119), which also holds the
six towns and the unincorporated county. Two choices: (i) the county rows scaled by Charlotte's share of the
county's eligible lots, or (ii) Charlotte's own pre-window permits from the Mecklenburg legacy file (`U2`,
`U3_4`, to 2023-05-31). I'd use (ii) as the main baseline, since it is Charlotte only and record level, and (i)
as a check, both in the freeze file. Scoring then needs N1 permits from the Accela file (legacy thins in 2025),
or else BPS 37119 at county level, disclosed. So the freeze should also carry a county-level prediction (the
Charlotte prediction plus the towns' and unincorporated area's baseline, unchanged), so either score source
works.

**Note on St. Paul's window.** Met Council's 2026 permits won't be out until 2027. I'd score 2024–2025 when
unblinded and add 2026 later, with each year's prediction frozen now.

## Proposed file format (`results/frozen/<test_id>.json`)

```json
{
  "test_id": "V5-MN-STPAUL",
  "frozen_at": "2026-11-XXT..:..-05:00",
  "code_commit": "<sha of main the script ran on>",
  "script": "scripts/dev/freeze_v5.py",
  "outcome": {"what": "2-4 unit homes permitted on H1/H2 lots", "years": [2024, 2025, 2026], "source_for_scoring": "metc_permits DTQ, placed on the 2023-11-26 zoning snapshot"},
  "inputs": [{"name": "eligible_lots", "value": 55269, "source": "stpaul_v5.load(...)['h_lots']", "dated": "roll 2023-12-26"}, "..."],
  "input_cap_year": 2023,
  "effect": {"source": "reports/mm-d024-4state/... or 'prior'", "log_att": 0.0, "low": 0.0, "high": 0.0, "label": "..."},
  "baseline": {"rate_per_lot_year": 0.0, "years_used": [2019, 2023], "low": 0.0, "high": 0.0},
  "simulation": {"draws": 10000, "seed": 0},
  "prediction": {"total": {"p10": 0, "p50": 0, "p90": 0}, "by_year": {"2024": {"p10": 0, "p50": 0, "p90": 0}}},
  "pass_rule": "observed total within P10-P90",
  "exposures": ["D-013: post-reform St. Paul figures appeared in a research doc during scouting; not used here"],
  "sha256_of_inputs": "<hash of the input table the script wrote>"
}
```

Charlotte's file is the same, with `n1_sf_share` and `n1_vacant_share` and the option used (a or b), and the
D-012 disclosure (Mecklenburg BPS rows leaked into the NC V1 backtests in aggregate).

## What I need from you

1. **Method:** OK as above? In particular: a flat 5-year baseline rate (no trend), and effect = 0 with D-024's
   interval if D-024 still has no credible estimate.
2. **Charlotte baseline:** legacy-file Charlotte permits (ii) as the main baseline, with county BPS (i) as a
   check?
3. **Nov 10:** option (a) or (b) for Charlotte.

Once you sign off: one PR adding `scripts/dev/freeze_v5.py` with tests on synthetic inputs, plus a dated
analysis-plan entry. Then one run per test writes both JSON files, and a second PR puts them on `main`
before Nov 17.
