# D-092 run 13: buildings per project (deviation (d))

Pre-registered in `docs/analysis_plan.md`, deviation 2026-11-15 (d). Ben: "Yes, run it" (2026-11-15).
Descriptive only: no fit, nothing to config, run 11 stands.

    uv run python scripts/dev/mm_project_size_d092.py --out reports/mm-d092/run13-projects
    uv run python scripts/dev/mm_projects_page.py

## Result

| Grouping | Projects | Buildings | Mean size | Inflation E[S²]/E[S] | In projects of 3+ |
|---|---|---|---|---|---|
| Same lot (15 sources) | 4,841 | 7,720 | 1.60 | 12.8 | 34% |
| Same day (20 sources) | 5,341 | 9,791 | 1.83 | 5.3 | 42% |

- **Verdict by the rule:** same-lot inflation ≥ 1.5, so **the compound (project) model goes back to Ben**.
  Same-day is also far over 1.5.
- **By source:** Minneapolis (1.13 by lot), Cleveland (1.36) and Cincinnati (1.41) are under the bar by lot.
  Austin (23.8), College Station (22.0), Wilmington (16.6) and Columbus (11.3) are far over. Texas's clusters
  fit its lumpiness in run 12.
- **The guess was wrong:** most 2–4 unit buildings are one per project, but a third or more come in clusters.
- **Same lot wasn't a lower bound.** The plan called it the low estimate. Pooled, it came out higher than same
  day, because one parcel can hold a whole build-to-rent community permitted over a year (the largest: 202
  duplex buildings on one Austin parcel). Both are far over the bar, so the verdict holds either way.
- **Reported, not selected** (a check after the run): without each city's top 1% of projects, same-lot
  inflation is still 3.0 (Austin), 9.3 (College Station), 8.7 (Wilmington) and 3.7 (Columbus).
- Franklin and Montgomery counties' files have no typed 2–4 unit permits (ADUs only), so they add nothing.

## Files

- `summary.json`: per source and pooled, for both groupings; the verdict.
- `coverage.csv`: per source, share of all permits with a parcel ID and dated to the day (the dry run's table).
- `run-log.txt`: the run's printout.
- `results.html`: the results page (https://claude.ai/artifact/BvoadqpTCF3itcSBYUYdgq).

Holdouts: permits through `holdout.apply`; St. Paul, Ramsey, Charlotte and Mecklenburg also dropped by GEOID
and source. Cached tables only. Nothing unblinded.
