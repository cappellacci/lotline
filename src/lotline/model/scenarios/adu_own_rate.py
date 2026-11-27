"""Observed ADUs and own-rate persistence with drift (D-091, D-093): the additionality floor, the own counts
and their draws. Part of `scenarios.adu`; the method is in that module's docstring.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


def _is_adu(permits: pd.DataFrame) -> pd.Series:
    return (permits["building_type_std"] == "ADU") | permits["adu_type"].notna()


def adu_share_of_one_unit(permits: pd.DataFrame, first: int, last: int) -> tuple[int, int]:
    """(ADU permits, ADU + detached single-family permits) issued in [first, last]."""
    w = permits[(permits["issue_year"] >= first) & (permits["issue_year"] <= last)]
    adu = int(_is_adu(w).sum())
    return adu, adu + int((w["building_type_std"] == "SFD").sum())


def observed_adu_counts(permits: pd.DataFrame | None, first: int, last: int, undercount=None) -> pd.DataFrame:
    """ADU permits per jurisdiction and year in [first, last], from sources that flag ADUs at all.

    Where two sources cover one jurisdiction (Met Council and Minneapolis's own permits), the larger count
    each year is kept, never the sum. Jurisdictions in a flagging source with no ADU get 0, not missing.

    With `undercount` (`model.undercount.Factors`, D-078), each source's count is first multiplied by its k
    and the larger scaled count is kept; the output then also has the kept `source`, its raw count
    (`counted`) and its table row (`k_row`, -1 for k = 1).
    """
    from lotline.model import undercount as uc

    if (
        permits is None or permits.empty
    ):  # no permit adapter for the state (WS-SCALE task 0): no observed ADUs
        cols = ["geoid", "year", "adu_permits"]
        cols += [] if undercount is None else ["source", "counted", "k_row"]
        return pd.DataFrame({c: pd.Series(dtype=object) for c in cols})
    flagging = permits.loc[_is_adu(permits), "source"].unique()
    p = permits[permits["source"].isin(flagging) & permits["jurisdiction_geoid"].notna()]
    p = p[(p["issue_year"] >= first) & (p["issue_year"] <= last)].assign(adu=_is_adu)
    by = p.groupby(["jurisdiction_geoid", "source", "issue_year"])["adu"].sum().reset_index()
    if undercount is None:
        out = by.groupby(["jurisdiction_geoid", "issue_year"])["adu"].max().reset_index()
    else:
        by = uc.scale(by.assign(adu=by["adu"].astype(float)), undercount)
        by = by.sort_values(["adu", "source"], ascending=[False, True], kind="stable")
        out = by.groupby(["jurisdiction_geoid", "issue_year"]).head(1)
        out = out[["jurisdiction_geoid", "issue_year", "adu", "source", "counted", "k_row"]]
        out = out.sort_values(["jurisdiction_geoid", "issue_year"]).reset_index(drop=True)
    return out.rename(columns={"jurisdiction_geoid": "geoid", "issue_year": "year", "adu": "adu_permits"})


def own_rate_paths(h_own, h_cur_mech, h_hb_mech):
    """D-091 (adopted 2026-11-15): the no-reform and Handbook hazards where a place's own counts set the
    no-reform rate. `h_own` is that rate (persistence × drift; NaN: no own counts, keep the mechanism).

    - no reform: h_own;
    - Handbook: h_own × (h_hb_mech ÷ h_cur_mech), the mechanism's ratio, where h_cur_mech > 0; where it is 0
      (no rule allows ADUs and nothing was observed) the ratio is undefined and the mechanism's added hazard
      h_hb_mech − h_cur_mech is added instead.

    Both capped at 1. By hand: h_own 0.01, mechanism 0.02 → 0.05 gives 0.01 → 0.025; h_own 0.001, mechanism
    0 → 0.03 gives 0.001 → 0.031; h_own NaN gives the mechanism's 0.02 → 0.05.
    """
    own = np.asarray(h_own, dtype=float)
    cur_m, hb_m = np.asarray(h_cur_mech, dtype=float), np.asarray(h_hb_mech, dtype=float)
    use = np.isfinite(own)
    o = np.where(use, own, 0.0)
    pos = cur_m > 0
    ratio_hb = o * np.divide(hb_m, cur_m, out=np.ones_like(cur_m), where=pos)
    hb_own = np.where(pos, ratio_hb, o + (hb_m - cur_m))
    cur = np.where(use, np.minimum(o, 1.0), cur_m)
    hb = np.where(use, np.minimum(hb_own, 1.0), hb_m)
    return cur, hb


def own_rate_draws(observed_rate, eligible, n_years, sigma, n, seed, mean_one: bool = False) -> np.ndarray:
    """D-091 (adopted 2026-11-15): each place's no-reform ADU rate per eligible parcel a year from its own
    counts, persistence × drift (draws × places; NaN where the place has no observed rate).

    - Persistence (D-090 F0): rate ~ Gamma(Y + 0.5, E), Y = observed_rate × eligible × n_years (the counts
      the observed rate came from, undercount-scaled as drawn), E = eligible × n_years lot-years.
    - Drift: × d = exp(σ z), z standard normal, one per place and draw for the whole window (median 1).
      With `mean_one` (`adu_drift_mean_one`, Ben 2026-11-20): × d = exp(σ z − σ² / 2), mean 1, so a place's
      expected rate stays at its persistence mean; its median falls to exp(−σ² / 2) (0.59 at σ 1.025).

    `observed_rate` is one row (places) or one row per draw (`observed_rate_draws`). Own stream: `seed`.
    By hand: rate 0.01, 100 lots, 3 years -> Y 3, E 300, posterior mean 3.5 / 300 = 0.01167 before drift;
    σ 1.025 with `mean_one`: every drift factor is the median-one factor × exp(−0.5253) = × 0.5914.
    """
    obs = np.atleast_2d(np.asarray(observed_rate, dtype=float))
    obs = np.broadcast_to(obs, (n, obs.shape[1]))
    e = np.asarray(eligible, dtype=float)
    lot_years = np.where(e > 0, e * n_years, np.nan)
    y = np.nan_to_num(obs * lot_years, nan=0.0)
    rng = np.random.default_rng(seed)
    rate = rng.standard_gamma(y + 0.5) / lot_years
    drift = np.exp(sigma * rng.standard_normal(obs.shape) - (sigma**2 / 2 if mean_one else 0.0))
    return np.where(np.isfinite(obs) & np.isfinite(lot_years), rate * drift, np.nan)


def own_rate_central(observed_rate, eligible, n_years) -> np.ndarray:
    """The persistence posterior mean (Y + 0.5) / E at drift 1 (the median, or with `adu_drift_mean_one` the
    mean, of the drift factor); NaN without an observed rate."""
    e = np.asarray(eligible, dtype=float)
    lot_years = np.where(e > 0, e * n_years, np.nan)
    obs = np.asarray(observed_rate, dtype=float)
    return (obs * lot_years + 0.5) / lot_years


def observed_terms_by_k_row(
    counts: pd.DataFrame, origin: int, n_years: int, stops: Mapping[str, int]
) -> dict[str, dict[int, float]]:
    """The observed floor per place split by undercount row: GEOID -> {k_row: raw ADU permits a year}.

    Same window as `observed_per_year`; `counts` from `observed_adu_counts(..., undercount)` (columns
    `counted`, `k_row`). Summing raw x k over the rows gives `observed_per_year`, so `run` can redraw k.
    By hand: 4 years, raw 1, 2, 3, 6 all from row 0 -> {0: 3.0}; 2 from row 0 and 2 from row -1 -> {0: 0.5,
    -1: 0.5}.
    """
    out: dict[str, dict[int, float]] = {}
    for g, grp in counts.groupby("geoid"):
        last = min(origin, stops.get(g, stops.get("*", 9999)) - 1)
        w = grp[grp["year"].between(last - n_years + 1, last)]
        if w["year"].nunique() < n_years:  # a year with no records: not observed (`observed_per_year`)
            continue
        out[g] = {int(r): float(v) / n_years for r, v in w.groupby("k_row")["counted"].sum().items()}
    return out


def observed_rate_draws(places: pd.DataFrame, n: int, seed: int, table=None) -> np.ndarray | None:
    """Observed ADU permits per parcel a year in each draw (draws x places), with each draw's k (D-078 §5:
    one shared z for field rows, its own for each parser row), or None when `places` has no per-row split.

    A place with no observed floor (NaN) stays NaN. Rows index `undercount.resolve(table)` (the config table
    by default, as `places_from_store` used); -1 is k = 1.
    """
    from lotline.model import undercount as uc

    if "observed_adu_by_k_row" not in places:
        return None
    rows = uc.resolve(table)
    k = np.hstack([uc.draw_matrix(rows, n, np.random.default_rng(seed)), np.ones((n, 1))])  # last: k = 1
    m = np.zeros((len(places), len(rows) + 1))
    for i, terms in enumerate(places["observed_adu_by_k_row"]):
        if isinstance(terms, dict):
            for r, v in terms.items():
                m[i, r] += v  # r = -1 lands in the last column
    e = places["eligible_parcels"].to_numpy(dtype=float)
    rate = (k @ m.T) / np.where(e > 0, e, np.nan)
    return np.where(places["observed_rate"].isna().to_numpy()[None, :], np.nan, rate)


def holdout_stops(holdouts) -> dict[str, int]:
    """First year a held-out place's outcomes are missing from the store: GEOID -> year of `outcome_from`
    (for the place and every GEOID its outcomes are reported under). A statewide holdout is keyed "*". A
    released holdout (`released_on`, `validation.holdout.still_blind`) no longer hides anything: skipped."""
    out: dict[str, int] = {}
    for h in holdouts:
        if h.released_on:
            continue
        for g in ["*"] if h.statewide else h.geoids:
            out[g] = min(out.get(g, 9999), h.outcome_from.year)
    return out


def observed_per_year(counts: pd.DataFrame, origin: int, n_years: int, stops: Mapping[str, int]) -> pd.Series:
    """Mean ADU permits a year per place over the `n_years` years ending at `origin` (WS-NC-GUTCHECK).

    A held-out place's years end the year before its holdout starts (`stops`), so a partly held-out year is
    never read as a low count and no held-out outcome is used; its window keeps `n_years` years.

    Coverage (2026-11-19, Ben): `observed_adu_counts` has a row for a place and year only where a source that
    flags ADUs holds at least one record of any kind for that place that year (0 when none was an ADU). A
    place observed only if every window year has a row; otherwise it is left out (NaN after mapping) and
    the mechanism estimates it. A year with no records means the source was not recording there (a source
    that ended, such as Chapel Hill's in 2021; a county source holding a few stray rows for a town mostly in
    the next county; a list of ADU permits only), not that no ADU was built.

    By hand: origin 2025, 4 years, place A 2022-25 = 1, 2, 3, 6 -> 3.0; place B held out from 2023 with
    2019-22 = 2, 2, 4, 0 -> 2.0; place C with rows 2022, 2023, 2025 only -> left out.
    """
    rows = {}
    for g, grp in counts.groupby("geoid"):
        last = min(origin, stops.get(g, stops.get("*", 9999)) - 1)
        by_year = grp.set_index("year")["adu_permits"]
        window = range(last - n_years + 1, last + 1)
        if not all(y in by_year.index for y in window):
            continue
        rows[g] = sum(float(by_year[y]) for y in window) / n_years
    return pd.Series(rows, dtype=float, name="adu_permits_per_year")
