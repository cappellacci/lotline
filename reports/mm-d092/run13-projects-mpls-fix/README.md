# D-092 run 13, rerun after the Minneapolis permit fix (2026-11-17)

Ben: "rerun run 13's Minneapolis row" (2026-11-17), after #451 (Closes #450) stopped the Minneapolis adapter
typing roof, remodel and addition permits on existing duplexes and fourplexes as new 2–4 unit buildings. Same
script, groupings and rule as run 13 (`reports/mm-d092/run13-projects/`, kept unchanged); main at cd091451.

    uv run python scripts/dev/mm_project_size_d092.py --out reports/mm-d092/run13-projects-mpls-fix
    uv run python scripts/dev/mm_projects_page.py --dir reports/mm-d092/run13-projects-mpls-fix

| | Run 13 (15 Nov) | Rerun (17 Nov) |
|---|---|---|
| Minneapolis, same lot: projects / buildings / inflation | 979 / 1,042 / 1.13 | 176 / 179 / 1.03 |
| Minneapolis, same day: projects / buildings / inflation | 734 / 1,044 / 2.07 | 161 / 181 / 1.28 |
| Pooled same lot: projects / buildings / inflation / in 3+ | 4,841 / 7,720 / 12.8 / 34% | 4,038 / 6,857 / 14.3 / 39% |
| Pooled same day: projects / buildings / inflation / in 3+ | 5,341 / 9,791 / 5.3 / 42% | 4,768 / 8,928 / 5.6 / 44% |
| Verdict | raise the compound model | the same |

- Every other source's numbers are identical to run 13.
- **Check:** Minneapolis's permit-file 2–4 unit buildings 2017–2025 now total 175 against Census BPS's 165
  (before the fix, about 1,040).
- The building-equivalent check (`run13-projects/check_building_equivalents.json`) was not rerun.
- Ben's decision stands: clustering is recorded as the reason for missing middle's wide ranges; no project model.

Results page (same link as run 13, updated): https://claude.ai/artifact/BvoadqpTCF3itcSBYUYdgq
Offline, cached tables only; St. Paul, Ramsey, Charlotte and Mecklenburg left out as in run 13.
