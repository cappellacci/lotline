#!/usr/bin/env python3
"""V2-style check of the ADU hazard against places that already allow ADUs (D-019, D-022).

    uv run python scripts/dev/adu_current_rules_check.py

For Minneapolis, Raleigh and Austin, compare, year by year over 2016-2022, the observed ADU permits with the
model's expected permits under each place's coded current rules. Uses the same place-years as the anchor fit
(`lotline.model.calibrate_adu.place_years`): coded rules in force by 1 July (config/reforms/*.csv, read at run
time), each year's actual rent, home value and mortgage rate, and blank rule fields integrated as a mixture
(D-022), rule types with graded shares and coverage (D-019 fit 3, D-021): expected = θ × Σ_c w_c k_c for a
typical place (place effect u = 1). The range is over the anchor θ only (triangular on its low, central and
high values in hazard.yaml); everything else is at its central value.

Years 2016-2022 sit before every holdout window. Nothing is fitted here.
"""

from __future__ import annotations

import numpy as np

from lotline.config import load_params
from lotline.io import DataStore
from lotline.model import calibrate_adu as cal
from lotline.model.scenarios import adu

YEARS = range(2016, 2023)
CASES = {"Minneapolis": ("MN", "2743000"), "Raleigh": ("NC", "3755000"), "Austin": ("TX", "4805000")}


def main() -> None:
    store = DataStore()
    spec = load_params("hazard")["adu_mature_hazard_ref"]
    thetas = np.random.default_rng(20261020).triangular(spec.low, spec.value, spec.high, 2000)
    central = adu.central_params()
    cv = adu.c_values(central)
    print(
        f"anchor θ {spec.value:g} ({spec.low:g}-{spec.high:g}); c by type (none, owner, other, both, "
        f"Handbook) = {np.round(cv, 2).tolist()}; typical place (u = 1)"
    )
    for name, (state, geoid) in CASES.items():
        data = cal.place_data(state, store, [geoid], YEARS)
        if not data:
            print(f"\n{name}: no checkable place-years (no coded rule in force, or permits don't flag ADUs)")
            continue
        pl = data[0]
        k = (pl.w[:, None] * pl.k(cv)).sum(axis=0)
        print(f"\n{name}: blank-field combinations {len(pl.w)}")
        print("year | observed | model P10  P50  P90 | ratio")
        tot = np.zeros_like(thetas)
        for t, yr in enumerate(pl.years):
            m = thetas * k[t]
            tot += m
            p10, p50, p90 = np.percentile(m, [10, 50, 90])
            print(
                f"{int(yr)} | {int(pl.y[t]):>8d} | {p10:>9.0f} {p50:>4.0f} {p90:>4.0f} | "
                f"{p50 / max(pl.y[t], 1):>5.1f}"
            )
        obs = int(pl.y.sum())
        p10, p50, p90 = np.percentile(tot, [10, 50, 90])
        print(
            f"{YEARS[0]}-{YEARS[-1]} total: observed {obs:,}, model P50 {p50:,.0f} (P10 {p10:,.0f}, "
            f"P90 {p90:,.0f}) -> {p50 / max(obs, 1):.1f}x"
        )


if __name__ == "__main__":
    main()
