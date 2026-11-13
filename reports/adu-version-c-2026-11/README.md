# ADU version C (exploratory, not adopted), run 2026-11-13

Plan: `PLAN.md`, committed before any fit (c1315a72). Run: `run/` (branch `ws/adu-version-c`, ba9c17c3), offline,
seed 20261111, 20,000 draws, 31 minutes. St. Paul blind; no `--unblind`. Results page: `results.html`.

## Process notes

- A first start (5:01 ET) was stopped after 3h23m with no fit finished; nothing from it was read. Two exact
  speedups were added (vectorized likelihood; θ's interval skips share candidates whose maximum is below the
  cutoff), each checked equal to `calibrate_adu`'s originals before the rerun.
- A one-fit smoke test of C on the full fit set was run before the main run (to time it); its estimates were
  seen. Nothing in the plan or code changed after it.

## Results (all on PR #417's proposed rows, applied on this branch only)

| | A′ (Form A, new rows) | C |
|---|---|---|
| log-lik (64 places, 491 place-years) | −1,400.1 (4 params) | −1,391.4 (7 params); AIC 11.4 better |
| tier-1 held-out log score, 56 places | −361.7 | −363.4 |
| useful states, tiers 0/1/2 (4 needed) | 0/0/0 | 0/0/0 |
| test A | TX only | TX only |
| test B | NC fail, OH pass | NC fail, OH pass |
| test C | pass in all 5 | not run (no engine) |

C's slopes (all states; multiplier): not by right ×0.26 (SE 0.38 on the log scale), 1 parking space ×0.70
(0.07), 2+ spaces ×0.75 (0.16), other restriction ×1.0 (at the bound), size +0.24 per log lot (0.16).
Leaving out North Carolina: not by right ×0.72, both parking effects 0, other restriction ×0.28. By the plan's
rule, the slopes are not identified beyond North Carolina.

A′ against D-079: θ 0.544 per 1,000 (0.39–0.78) against 0.756; m_o 1.0, m_x 0.7 (was 0.4); 10 events in 3
states (was 5 in 2), so Form B's g is fitted (−0.47, SE 0.27). Form B: useful in MN at tier 2 and NC at tier 1.

Sensitivity (18 `[detached-conditional]` rows as not by right): not by right ×0.30, no tier passes.

Files: `run/fits.csv`, `tiers.csv`, `logscores_tier1.csv`, `test_a.csv`, `test_b.csv`, `test_c_a_prime.csv`,
`event_check.csv`, `events.csv`, `summary.json`, `run-log.txt`.
