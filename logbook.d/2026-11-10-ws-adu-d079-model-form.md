### LB-NNN · 2026-11-10 · Method: D-079 (proposed), the model form for the D-075 ADU joint refit (docs only)
- **Question:** Which model form should the D-075 joint refit use, D-048 or D-047's approach 3 with rule-change
  terms, and how do the data-tier test and tests A–C choose between them, fixed before any fit?
- **What I did:**
  - Wrote D-079 in `docs/analysis_plan.md`, marked **Proposed, for Ben's review**. It defines the two forms
    exactly:
    - Form A is D-048 as adopted.
    - Form B is approach 3 plus a dose term g d_it with the place's mean dose d̄_i, so g is identified only from
      in-window rule changes. The events are built by code, and g is estimated only with 8 or more events in
      3 or more states.
  - It states the shared data: central k from D-078 and permit-level remainders from #375.
  - It says how each tier of the D-075 data-tier test, tests A–C and the D-049 log score are scored for each
    form, and fixes a decision rule. The proposed pick is Form A, with Form B as the pre-registered challenger.
  - Checked that D-079 was unused on `main` and in every open PR.
- **Inputs:** D-037, D-047, D-048, D-049, D-053, D-074, D-075, D-078 and the merged NC reports. No fit output
  newer than D-053 was read.
- **Outputs:** `docs/analysis_plan.md` (D-079).
- **Decisions:** none. D-079 is proposed for HANDOFF once Ben accepts it.
- **AI:** Claude Code drafted the entry overnight, with Ben asleep. Its numbers were checked against D-047,
  D-048, D-049 and D-053 as written. No fit, run or data read.
- **Open / next:** Ben's review. Then the rebuild, the joint refit under the accepted form, and the tests.
