# D-083 screen rerun on PR #417's ADU rule rows, 2026-11-13

Plan: `PLAN.md`, committed before the run (90e70cdf). Branch `ws/adu-screen-new-rows` = `ws/adu-rules-config`
(#417's rows in config) + PR #416. Commands:

```bash
uv run python scripts/dev/adu_covariate_screen.py --out reports/adu-covariate-screen-new-rows --m-owner 1.0 --m-other 0.7
uv run python scripts/dev/adu_covariate_screen.py --out reports/adu-covariate-screen-new-rows --m-owner 1.0 --m-other 0.7 --influence
```

Offline, 16 minutes. Fit set 64 places, 491 place-years (D-083: 395). St. Paul out; no `--unblind`.

## Result (within-state version, D-083's bars)

| Factor | β per SD, old → new | Holm p, old → new | α falls, old → new | Verdict, old → new |
|---|---|---|---|---|
| X1 Owner-occupied share | −0.71 → −0.72 | 0.083 → 0.117 | 16% → 19% | candidate → **misses the p bar** |
| X2 Homes built before 1960 | +0.59 → +0.93 | 0.095 → 0.0005 | 11% → 28% | candidate → **candidate, much stronger** |
| X3–X5, R1, R2 | | all ≥ 0.47 | ≤ 4% | no → no |

- **Housing age** leave-one-place-out: β +0.79 to +1.03 over 57 drops, sign and p < 0.10 kept in all 57. Robust.
- **Owner share pooled** (across states, not a D-083 bar): β −0.95 (−1.32, −0.59), α falls 35% (2.63 → 1.72),
  Holm p 0.0004. D-083 run: −0.81, 26%. It remains the one factor that explains differences between states.
- α itself is larger on the new rows (within-state null 1.77 against 1.43), so places differ more once the
  rules are coded in detail.

## Caveats

- The rule rows are not on `main`. Putting them into config breaks 22 state reform tests (74 local-path
  sources, 3 rows without a source, 35 renamed rows, 43 overturned values in 25 rows). These need resolving
  before the rows are accepted; values may still change, and so may these numbers.
- The `--m-owner/--m-other` flags were added to the script for this rerun; defaults keep D-079's values.
