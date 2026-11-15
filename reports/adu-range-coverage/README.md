# ADU range coverage: are the ranges the right width?

Asked by Ben on 2026-11-15 ("Range coverage check"), after D-088 was rescored on the checked rule rows (#437).
A diagnostic, not a method change. No new parameter, nothing written to config.

```bash
# from the main checkout (cached ACS requests are keyed with CENSUS_API_KEY from .env)
PYTHONPATH=<worktree>/src .venv/bin/python <worktree>/scripts/dev/adu_range_coverage.py --out <worktree>/reports/adu-range-coverage --workers 7
uv run python scripts/dev/adu_range_coverage_page.py . reports/adu-range-coverage/results.html
```

**What it does:** each state is left out, and Forms A and A + P are refitted on the others (checked rows,
64 places, 491 place-years). Each held-out place's total over its fit years is drawn at tier 1, using the same
inputs as D-088's held-out log score (`joint_refit.predict`). For each place it records:
- whether the observed total is inside P10–P90;
- the randomized percentile (PIT), which corrects for small counts.

Each state's total is also redrawn with each source of spread switched off.

## Result (A + P)

- **Overall the place ranges are about right, slightly narrow.** P10–P90 holds 83% of the places. The randomized
  middle 80% holds 69%, with 17% below and 14% above. The SE is about 5 points (64 places, 43 of them in MN).
- **By type they miss in opposite directions:**
  - Core cities: 88% in the middle 80% and 69% in the middle 50%, so too wide. n = 16, about 1.5 SE.
  - Suburbs: 62% in the middle 80%, so too narrow.
  - Core cities hold 97% of the observed ADUs.
- **What makes a state total wide** (P90 ÷ P10):

  | State | Counted places | Everything | Without the state level | Without place luck | Shared parameters only |
  |---|---:|---:|---:|---:|---:|
  | MN | 43 | ×9.2 | ×6.1 | ×4.3 | ×2.6 |
  | NC | 13 | ×24.4 | ×15.1 | ×8.6 | ×5.0 |
  | TX | 3 | ×24.8 | ×19.5 | ×5.2 | ×3.6 |
  | OR | 4 | ×27.3 | ×20.2 | ×6.2 | ×4.0 |

  Place-to-place luck is the largest source wherever a few cities make up the total.
- **Over time:** without drift, about half of places fall in the middle 80% (test D and D-091 with no drift).
  With D-091's drift, which the engine now uses, it is about 80% (F0: 79%).

**Suggests:**
- a separate place-luck spread (α) for core cities and suburbs, which needs its own entry before any fit;
- own counts for the biggest core cities, which the engine already uses where they exist (D-093).
