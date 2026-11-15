# ADU engine switch to Form A + place types (D-088, D-089)

Development runs of the Handbook ADU scenario (`scenarios.adu.run`) on real data, before and after the engine
began reading place types. Not a published result. Page: https://claude.ai/artifact/Wn5ktV2Hvo26TQdTEseNci

- `totals_d053.csv`: the engine before the switch (D-053: θ 0.308 per 1,000, α 2.317, m_x 1.0, no types).
- `totals_types.csv`: the engine as switched (θ 0.448 per 1,000 for a suburb, α 1.55, m_x 0.4, core-city
  term +1.199, town prior sd 0.729).
- `totals_types_mx1.csv`: as switched but with m_x held at 1.0. This splits the change into its two causes.
  No fit has m_x 1.0 with types, so it is not a forecast.
- `by_type.csv`, `by_type_mx1.csv`: mean five-year current-rules ADUs and ADU permits added, by state and
  place type.
- `results.html`: the page, built by `scripts/dev/adu_types_engine_page.py`.

How the runs were made:

- `scripts/dev/adu_types_engine_check.py` (`--mx 1.0` for the split), run offline with origin 2025, window
  2027–2031, 1,000 draws and seed 20261020.
- Inputs: `places_from_store` reading the holdout-filtered tables, for MN, NC, OH, TX and OR.
- St. Paul (V5, still blind) is left out.
- The "before" run used this branch's code before the engine edits (commit d36bd9fe's engine).

Additional homes, 2027–2031, P50 (P10–P90):

| State | D-053 | Types, m_x 1.0 | Types, m_x 0.4 |
|---|---:|---:|---:|
| MN | 286 (132–667) | 412 (199–995) | 634 (318–1,463) |
| NC | 139 (46–424) | 215 (77–655) | 575 (252–1,516) |
| OH | 236 (78–927) | 349 (121–1,608) | 422 (149–1,901) |
| TX | 1,902 (819–4,922) | 3,744 (1,488–10,254) | 4,809 (1,925–13,788) |
| OR | 26 (10–72) | 11 (5–28) | 29 (10–103) |

Two approximations remain until they are redone for this fit:

- The anchor's judgment slopes (`adu_anchor.yaml`) are still D-053's.
- θ's lognormal width comes from its profile interval. Only the correlation and α's information come from
  the new fit's observed information.
