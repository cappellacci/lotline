# D-083 screen on the final ADU rule rows, 2026-11-13

Asked by Ben ("Rerun screen") after the source check and his ruling on four values (PR #419). Same plan as
`../adu-covariate-screen-new-rows/PLAN.md`; only the rows and Form A's multipliers differ.

Branch `ws/adu-screen-new-rows` with `ws/adu-rules-config` at ef37063f merged in. Form A refitted on these rows
first (`adu_joint_refit.fit_a_task`, all 64 places, 999 s): θ 0.503 per 1,000 (0.36–0.78), α 2.65, m_o 1.0,
m_x 0.8 (90% range 0.7–0.8; 0.7 on the unchecked rows). Commands, run from the main checkout for `.env`:

```bash
uv run python scripts/dev/adu_covariate_screen.py --out reports/adu-covariate-screen-final-rows --m-owner 1.0 --m-other 0.8
uv run python scripts/dev/adu_covariate_screen.py --out reports/adu-covariate-screen-final-rows --m-owner 1.0 --m-other 0.8 --influence
```

Offline. Fit set 64 places, 491 place-years. St. Paul out; no `--unblind`.

## Result (within-state version, D-083's bars)

| Factor | β per SD, unchecked → final | Holm p | α falls | Verdict |
|---|---|---|---|---|
| X1 Owner-occupied share | −0.72 → −0.76 | 0.117 → 0.081 | 19% → 21% | misses → **candidate (narrow)** |
| X2 Homes built before 1960 | +0.93 → +0.95 | 0.0005 → 0.0004 | 28% → 30% | candidate → **candidate** |
| X3–X5, R1, R2 | | all ≥ 0.52 | ≤ 3% | no → no |

- Leave-one-place-out, 57 drops each: owner share β −1.05 to −0.66, housing age β +0.84 to +1.06; sign and
  p < 0.10 kept in all 57 for both. Largest moves: Orono, Dayton (X1); Asheville, Orono (X2).
- Pooled owner share: β −0.99 (−1.36, −0.62), α falls 36% (2.74 → 1.76), Holm p 0.0003.

## Sensitivity: owner share's pass rests on m_x

Same final rows with m_x held at 0.7: owner share Holm p 0.110 (misses), housing age 0.0005. So the source-check
corrections moved owner share from 0.117 to 0.110, and the refit m_x (0.8) moved it to 0.081. Its within-state
pass is marginal; its pooled role (the state gap) is not.
