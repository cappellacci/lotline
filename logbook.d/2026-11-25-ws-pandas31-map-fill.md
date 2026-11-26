### LB-NNN · 2026-11-25 · Review · pandas 3.1: `.map(dict).fillna(text)` made safe (unblocks the pandas upgrade)

- **Question:** What still breaks under pandas 3.1 after the Austin fix (#528)?
- **Outputs:** `.astype("str")` between `map` and `fillna` in `mn/metc_permits.py`, `mn/mpls_permits.py`,
  `mn/stpaul_permits.py`, `oh/oh_parcels.py` (2), `or/portland_permits.py`, `or/rlis_parcels.py`,
  `tx/austin_adu_roll.py` and `rule_agents/mm/places.py`.
- **Decision:** Ben, 2026-11-25 (overnight): "go with your suggested order"; item 3. Merge left to Ben.
- **What Claude did and how it was checked:** reproduced the failure in a pandas 3.1.0 environment: when every value
  misses the lookup, `.map` returns an all-null `double[pyarrow]` column and `fillna("UNKNOWN")` raises
  `ArrowInvalid`; `.astype("str")` first fixes it and changes nothing on 3.0.6. With this branch's code: pandas 3.0.6,
  1,827 adapter/core/build/config/rule-agent tests pass; pandas 3.1.0, those plus the app tests (1,903) and the rest
  of the suite (954) pass. Dependabot's pandas 3.1 PR (#236) can be reopened after merge.
