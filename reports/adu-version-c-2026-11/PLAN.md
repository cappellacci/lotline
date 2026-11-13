# ADU version C: separate rule-detail effects (exploratory, not adopted)

Written 2026-11-13, before any fit, on branch `ws/adu-version-c`. This is not a D-entry and nothing here
goes to config on `main`. Ben asked for an overnight test model once the WS-ADU-RULES research finished
(2026-11-12: "feel free to run whatever test model"); this file fixes what that test is before it runs.
It is exploratory because the idea came from looking at uptake by rule detail on 2026-11-12, after the
D-079 refit was read. PR #416 (D-083, proposed) screens other place factors with the same likelihood; this
test does not use or pre-empt it.

## Data

- **Rule rows:** the 153 proposed rows of PR #417 (`docs/research/ordinances/adu-fit-rules-proposed-2026-11.csv`),
  including Ben's seven rulings of 2026-11-13 and the single-coder rows, applied on this branch only by
  `scripts/dev/apply_adu_rules_proposed_2026_11.py`:
  - each of the 65 places' own local ADU rows (`<ST>-<geoid>-…`) is replaced by its proposed rows; state-law
    rows (NC S.L. 2026-59, Oregon SB 1051 / HB 2001) are untouched;
  - a superseded row ends on its successor's effective date;
  - `coverage_zones` carries over from the existing row with the same id, else from the place's existing
    row in force on the proposed row's effective date.
  - Open items in #417 stay as the research coded them: Wayzata before 2022 (no ADUs, flagged), the six
    conflicts with existing rows (the proposed value is used), Ramsey's 2023 lot minimum, Austin HOME's date.
- **Fit set and windows:** as D-079 builds them (`adu_joint_refit.fit_set`, 2016-2025, Austin to 2023, San
  Antonio from 2021), from the new rows. Differences from D-079's `fit_set.csv` are reported.
- **Holdouts:** St. Paul is out of every fit and score (its rules are coded; its permits are never read).
  No `--unblind`. Offline only.

## The models compared (all on the new rows)

- **A′:** Form A (D-048, `calibrate_adu.fit3`) refit on the new rows: θ, α, m_o, m_x. This separates
  "new data" from "new structure".
- **C:** Form A's Poisson-gamma likelihood with the rule share c of each rule in force replaced by

  c = exp(β_br·[not by right] + β_p1·[1 parking space] + β_p2·[2+ spaces] + β_x·[any other restriction]),

  and the place's base multiplied by (lots / median lots of the fit set)^β_s.
  - Owner occupancy has **no effect** (as A's refit found, m_o = 1), so its slope is not fitted.
  - **Signs fixed in advance:** β_br, β_p1, β_p2, β_x ≤ 0 (a restriction never raises uptake). β_s is free.
  - "Other restriction" = no detached ADUs or a size cap under 600 sq ft (`restriction_fields`).
  - Parking levels: `parking_min_per_unit` 0 / 1 / 2+; a rule whose parking "depends" (for example on size)
    counts as 1; a blank parking field enters as a blank-field combination (D-022), and "restricts" counts
    as 1 space.
  - A blank by-right or other field enters as a blank-field combination, as in Form A.
  - Fit by maximum likelihood (Nelder-Mead, best of 5 starts), θ's 90% interval from the observed
    information, so θ's draws match Form A's treatment. β's uncertainty is not carried into the draws
    (Form A does not carry m_o's or m_x's either); this narrows C's ranges and is a stated limit.
  - Tier 0 (rules borrowed by type): handbook and owner-only rules take c = 1, the other types take the
    mean c over the training places' restricted rule-years.
- **Form B** runs alongside as in D-079 (needed by the scoring code); it is reported, not compared.

## Events

The in-window rule-change events are rebuilt from the new rows by `joint_refit.events`. If they reach
D-079's bar (8 events in 3 states) they are reported with C's predicted against observed steps. C has no
separate event term: a rule change moves c through the slopes, so the events test the slopes.

## Scores (the same as D-079)

- Fit: log-likelihood and AIC for A′ and C on the same place-years.
- D-075 data tiers 0-2, leave one state out, claim rule (4 of 5 states useful).
- Test A (new places), test B (roll counts).
- **Test C is not run for C:** the scenario engine has no version C. Test C for A′ is run as in D-079.
- Event check: predicted against observed step per event.

## Sensitivity (one, reported)

- Rows tagged `[detached-conditional]` (18 rows: by right only for some ADU forms) treated as **not** by
  right.

## What counts as a result

Nothing here is adopted. The read is: does C pass more tiers or tests than A′, by how much does the fit
improve per added parameter, and are the slopes sizeable and stable across the leave-one-state-out fits?
A slope that flips size between folds, or that only Minnesota or only Oregon identifies, is reported as
not identified. Any adoption needs Ben to accept the #417 rows and a dated method entry first.
