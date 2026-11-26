# Calibration: where every fitted number comes from

About 130 values in `config/params/` are fitted to our own data (the rest are judgment, literature or the
Handbook's own numbers, each with its source). Every fitted value belongs to exactly one **calibration step**,
declared in `src/lotline/calibrate/steps.py`. Each step names:

- the values it produces;
- the decision in `docs/analysis_plan.md` it implements;
- the script or library function that computes it;
- the steps it needs first;
- whether today's value was written by code or copied from a report.

```bash
uv run lotline calibrate --list    # the steps in run order: what each produces, how, and its status
uv run lotline calibrate --check   # registry, config and lock agree (no data needed; also a test in CI)
```

`config/calibration.lock.json` records every fitted value as it stands. If a value changes in config without
its step being re-run and the lock rewritten (`lotline calibrate --write-lock`), the check fails, so a fitted
number can't drift from its fit unnoticed.

**Status of the steps (2026-11-26).** 18 of the 22 steps rerun from the fetched data with `lotline calibrate
--run`. Four are recorded values with a named source instead of a runner:

- `completion_factors`: a judgment informed by measured ratios (`scripts/dev/completion_factors.py`).
- `adu_undercount_k`: one report per row; the roll and coverage checks that set each k are in
  `scripts/dev/` (`nc_wake_roll_adu_diff.py`, `tx_adu_coverage.py`, `tx_austin_adu_k.py`, `or_adu_coverage.py`,
  `or_portland_adu_k.py`, `mn_adu_coverage.py`, `oh_adu_coverage.py`, `parser_phrase_check.py`).
- `adu_survey_report_rate`: D-041's count (`scripts/dev/calibrate_adu.py`).
- `adu_covariate_centres`: D-083/D-084's screen (`scripts/dev/adu_covariate_screen.py`).

`v5_charlotte_prior` is `frozen`: it serves only the frozen V5 Charlotte test and is never refitted.

**Runnable steps.** `uv run lotline calibrate --run` recomputes every step that has a runner and compares each
value with config; `--write` puts the new values into config and rewrites the lock. The data-only steps are in
`src/lotline/calibrate/data_steps.py`:

- three reproduce config exactly: the baseline ADU share, the ADU reference values and the mortgage rate;
- the eligible-parcel proxy (D-056) was refitted on 2026-11-26 with this command: k 0.971 and σ 0.106 (the
  2026-11-06 run gave 0.998 and 0.060, before more parcel rolls were added). Config now holds the new values.

The ADU chain (phase 4), the missing-middle chain (phase 3) and the three older ADU fits (phase 5) are below.
Development scripts that these steps replaced are in `scripts/archive/` (phase 6; see its README).

## The ADU chain (phase 4)

Six ADU steps rerun from the fetched data with one command:

- `adu_joint`: D-096's Form A + place types fit.
- `adu_partial_share_grid`: the D-097 m_x grid.
- `adu_anchor_slopes`: the D-030 draw terms.
- `adu_calibration_range`: D-060.
- `adu_town_prior_sd`: D-089.
- `adu_new_rule`: D-099's ν and its held-out check.

```bash
uv run lotline calibrate --run --quick --step adu_joint   # minutes: the rule-share grid near today's maximum
uv run lotline calibrate --run --step adu_joint           # the full fit
uv run lotline calibrate --run --write                    # rewrite config and the lock after a full run
```

The fit set they share is library code: `lotline.model.adu_fit_set` (D-079's places, D-096's unknown years,
the owner and age readers, place types) and `lotline.model.adu_refit` (the m_x grid weights, the slopes'
central differences). These used to live only in development scripts that loaded one another by file path.
Heavy steps run in a process pool of `LOTLINE_CALIBRATE_WORKERS` workers (default 4). The grid step returns
the whole CSV; `--run` compares it row by row and `--write` writes it.

## The missing-middle chain (phase 3)

Four missing-middle steps rerun from the fetched data with one command:

- `mm_units_per_project`: D-038's homes per 2-4 unit building.
- `mm_year_spread`: D-092 run 9's per-year spread φ.
- `mm_c4`: D-092 run 10, challenger C4. It fits the mature rate, the place-effect variance and the ramp's
  half-way point.
- `mm_fast_ramp`: D-100's half-way point for locally adopted places.

```bash
uv run lotline calibrate --run --quick --step mm_c4   # minutes: a coarse half-way-point grid
uv run lotline calibrate --run --step mm_c4           # the full fit (5-17 minutes, depending on machine load)
```

The fit sets are library code in `lotline.calibrate.mm.mm_fitsets`: D-092's panel, events, fit and test split, the
always-allowed level set, the year-spread places, and D-038's named places. They used to live only in
development scripts, which now import them. Every fit is deterministic (grid and golden-section search), so a
full run on unchanged tables reproduces config. C4 and D-100 read φ from config rather than refitting it in
the same run.

On 2026-11-26, three steps reproduced config exactly. φ did not. Run 9 fitted 941 pseudo-forecasts of 483
places. Today's tables give 1,379 forecasts of 713 places under the same rules, and φ comes out at 13.03
(12.39-13.70) against run 9's 13.63 (12.85-14.48). Ben chose to update it (2026-11-26), so φ, C4 and D-100
were rewritten with `--write`:

- φ: 13.63 (12.85-14.48) → 13.03 (12.39-13.70).
- Mature rate: 0.0010387 (0.0001316-0.01939) → 0.0016571 (0.0001361-0.01898).
- Ramp half-way point: 4.0 → 4.5 years (range 1.0-6.0 unchanged).
- Place-effect variance, the fast ramp (0.5) and units per project are unchanged.

The missing-middle five-year P50 rises 7-10% in each fitted state: the higher rate is mostly offset by the
slower ramp. The analysis plan's deviation entry of 2026-11-26 has the before and after ranges.

## The three older ADU fits (phase 5)

`adu_state_effect`, `adu_drift` and `adu_ramp_share` were fitted on older model forms. Each now has a runner
that refits it on D-096's form, the same 70 places and 498 place-years as the chain above:

- `adu_state_effect` (D-043/D-044): τ's profile and maximum likelihood on the places with the core
  multiplier folded in, rule shares held at config.
- `adu_drift` (D-091): σ from the persistence forecaster's held-out window, places with history in MN, NC,
  TX and OR.
- `adu_ramp_share` (D-048): the fit at each ramp half-life on D-047's grid against no ramp. The runner stops
  if a ramp wins, because one share can't hold a ramp.

Written 2026-11-26 (Ben approved; PR #549). Ramp and drift came out unchanged. τ fell from 0.565 to 0
(upper bound 1.70 → 0.46), which leaves the five fitted states' results unchanged and narrows a new state's
ADU range.
