### LB-NNN · 2026-11-01 · WS-OH (core change) · Interpolate eligible lots between two real parcel rolls (D-035 addendum)

**Question.** With yearly county rolls (Franklin, Montgomery) and Wake's two rolls, the years between real rolls
were ACS scaled to the rolls. Is a straight line between the real counts better?

**Outputs.**
- `src/lotline/build/eligible.py`: `scale_history` interpolates between rolls; `PARCEL_SOURCES` is updated.
- `src/lotline/schemas.py`: new `denominator_source` value `parcels_interpolated`, schemas 1.9.
- `docs/schemas.md` (regenerated), the `docs/analysis_plan.md` D-035 addendum, and
  `tests/core/test_eligible.py` and `tests/core/test_schemas.py`.

**Why.** Dayton's scaled 2020 came out 1,500 above the real counts on both sides (ACS noise). The rule now
interpolates only strictly between two real rolls; outside them the scaled ACS series is kept.

**Effect (computed in memory, tables not overwritten).**
- OH: 13 jurisdictions, all in Montgomery.
- NC: 13 Wake jurisdictions, 2020–2022. Raleigh rises 1–1.3%; Zebulon and Knightdale about 13%.

**How Claude worked and checked.** Ben chose this as a separate PR in the Montgomery review (decision 5).
Claude re-worked the hand examples in the tests: rolls of 90 (2019) and 110 (2023) give 95 for 2020 and 100 for
2021. Claude diffed OH and NC against the processed tables. This changes a shared contract (schemas) and the NC
thread's numbers, so both are flagged in the PR.
