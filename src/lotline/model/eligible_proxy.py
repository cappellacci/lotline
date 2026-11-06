"""Does the ACS fallback stand in for real eligible-parcel counts? (analysis plan D-055)

The ACS fallback (`build/eligible.from_acs`, `denominator_source = "acs_sf_fallback"`) counts one-unit
detached homes, not eligible parcels, and cannot see zoning or lot size. D-055 tests it on the states that
have both denominators, at the level the app would use it (state totals):

- r_s = E_s / A_s: real eligible parcels over ACS homes, summed over the same jurisdictions and years.
- k = exp(mean_s log r_s): the scale factor (geometric mean of the ratios).
- Leave one state out: k_(-s) from the other states; held-out ratio q_s = E_s / (k_(-s) * A_s).
- sigma = sample standard deviation (n - 1) of log r_s.
- Pass: every q_s in [0.7, 1.4] (`PASS_BAND`, written in D-055 before any run).

By hand, three states with r = (0.5, 1.0, 2.0): log r = (-ln 2, 0, ln 2), so k = 1 and sigma = ln 2.
Leaving out the first, k_(-1) = sqrt(1.0 * 2.0) = sqrt 2 and q_1 = 0.5 / sqrt 2 = 0.354;
q_2 = 1.0 / sqrt(0.5 * 2) = 1.0; q_3 = 2.0 / sqrt(0.5) = 2.83.
Two held-out ratios fall outside the band, so that set fails.

`multipliers` is the per-draw step D-055 adds for a state with no parcel denominator (`proxy_states`): each
draw multiplies the ACS homes by k * exp(sigma * z), z standard normal, once per state per draw. Every place
in a state with any parcel-based denominator gets exactly 1.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

PASS_BAND = (0.7, 1.4)  # D-055 reading rule, fixed before the comparison was run
ACS_SOURCE = "acs_sf_fallback"


@dataclass(frozen=True)
class ProxyTest:
    """Result of D-055's comparison: one row per state in `table`, plus k, sigma and the verdict."""

    table: pd.DataFrame  # state, parcels (E_s), acs_homes (A_s), ratio (r_s), k_loo (k_(-s)), held_out (q_s)
    k: float
    sigma: float
    passed: bool


def geometric_mean(x: np.ndarray) -> float:
    return float(np.exp(np.mean(np.log(x))))


def proxy_test(totals: pd.DataFrame, band: tuple[float, float] = PASS_BAND) -> ProxyTest:
    """k, leave-one-out q_s and sigma from state totals.

    `totals`: one row per state with `state`, `parcels` (E_s) and `acs_homes` (A_s), both > 0.
    """
    t = totals[["state", "parcels", "acs_homes"]].copy().reset_index(drop=True)
    if len(t) < 3:
        raise ValueError("D-055 needs at least three states (two to fit k for each held-out one)")
    if not ((t["parcels"] > 0).all() and (t["acs_homes"] > 0).all()):
        raise ValueError("every state needs E_s > 0 and A_s > 0")
    r = (t["parcels"] / t["acs_homes"]).to_numpy(dtype=float)
    logs = np.log(r)
    k_loo = np.array([np.exp(np.delete(logs, i).mean()) for i in range(len(r))])
    t["ratio"] = r
    t["k_loo"] = k_loo
    t["held_out"] = r / k_loo
    t["in_band"] = t["held_out"].between(*band)
    return ProxyTest(
        table=t,
        k=float(np.exp(logs.mean())),
        sigma=float(np.std(logs, ddof=1)),
        passed=bool(t["in_band"].all()),
    )


def proxy_states(places: pd.DataFrame) -> list[str]:
    """States whose every row is the ACS fallback: no parcel denominator at all (tier 3 in D-055's sense).

    A state with even one parcel-based jurisdiction keeps its ACS-fallback places unscaled: D-055 changes
    nothing for the onboarded states.
    """
    src = places["denominator_source"] if "denominator_source" in places else pd.Series(index=places.index)
    fallback = (src == ACS_SOURCE).groupby(places["state"]).all()
    return sorted(fallback.index[fallback])


def multipliers(
    places: pd.DataFrame,
    n_draws: int,
    rng: np.random.Generator,
    k: float | None = None,
    sigma: float | None = None,
) -> np.ndarray:
    """(n_draws, n_places) multipliers on eligible parcels: k * exp(sigma * z) for each place in a
    `proxy_states` state, one z per state per draw (the proxy's error is a state-level shift, which is what
    D-055 measured), and exactly 1.0 elsewhere. k and sigma default to config/params/eligible_proxy.yaml.
    """
    if k is None or sigma is None:
        from lotline.config import load_params

        p = load_params("eligible_proxy")
        k = p["eligible_proxy_scale"].value if k is None else k
        sigma = p["eligible_proxy_sd"].value if sigma is None else sigma
    out = np.ones((n_draws, len(places)))
    states = proxy_states(places)
    if not states:
        return out
    z = rng.standard_normal((n_draws, len(states)))
    col = {s: i for i, s in enumerate(states)}
    for j, st in enumerate(places["state"].to_numpy()):
        if st in col:
            out[:, j] = k * np.exp(sigma * z[:, col[st]])
    return out
