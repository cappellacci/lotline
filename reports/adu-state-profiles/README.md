# D-089: ADU state profiles, evidence coverage, and the town prior

Method: D-089 in `docs/analysis_plan.md`, accepted by Ben on 2026-11-14 ("Accept D-089"). Results page:
https://claude.ai/artifact/GoxSAAjVEv2szddSuRSJEb

```bash
uv run python scripts/dev/adu_state_profiles.py --out reports/adu-state-profiles
uv run python scripts/dev/adu_profiles_page.py . reports/adu-state-profiles/results.html
```

The run is offline. The profiles read no ADU count. Part 4 uses the scenario's own inputs (holdout-filtered).
St. Paul is left out of the totals, and nothing is unblinded.

## Result

- **Every state is labeled "mostly outside the places the model was fitted on".**
  - Outside the evidence: MN 63%, NC 74%, OH 89%, OR 77%, TX 93% of eligible lots.
  - Towns are 9–30% of that. The rest is beyond the fit's range for the type, mainly on price and size.
- **Towns give 1–5% of each state's expected ADUs.** So the town prior (90% ×0.30–×3.3) moves no P90 by more
  than 3%.
- **The share of expected ADUs from places outside the evidence:** MN 42%, NC 25%, OH 47%, OR 65%, TX 96%.
- **Statewide ADU permits, 2027–2031, current rules, Form A + P with the town prior** (P10–P50–P90):
  - MN 644–1,000–1,951
  - NC 2,898–4,269–7,681
  - OH 759–1,278–2,881
  - TX 3,244–5,482–11,459
  - OR 3,031–4,021–6,846
  - These are a sensitivity: no state effect and no market-path draws.

## Files

- `jurisdictions.csv`: every jurisdiction's type, population, lots, value, rent, owner share and evidence flags.
- `profiles.csv`: the profile by state and type, plus the fit set.
- `evidence.csv`: each state's share of lots outside the evidence, and its label.
- `scenario_places.csv`: Part 4's places with their type and evidence flag.
- `summary.json`: the fit ranges, what drives the flags, the totals and the A + P values used.
- `run-log.txt`: the run's log.
- `results.html`: the results page.
