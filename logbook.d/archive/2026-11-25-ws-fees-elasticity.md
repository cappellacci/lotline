### LB-NNN · 2026-11-25 · Review · Fees: elasticity everywhere (thread 17, part A)

- **Question:** Should places with a parcel roll keep the lot-feasibility fee channel, whose answers were
  4–40 times the elasticity route's?
- **Outputs:** `config/params/fees.yaml` (`fee_feasibility_channel` = 0); `src/lotline/model/scenarios/fees.py`
  (`pct_change`, docstring); `tests/model/test_fee_scenario.py`; `src/lotline/app/template.html` (fee card);
  `docs/model_and_assumptions.md`; `docs/analysis_plan.md` deviation entry (2026-11-25); review log rows
  A17–A19.
- **Decision:** Ben, 2026-11-25: "Elasticity everywhere". Proposed HANDOFF decision in the PR.
- **What Claude did and how it was checked:** Claude Code reviewed `fees.py`, measured the two channels per
  place, and put the choice to Ben. It added a config switch (off) rather than deleting the channel. Tests
  check that a place with parcel data takes the same %Δ as one without, and that the channel still works when
  switched on. Ran `lotline results` for MN and OR against `main` after #525: only the fee scenarios moved
  (MN benchmark P50 862 → 618, OR 642 → 314).
