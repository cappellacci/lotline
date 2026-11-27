### LB-NNN · 2026-11-14 · ADU model · Do place types shared across states help the ADU model carry over to a new state, and where do the differences between places sit?

- **Question:** D-088, accepted by Ben on 2026-11-14 ("Accept D-088"). It was built and run the same day.
- **Outputs:**
  - code: `src/lotline/model/adu_types.py`, `scripts/dev/adu_types_refit.py`, `scripts/dev/adu_types_page.py`;
  - tests: `tests/model/test_adu_types.py`;
  - a small change to `joint_refit.GlobalsA` (type terms per draw);
  - results: `reports/adu-place-types/`, and the page https://claude.ai/artifact/F8JER4WdEHK6GUn581E4J3;
  - D-088's Built, Inputs count and Run notes in `docs/analysis_plan.md`.
- **Result:**
  - **The fit set's types line up with its states.** It has 16 core cities in 5 states and 48 suburbs in MN and
    NC. MN is all suburbs counted by the Met Council survey.
  - **Part 1:**
    - under Form A, state, type and counting source each explain about a quarter of the place-effect spread,
      and together 29%. The reading is "types matter";
    - under A′ the reading is "mixed";
    - about 70% of the spread is between look-alike places.
  - **Part 2:**
    - **A core-city term (×3.3) replaces Form A by the rule.** Tier-1 log score +7.2, 2 SE 6.1. Useful states
      by tier go from 0/0/0 to 2/3/3.
    - **It does not improve Form A′.** Owner share and core city correlate at −0.68.
    - **No tier passes the claim rule.** Test D is unchanged, and carry-forward still wins.
  - **Which form is in use waits on D-084.**
- **What Claude did:**
  - wrote the code and the hand-worked tests;
  - reported the inputs count (types, sources) in the plan before any fit;
  - ran the fits offline;
  - fixed a tally bug in the final step and reran that step from saved tables, with no refit;
  - wrote the plan entries, README and results page.
- **How it was checked:**
  - 11 new hand-worked tests, plus D-084's and D-085's (32 pass across the three files);
  - joint-refit tests pass;
  - Form A and A′ reproduce D-084's numbers to the digit (θ 0.7563/1,000, log-lik −1,347.71; β_o −0.546);
  - the planted type terms are recovered on synthetic data;
  - `compliance_check.py` shows 0 FAIL.
