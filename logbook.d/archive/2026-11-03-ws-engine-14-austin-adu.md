### LB-NNN · 2026-11-03 · Validation: Austin ADU counts after HOME, which fits use 2024+?
- **Question:** HOME phase 1 (applications from 2024-02-05) moved Austin's second and third homes out of the
  ADU permit class (R-102) into R-101 and R-103 permits described "TWO UNIT RES" or "THREE UNIT RES" (D-038
  Austin check, PR #272 §6.6). Does any ADU fit, estimate or check count Austin (4805000) ADUs from 2024 on?
- **What I did:**
  - Traced every place Austin ADU counts enter: `scenarios/adu.py` (`_is_adu`, `observed_adu_counts`,
    `adu_share_of_one_unit`), `model/calibrate_adu.py`, `model/estimate_adu.py`, `model/backtest.py`, and
    the dev scripts `calibrate_adu.py`, `estimate_adu.py`, `estimate_pooled_adu.py`,
    `adu_current_rules_check.py`, `adu_baseline_share.py`.
  - Read each Austin year window on main and on the open engine branches (#266, #271, #274, #275, #272).
  - Scanned every committed CSV under `reports/` on main, #266, #274 and #275 for Austin rows with
    year ≥ 2024 (none).
- **Inputs:** main at fa3994a; `config/params/adu.yaml`, `config/params/aggregate.yaml`,
  `config/params/v1_excluded_places.csv`; `reports/mm-d038/austin_check.csv` on `ws/engine-14-mm-anchor`.
  No data was read and no model was run.
- **Outputs:** this fragment; the note in the PR description.
- **Findings:**
  - **No ADU fit is affected.** Every Austin ADU window ends in 2023 or earlier:
    - D-019 anchor fit (`scripts/dev/calibrate_adu.py`): `FIT_YEARS_AUSTIN = range(2016, 2024)`, the same
      on #274 and #275, including the D-039/D-040 place lists.
    - D-023 and D-025 (`estimate_adu.py`, `estimate_pooled_adu.py`): the Austin transport rows are 2016–2023.
      On #266/#271 Austin joins the D-025 sample as `range(2016, 2024)`, commented "HOME ended the R-102 ADU
      flag in 2024".
    - The scenario's observed-ADU floor: `adu_observed_first_year`–`adu_observed_last_year` = 2019–2022.
    - `baseline_adu_share_of_one_unit` (Austin 1,371 of 17,928): 2019–2022.
    - `adu_current_rules_check.py`: 2016–2022.
    - V1 backtest: Austin is in `v1_excluded_places.csv`, and V1 scores BPS units, not ADU classes.
    - V5: Charlotte and St. Paul only.
  - **Where the relabelling does matter is missing middle, not ADUs.** The D-038 Austin excess (2024–25) is
    mostly relabelled ADUs, as PR #272 §6.6 already says.
  - **If an Austin ADU window is ever extended past 2023**, `building_type_std == 'ADU'` would show about
    90 instead of about 191 in 2024, and 9 instead of about 376 in 2025 (R-102 against R-102 + R-103). The
    proposed rule is in the PR note.
- **Decisions:** none needed. Proposed for HANDOFF, as a note under D-019 and D-025: Austin ADU counts stop at
  2023 because HOME removed the R-102 class; any extension must first adopt a post-HOME counting rule.
- **AI:** Claude traced the code and the branch diffs with grep and `git show`, and wrote this fragment.
  Checked by reading each year constant in place on every branch, and by scanning the committed reports.
- **Open / next:** none for ADUs. The missing-middle side belongs to PR #272.
