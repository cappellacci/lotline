"""The results bundle's no-policy baseline, what was observed, and the gut check that compares them
(`results.build_bundle` fills them; split out of `results.py` in modularity plan step 3).

- `baseline_class_draws`, `baseline_table`: the `baseline` part, statewide homes permitted with no policy
  change per BPS size class and period.
- `observed_table`: the `observed` part, what was permitted in the years before the window.
- `historical_floor_rows`: the scorecard's `historical_floor` rows, with-reform permits against that record.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.model import aggregate, baseline, gutcheck
from lotline.model.results_tables import _pct


def baseline_class_draws(panel: pd.DataFrame, state: str, origin: int, params=None):
    """Statewide baseline draws per BPS size class, {size: (window years x draws)} with "all" their sum per
    draw, and the set of places forecast (`baseline_table`)."""
    p = params or load_params("baseline")
    reported = bool(p["use_reported_only"].value)
    _, horizon, _ = baseline.window(origin, p)
    panel = panel[panel["state"] == state.upper()]
    by_class, modelled = {}, set()
    for size in baseline.SIZE_CLASSES:
        table, draws = baseline.forecast_draws(
            panel, baseline.outcome_column(size, reported), origin, params=p
        )
        h = table["horizon"].to_numpy()
        by_class[size] = np.stack([draws[h == k].sum(axis=0) for k in range(1, horizon + 1)]).astype(float)
        modelled |= set(table["geoid"])
    return {"all": sum(by_class.values()), **by_class}, modelled


def baseline_table(
    panel: pd.DataFrame, state: str, origin: int, params=None, class_draws=None
) -> pd.DataFrame:
    """The `baseline` part: statewide homes permitted with no policy change, per size class and period.

    For each BPS size class, `baseline.forecast_draws` gives every place's simulated counts over the window
    (D-061: origin 2025 -> 2027-2031); a draw's statewide count for a year is the sum over places. Places in
    one state share the cycle path within a draw, and every size class samples the same cycle years
    (`baseline.cycle_years` is seeded by state and origin, not by class), so draws line up across classes and
    "all" is their sum within each draw. P10/P50/P90 are taken from those sums, never by adding percentiles.

    `coverage_share`: the origin-year units of the places forecast over the units of every place in the
    panel that year, on the same basis (reported or with imputation). Null when the origin year has none.
    """
    p = params or load_params("baseline")
    reported = bool(p["use_reported_only"].value)
    _, horizon, first = baseline.window(origin, p)
    st = state.upper()
    panel = panel[panel["state"] == st]
    by_class, modelled = class_draws or baseline_class_draws(panel, st, origin, p)
    by_class = {**by_class, "2_4": by_class["2"] + by_class["3_4"]}

    cols = [baseline.outcome_column(s, reported) for s in baseline.SIZE_CLASSES]
    at_origin = panel[panel["year"] == origin]
    units = at_origin[cols].sum(axis=1, min_count=1).fillna(0)
    total = float(units.sum())
    covered = float(units[at_origin["geoid"].isin(modelled)].sum())
    coverage = covered / total if total > 0 else None

    rows = []
    for size, a in by_class.items():  # a: (horizon, draws)
        periods = [(f"{first}-{first + horizon - 1}", a.sum(axis=0))]
        periods += [(str(first + k), a[k]) for k in range(horizon)]
        for period, x in periods:
            rows.append({"size_class": size, "period": period, **_pct(x), "mean": float(x.mean())})
    return pd.DataFrame(rows).assign(
        places=len(modelled),
        coverage_share=coverage,
        basis="reported" if reported else "with_imputation",
        state=st,
    )


def historical_floor_rows(
    state: str,
    places: pd.DataFrame,
    run_draws: Mapping,
    adu_counts: pd.DataFrame,
    panel: pd.DataFrame,
    draws: pd.DataFrame,
    origin: int,
    class_draws=None,
) -> list[dict]:
    """`historical_floor` rows (`gutcheck.historical_floor`) for the ADU and missing-middle scenarios.

    - ADUs: places whose local permits flag ADUs, less any still-blind holdout place. With reform = current-
      rules gross ADUs + added, per draw and window year, on those places; observed = their ADU permits.
    - Missing middle: every BPS place. With reform = the baseline's 2-unit and 3-4 unit homes (per draw) +
      the scenario's gross permits added (window total spread evenly); observed = BPS 2-4 unit homes on the
      baseline's basis. Baseline and scenario draws are paired by index (they are independent).
    `class_draws`: `baseline_class_draws`' result, if already computed.
    """
    from lotline.config import load_state
    from lotline.model.scenarios import adu

    st = state.upper()
    why = gutcheck.reasons().get(st, {})
    rows = []
    blind = adu.holdout_stops(load_state(st).holdouts)
    counts = adu_counts[~adu_counts["geoid"].isin(blind)]
    if "*" not in blind and len(counts):
        on = places["geoid"].isin(set(counts["geoid"])).to_numpy()
        cur = np.asarray(run_draws["current"], dtype=float)[:, on, :].sum(axis=1)
        add = np.asarray(run_draws["added"], dtype=float)[:, on, :].sum(axis=1)
        observed = counts.groupby("year")["adu_permits"].sum()
        observed = observed.reindex(range(int(observed.index.min()), origin + 1), fill_value=0)  # floor years
        scope = f"{int(on.sum())} places whose permits flag ADUs"
        rows.append(
            gutcheck.historical_floor("adu", cur + add, observed, origin, scope=scope, reason=why.get("adu"))
        )
    mm = draws[draws["scenario"] == "missing_middle"].sort_values("draw")
    if len(mm):
        reported = bool(load_params("baseline")["use_reported_only"].value)
        by_class, _ = class_draws or baseline_class_draws(panel, st, origin)
        base = (by_class["2"] + by_class["3_4"]).T  # draws x years
        added = aggregate.homes_from_draws(mm)["permits_added"]
        with_reform = base[np.arange(len(added)) % len(base)] + added[:, None] / base.shape[1]
        cols = [baseline.outcome_column(s, reported) for s in ("2", "3_4")]
        p = panel[panel["state"] == st]
        observed = p.groupby("year")[cols].sum().sum(axis=1)
        rows.append(
            gutcheck.historical_floor(
                "missing_middle",
                with_reform,
                observed,
                origin,
                scope="BPS 2-4 unit homes, every place",
                reason=why.get("missing_middle"),
            )
        )
    return rows


def observed_table(
    panel: pd.DataFrame, permits, jurisdictions, state: str, origin: int, years: int = 7, params=None
) -> pd.DataFrame:
    """The `observed` part: what was actually permitted in the `years` years ending at the origin.

    - `homes_2_4`: units in 2-unit and 3-4 unit buildings, summed over every BPS place in the
      (holdout-filtered) panel, on the baseline's basis (`use_reported_only`); `places` counts the places
      with a row that year.
    - `adu_permits`: `adu.observed_adu_counts` (sources that flag ADUs; the larger count where two cover one
      place), summed over places; `places` = every place in those sources over the years, and
      `population_share` the covered places' share of the 2020 population of the state's places (GEOIDs
      longer than 5 characters on both sides, so county remainders are left out). Without permits, or none
      flagged, there are no ADU rows.
    By hand: 2-unit 4 + 3-4 unit 6 in one place and 2 in another in 2025 -> homes_2_4 = 12 from 2 places.
    """
    from lotline.model.scenarios import adu

    p = params or load_params("baseline")
    reported = bool(p["use_reported_only"].value)
    first = origin - years + 1
    st = state.upper()
    w = panel[(panel["state"] == st) & panel["year"].between(first, origin)]
    cols = [baseline.outcome_column(s, reported) for s in ("2", "3_4")]
    rows = []
    for year in range(first, origin + 1):
        y = w[w["year"] == year]
        rows.append(
            {
                "measure": "homes_2_4",
                "year": year,
                "value": float(y[cols].sum().sum()),
                "places": int(y["geoid"].nunique()),
                "population_share": None,
                "basis": "reported" if reported else "with_imputation",
            }
        )
    if permits is not None and len(permits) and adu._is_adu(permits).any():
        counts = adu.observed_adu_counts(permits, first, origin)
        by_year = counts.groupby("year")["adu_permits"].sum()
        covered = set(counts["geoid"])
        share = None
        if jurisdictions is not None and "pop_2020" in jurisdictions:
            pop = jurisdictions.set_index("geoid")["pop_2020"].astype(float)
            places_pop = pop[pop.index.str.len() > 5].sum()
            in_places = pop.reindex(sorted(g for g in covered if len(g) > 5)).sum()
            share = min(1.0, float(in_places / places_pop)) if places_pop > 0 else None
        for year in range(first, origin + 1):
            rows.append(
                {
                    "measure": "adu_permits",
                    "year": year,
                    "value": float(by_year.get(year, 0)),
                    "places": len(covered),
                    "population_share": share,
                    "basis": "flagged_permits",
                }
            )
    return pd.DataFrame(rows).assign(state=st)
