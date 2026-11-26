"""Missing-middle estimation panel (analysis plan D-024, pre-registered; this module runs no estimate).

The panel D-024 estimates on: one row per place and year, 2010-2025, for every permit-issuing place in the
four reform states (MN, NC, OH, TX) with at least `mm_estimation_min_population` people, plus every place
with a coded missing-middle rule. Columns:

- **Outcome** `y`: new homes permitted in 2-4 unit buildings. From Census BPS (`units_2 + units_3_4`, the
  same measurement in every state and year; townhouses are 1-unit in BPS and stay out) or, for a local check,
  from a permit source's U2 / U3_4 / DTQ rows. A place-year missing from BPS is missing (NaN), never 0.
  `y_buildings` counts the buildings.
- **Exposure** `eligible`: missing-middle eligible parcels (rule 1.1, D-014: single-family houses and vacant
  single-family-zoned lots), from the nearest roll.
- **Treatment and dose:** from coded `missing_middle` rows in `config/reforms/*.csv` (in force on 1 July):
  dose = units grade × approval grade × coverage (`rule_dose`). Units allowed 2 / 3 / 4+ grade 1/3, 2/3, 1;
  approval by right 1, by permit `mm_dose_grade_permit`; coverage of single-family zones as in D-021. Blank
  fields take coded shares (D-022). Adoption year `T` = the first year a rule with P(by right) >= 0.5 is in
  force on 1 July (NaN if never).
- **Status** of each place: `treated` (has T), `coded_not_treated` (a coded rule, never by right) or `uncoded`
  (no coded rule: unknown under D-022; D-024 asks Ben whether these serve as comparisons).
- **Pre-adoption modifiers** (year T - 1; NaN for places never treated): `pcr` (price-to-cost of a rental
  duplex from the pro forma), `log_value` (log median home value: the existing-use value a teardown must
  beat, C46), `pre_permits` (2-4 unit homes per 1,000 eligible parcels, mean of T - 3 ... T - 1, C06) and
  `hh_growth` (log ACS households T - 1 over T - 6, C04).
- `adu`: P(a by-right ADU rule is in force) that year (the ADU-on-the-same-lot substitution, C47), from the
  place's coded ADU rules; uncoded places take the mean of coded places in their state and size band.
- `rate` (national 30-year mortgage rate), and the placebo / substitution outcomes `units_1` and `units_5p`.

The code is split by method step (modularity step 3), and this module re-exports every name, so
`estimate_mm.build_panel` and the like keep working:

- `panel`: dose and adoption year, counts, modifiers, the ADU prior, `build_panel` and the smoke counts;
- `estimate`: the design, PPML, the negative binomial and random-effects fits, the bootstrap and summaries;
- `checks`: randomization inference, added homes, the reported checks and `transport_predict`.

St. Paul (V5 blind test) and Charlotte with every place reporting under Mecklenburg County (holdout from
2023-06-01, D-012) are excluded entirely. Only NumPy and pandas; tests use synthetic tables
(tests/calibrate/test_estimate_mm.py).
"""

# ruff: noqa: F401
from __future__ import annotations

# The original module's own imports: some callers read them through it (mm.rule_dose).
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from lotline.model.estimate_adu import nearest_roll
from lotline.model.mm_rates import _mm_coverage, blank_shares, plex_price_to_cost, rule_dose

from .checks import (
    PACKAGE,
    _delta,
    _interval,
    _pred_row,
    _ri_one,
    _safe,
    added_homes,
    check_inside,
    check_leads,
    check_leave_one_out,
    check_outcome,
    check_placebo_dates,
    imputation_effects,
    randomization_inference,
    reassign,
    transport_predict,
)
from .estimate import (
    BIN_NAMES,
    LEADS,
    LOG_A_BOUND,
    MAIN_MODIFIERS,
    NB_MAX_ITER,
    NB_NAMES,
    NBFit,
    REFit,
    _damped_newton_step,
    _re_parts,
    bootstrap,
    build_design,
    estimate,
    fit_nb,
    fit_re,
    overall,
    poisson_start,
    pooled_panel,
    summary,
    treated_dropped,
    year_code,
)
from .panel import (
    BPS,
    CHARLOTTE,
    EVENT_BINS,
    MECKLENBURG,
    MM_TYPES,
    MODIFIERS,
    ST_PAUL,
    STATES,
    MMPanel,
    _excluded_holdout,
    adoption_year,
    bps_counts,
    build_panel,
    event_bin,
    fill_adu_prior,
    local_counts,
    pre_permit_rate,
    rules_by_year,
    smoke_counts,
)
