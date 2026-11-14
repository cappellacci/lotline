# D-088: ADU place types and where the differences between places sit

Method: D-088 in `docs/analysis_plan.md`, accepted by Ben on 2026-11-14 ("Accept D-088"). Results page:
https://claude.ai/artifact/F8JER4WdEHK6GUn581E4J3

```bash
uv run python scripts/dev/adu_types_refit.py --inputs-only --out reports/adu-place-types
uv run python scripts/dev/adu_types_refit.py --out reports/adu-place-types --workers 7
uv run python scripts/dev/adu_types_refit.py --finish --out reports/adu-place-types   # decision step only
uv run python scripts/dev/adu_types_page.py . reports/adu-place-types/results.html
```

The run is offline from cached tables. St. Paul stays out, ACS goes through `holdout.apply_acs`, and nothing is
unblinded. The first full run stopped on a variable-name error in the final tally, after every table had been
written. The decision step was rerun from those tables with `--finish`; nothing was refitted.

## Result

**Inputs, read before any fit:**
- The 64 fit places are 16 core cities (all 5 states) and 48 suburbs (MN 41, NC 7). There are no towns.
- Counting source: survey 41 (all MN), parser 13, field-flag permit records 10.
- So state, type and counting source largely coincide in this fit set.

**Part 1, the share of the place-effect spread explained (weighted by fit years):**

| | State | Type | Source | All three | Reading |
|---|---:|---:|---:|---:|---|
| Form A | 23% | 26% | 23% | 29% | types matter |
| Form A′ | 12% | 9.5% | 10% | 14% | mixed |

About 70% of the spread is between places of the same state, type and counting source.

**Part 2, decisions by the rule fixed in advance:**
- **A + P (core city against suburb) replaces Form A.**
  - Tier-1 held-out log score +7.2 (2 SE 6.1). Tests A–B are equal. Test D −3.4 (SE 2.6) is inside the allowance.
  - The core-city term is ×3.3 (90%: ×1.7 to ×6.7).
  - Useful states by tier: A 0/0/0, A + P 2/3/3.
- **A′ + P does not replace A′.** Tier-1 log score −0.6 (2 SE 4.4). With owner share in, the core term is +0.85
  (−0.08 to +1.79).
- **No form passes D-075's claim rule.** Which pair counts depends on D-084 (A or A′), still Ben's call.
- **Test D:** types change nothing. Carry-forward still scores best.

## Files

- `place_types.csv`: each fit place's type, metro area, housing units and main counting source.
- `part1_effects.csv`: each place's log effect under A and A′.
- `fits.csv`: every fit.
- `tiers.csv`, `tiers_sensitivity.csv`: the data-tier test, for the four forms and for the 4-type sensitivity.
- `heldout_log_scores.csv`: tier-1 held-out log score per place.
- `test_a.csv`, `test_b.csv`: tests A and B.
- `test_d_places_scores.csv`, `test_d_states.csv`: test D.
- `summary.json`: the decisions and Part 1.
- `run-log.txt`: the run's log.
- `results.html`: the results page.
