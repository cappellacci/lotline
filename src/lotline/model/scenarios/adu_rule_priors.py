"""Legal lots, step 2: rule priors for places with no coded rule (D-022, D-102) and the rule share each place
draws. Part of `scenarios.adu`; the method is in that module's docstring.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.model.scenarios.adu_rules import P_COLS, TYPES, c_values


def size_band(population, edges) -> np.ndarray:
    """Place-size band 0, 1, 2 … from 2020 population and band edges (e.g. 10,000 and 50,000)."""
    return np.searchsorted(np.asarray(edges, dtype=float), np.asarray(population, dtype=float), side="right")


REMAINDER = "county_unincorporated"  # a county remainder: unincorporated land the county itself zones
REMAINDER_BAND = -1  # the priors row county remainders read under D-102 option (b)


def _cities(coded: pd.DataFrame) -> pd.DataFrame:
    """The coded places that are not county remainders: the pool behind the size-band priors. Remainders get
    their own row (`remainder_priors`, D-102 option (b)), so they never shape what towns and cities borrow."""
    return coded[coded["kind"] != REMAINDER] if "kind" in coded else coded


def remainder_priors(coded: pd.DataFrame, min_count: int) -> pd.DataFrame:
    """D-102 option (b) (Ben, 2026-11-24): for each state with at least `min_count` coded county remainders
    (`kind` == county_unincorporated), one priors row (band `REMAINDER_BAND`) with their mean probabilities.
    An uncoded remainder in that state reads it instead of its size band (`apply_priors`), since
    unincorporated land is zoned by the county, not by cities its size. In other states remainders read the
    smallest band (`apply_priors`).
    By hand: 5 coded remainders, 1 Handbook-equivalent and 4 'none' -> p_handbook 0.2, p_none 0.8."""
    if "kind" not in coded:
        return pd.DataFrame(columns=["state", "band", "n_coded", "source", *P_COLS, "p_partial"])
    rem = coded[coded["kind"] == REMAINDER]
    rows = [
        {"state": st, "band": REMAINDER_BAND, "n_coded": len(g), "source": "state, coded county remainders",
         **g[list(P_COLS)].mean().to_dict()}
        for st, g in rem.groupby("state") if len(g) >= min_count
    ]  # fmt: skip
    out = pd.DataFrame(rows, columns=["state", "band", "n_coded", "source", *P_COLS])
    return out.assign(p_partial=out[["p_owner", "p_other", "p_both"]].sum(axis=1))


def rule_priors(coded: pd.DataFrame, edges, min_count: int) -> pd.DataFrame:
    """Type probabilities for places with no ADU row, from the coded places themselves (D-022).

    `coded`: state, population and p_* (over TYPES) for every place with a coded rule (fractional where blanks
    or coverage leave the type uncertain). For each state and size band: the mean of the coded places'
    probabilities if at least `min_count` places are coded there; else the state's pooled mean; else the mean
    over every state. Returns state, band, n_coded, source and p_* (and p_partial). With a `kind` column,
    coded county remainders are left out of the band rows and get their own `remainder_priors` rows instead
    (D-102 option (b)).
    By hand: 5 coded places in a band, 2 'other' and 3 Handbook-equivalent -> p_other 0.4, p_handbook 0.6.
    """
    c = _cities(coded).assign(band=size_band(_cities(coded)["population"], edges))
    rows = []
    for state in sorted(c["state"].unique()):
        for band in range(len(edges) + 1):
            own = c[(c["state"] == state) & (c["band"] == band)]
            whole = c[c["state"] == state]
            if len(own) >= min_count:
                use, src = own, "state and band"
            elif len(whole) >= min_count:
                use, src = whole, "state, all bands"
            else:
                use, src = c, "all states"
            rows.append(
                {
                    "state": state,
                    "band": band,
                    "n_coded": len(own),
                    "source": src,
                    **use[list(P_COLS)].mean().to_dict(),
                }
            )
    out = pd.DataFrame(rows)
    out = out.assign(p_partial=out[["p_owner", "p_other", "p_both"]].sum(axis=1))
    rem = remainder_priors(coded, min_count)
    return pd.concat([out, rem], ignore_index=True) if len(rem) else out


def no_state_rule_priors(coded: pd.DataFrame, edges, min_count: int, law_states, state: str) -> pd.DataFrame:
    """D-068: priors for the places a state ADU law leaves out, from the coded places of the states without
    such a law (`law_states` are those whose law is coded row by row, `adu_state_law_rows_complete`).

    For each size band: the mean P(type) of those states' coded places in the band if at least `min_count`
    are coded there; else their pooled mean. Rows are labelled `state` so `apply_priors` reads them for it.
    By hand: no-law places in band 0, 3 Handbook-equivalent and 2 'none', min_count 5 -> p_handbook 0.6,
    p_none 0.4; flagged states' places never count.
    """
    pool = _cities(coded)
    pool = pool[~pool["state"].isin(set(law_states))]
    pool = pool.assign(band=size_band(pool["population"], edges))
    rows = []
    for band in range(len(edges) + 1):
        own = pool[pool["band"] == band]
        use, src = (own, "band") if len(own) >= min_count else (pool, "all bands")
        rows.append(
            {
                "state": state,
                "band": band,
                "n_coded": len(own),
                "source": f"states without a coded state ADU law, {src}",
                **use[list(P_COLS)].mean().to_dict(),
            }
        )
    out = pd.DataFrame(rows)
    return out.assign(p_partial=out[["p_owner", "p_other", "p_both"]].sum(axis=1))


def apply_priors(places: pd.DataFrame, priors: pd.DataFrame, edges) -> pd.DataFrame:
    """Fill p_* for 'unknown' places from `rule_priors` by state and size band; adds `prior_source`. A county
    remainder (`kind`) reads its state's `REMAINDER_BAND` row where there is one, else the smallest band (0)
    whatever its population (D-102 option (b), Ben 2026-11-24: county land is zoned more like small towns)."""
    out = places.assign(band=size_band(places["population"].fillna(0), edges))
    if "kind" in out:
        has_rem = set(priors.loc[priors["band"] == REMAINDER_BAND, "state"])
        rem = out["kind"] == REMAINDER
        out.loc[rem, "band"] = np.where(out.loc[rem, "state"].isin(has_rem), REMAINDER_BAND, 0)
    pr = priors.set_index(["state", "band"])
    pooled = priors.loc[priors["band"] != REMAINDER_BAND, list(P_COLS)].mean()
    src = pd.Series("coded", index=out.index, dtype=object)
    for i in out.index[out["rule_class"] == "unknown"]:
        key = (out.at[i, "state"], out.at[i, "band"])
        row = pr.loc[key] if key in pr.index else None
        for col in P_COLS:
            out.at[i, col] = row[col] if row is not None else pooled[col]
        src[i] = row["source"] if row is not None else "all states"
    out["p_partial"] = out[["p_owner", "p_other", "p_both"]].sum(axis=1)
    return out.assign(prior_source=src)


def type_probs(places: pd.DataFrame) -> np.ndarray:
    """(places × TYPES) probabilities. Tables from before D-022 with only p_none/p_partial/p_handbook (or only
    `rule_class`) read 'partial' as 'other'."""
    have = all(c in places for c in P_COLS)
    if have and places[list(P_COLS)].notna().all(axis=None):
        return places[list(P_COLS)].to_numpy(dtype=float)
    cls = places["rule_class"]
    get = lambda col, fallback: places[col] if col in places else fallback  # noqa: E731
    none = get("p_none", (cls == "none").astype(float)).fillna((cls == "none").astype(float))
    part = get("p_partial", (cls == "partial").astype(float)).fillna((cls == "partial").astype(float))
    hb = get("p_handbook", (cls == "handbook").astype(float)).fillna((cls == "handbook").astype(float))
    zero = np.zeros(len(places))
    out = np.column_stack([none, zero, part, zero, hb]).astype(float)
    if have:  # rows with every p_* filled keep them; only rows with a gap fall back
        full = places[list(P_COLS)].notna().all(axis=1).to_numpy()
        out[full] = places.loc[full, list(P_COLS)].to_numpy(dtype=float)
    return out


def expected_rule_share(places: pd.DataFrame, params: Mapping[str, float]) -> np.ndarray:
    """E[c] = Σ P(type) × c(type): the central-path value of c (D-022)."""
    return type_probs(places) @ c_values(params)


def draw_rule_share(places: pd.DataFrame, params: Mapping[str, float], rng: np.random.Generator):
    """One draw of each place's rule type -> (c, drawn type index, sampled mask)."""
    p = type_probs(places)
    u = rng.random(len(p))[:, None]
    idx = (u > np.cumsum(p, axis=1)).sum(axis=1).clip(max=len(TYPES) - 1)
    return c_values(params)[idx], idx, p.max(axis=1) < 1


def rule_share(rule_class: pd.Series, partial_share: float) -> np.ndarray:
    """c for a known class (before D-022): 0 none, `partial_share` partial, 1 Handbook-equivalent."""
    return rule_class.map({"none": 0.0, "partial": partial_share, "handbook": 1.0}).to_numpy(dtype=float)
