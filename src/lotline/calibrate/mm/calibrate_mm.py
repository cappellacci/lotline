"""Calibrate the missing-middle uptake hazard on Lotline's own post-reform places (analysis plan D-038,
pre-registered; D-037 amendment).

For place i in year t at or after its adoption year T_i, at event age a = t − T_i + 0.5:

    y_it ~ Poisson(B_it + θ u_i k_it),   u_i ~ Gamma(mean 1, variance α)
    B_it = β_i g_it                          building that would have happened anyway
    k_it = E_it d_it F_i / F_ref ramp(a)     eligible parcels × dose × feasibility relative to PCR = 1 × ramp

- y: new 2-4 unit buildings (BPS); β_i: the place's mean over T − 3 … T − 1; g_it: its growth in homes outside
  2-4 unit buildings (units_1 + units_5p, centred 3-year mean over its pre-reform mean, capped).
- F = Φ((ln PCR − ln(1 + margin)) / σ) as in `hazard.feasible_share`; the rental duplex PCR is the panel's.
- u is integrated out numerically on a grid of log u (trapezoid weights renormalized to one, plus the mass
  below the grid at u = 0). θ is estimated on the log scale with α and the ramp's half-way point profiled
  out; its 90% interval is {θ : 2(ℓ̂ − ℓ_p(θ)) <= 2.706}.

D-042 (the second pre-registered fit) keeps this likelihood and changes its inputs: the event is the first
in-window rise in a place's unit cap, the outcome counts only the building classes above the prior cap
(`prior_cap`, `outcome_classes`, `retarget`), the baseline follows comparison places (`comparison_series`,
`baseline_series`), and θ_i = θ exp(b z_i) with z the centred log builder capacity (`fit_capacity`).

The code is split by method step (modularity step 3), and this module re-exports every name, so
`calibrate_mm.fit` and the like keep working:

- `places`: the `Place` inputs, baselines, growth index and dispersion test;
- `likelihood`: the place likelihood (u on a grid; the κ and φ forms) and `loglik`;
- `year_spread`: fitting φ or κ (`fit_noise`, `fit_kappa`);
- `fit`: θ, α and the half-way point, and the five-year ramp profile;
- `capacity`: D-042's classes, comparison baseline and builder capacity;
- `backtest`: predictions and the V4 leave-one-place-out test (`loo_backtest`);
- `state_backtest`: D-054's statewide backtest, verdicts, held-out log score and τ;
- `challengers`: D-092's standards events, level component and prior (C4), C1, C3 and model choice.

Only NumPy, pandas and the standard library; tests use hand-worked examples
and simulated places (tests/calibrate/test_calibrate_mm.py).
"""

# ruff: noqa: F401
from __future__ import annotations

# The original module's own imports: some callers read them through it (cal.replace, cal.Z_95).
import functools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from lotline.calibrate.adu.calibrate_adu import CHI2_90, LOG_ALPHA, Z_95, _golden_max, gh_log_nodes
from lotline.model import rule_tags
from lotline.model.hazard import feasible_share, ramp

from .backtest import (
    benchmark_total,
    loo_backtest,
    predict_total,
    realized_hazard,
    score,
)
from .capacity import (
    CAPACITY_SLOPES,
    CLASS_COLUMNS,
    POOL_MIN,
    CapacityFit,
    baseline_series,
    capacity_z,
    comparison_series,
    event_year,
    fit_capacity,
    outcome_classes,
    prior_cap,
    retarget,
    scaled,
)
from .challengers import (
    C4_WIDENING,
    CLASS_SIZES,
    DOSE_CLASSES,
    LEVEL_AGE,
    LEVEL_POOL_MIN,
    S_DOSE,
    SE_MARGIN,
    Event,
    _new_rows,
    classify_event,
    conditional_z,
    first_event,
    fit_level,
    level_places,
    level_prior,
    level_rate,
    not_yet_treated_series,
    paired_delta,
    retarget_events,
    select_model,
    standards_classes,
    standards_variant,
    standards_year,
)
from .fit import (
    SCENARIO_AGES,
    Fit,
    FiveYearFit,
    _best_alpha,
    _best_at_half,
    _best_theta,
    fit,
    five_year_profile,
    log_prior_term,
    profile_theta,
    ramp_mean,
)
from .likelihood import (
    KAPPA_NONE,
    LOG_KAPPA,
    Stack,
    _interval,
    _lg,
    _log_pois,
    _loglik_w,
    _loglik_y,
    _nb_core,
    _phi_on,
    _place_loglik_w,
    _place_loglik_y,
    _u_grid,
    _w_mixed,
    _ylogmu,
    loglik,
    place_loglik,
)
from .places import (
    _V,
    ALPHA_LOCAL,
    ALPHA_POISSON,
    DISPERSION_P,
    G_CAP,
    HALF_GRID,
    LOG_THETA,
    LONG_YEARS,
    SLOPE,
    ZERO_FLOOR,
    Place,
    _gamma_q,
    centred_mean,
    chi2_sf,
    dispersion_test,
    feasibility_ratio,
    growth_index,
    place_inputs,
)
from .state_backtest import (
    GH_NODES_STATE,
    GH_THETA,
    TAU_GRID,
    _w_draws,
    _year_draws,
    benchmark_places,
    heldout_log_score,
    no_effect_log_score,
    predict_places,
    state_loglik,
    state_total,
    tau_profile,
    tau_summary,
    verdict,
)
from .year_spread import (
    KappaFit,
    baseline_scores,
    fit_kappa,
    fit_noise,
    nb_year_terms,
    with_kappa,
    with_phi,
    with_phi_by,
)
