"""What places charge today: the coded local development fees, for the app's fee reduction card.

For every place with rows in `config/fees/<st>.csv`, per building type (house, duplex unit, fourplex unit,
ADU), the fee per unit the fee scenario uses (`fee_levels.place_fees`, D-065, D-066: 2025 dollars, missing
permit and water/sewer charges filled from the median of coded places) and:

- **by component** (house only): permit, water and sewer, impact, planning, other, and what was filled;
- **per lot**: fee per unit x units in the prototype (one tap versus four, D-073);
- **share of building cost**: fee per lot over hard + soft + fees + interest for that prototype
  (`pencil_out.row`; this cost does not depend on the home's value, so no market data is needed).

Fees are inputs, not outcomes, so holdout places are shown (as in docs/research/fee-levels-vs-handbook.md).
Nothing here is new method: it lays the scenario's own fee inputs out for a reader.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.config import load_fees
from lotline.model import fee_levels, pencil_out, proforma

TYPES = {"SFD": "house", "U2": "duplex", "U3_4": "fourplex", "ADU": "adu"}
COMPONENTS = ("permit", "water_sewer", "impact", "planning", "other")


def _num(x, digits: int = 2) -> float | None:
    return None if x is None or not np.isfinite(float(x)) else round(float(x), digits)


def cost_shares(fee_per_unit: float, params: Mapping[str, float] | None = None) -> dict[str, dict]:
    """Fee per lot and fee share of building cost for the house, duplex and fourplex prototypes.

    By hand (central pro forma, $8,000 a unit): a house is one unit, so $8,000 per lot; a fourplex is four,
    so $32,000 per lot. The share is fee per lot over that prototype's cost, land and profit left out.
    """
    p = pencil_out.central_params() if params is None else params
    mkt = pencil_out.market(300_000, 1_500, p)  # cost does not depend on the market; any values do
    out = {}
    for t in pencil_out.TYPES:
        r = pencil_out.row(t, proforma.TENURES[0], "now", mkt, fee_per_unit, None, p)
        out[t] = {"units": int(r["units"]), "per_lot": r["fee_per_lot"], "share": r["fee_share_of_cost"]}
    return out


def fee_sample(
    state: str,
    fees: pd.DataFrame,
    names: Mapping[str, str] | None = None,
    index: pd.Series | None = None,
    params: Mapping[str, float] | None = None,
) -> dict | None:
    """The fee summary for one state. `fees` holds every coded state (pooled priors fill thin states)."""
    st = fees[fees["state"] == state]
    if st.empty:
        return None
    names = names or {}
    p = pencil_out.central_params() if params is None else params
    places = st[["jurisdiction_geoid", "state"]].drop_duplicates()
    places = places.rename(columns={"jurisdiction_geoid": "geoid"})
    levels = fee_levels.all_types(places, fees, tuple(TYPES), index=index)
    comps = fee_levels.component_fees(fees, "SFD", index=index)
    comps = comps[comps["state"] == state]
    out_places = []
    for geoid, g in levels.groupby("geoid"):
        g = g.set_index("building_type")
        row = {"geoid": geoid, "name": names.get(geoid, geoid), "types": {}}
        for code, key in TYPES.items():
            r = g.loc[code]
            fee = float(r["local_fee_per_unit"])
            if not np.isfinite(fee):
                continue
            entry = {
                "fee": _num(fee),
                "low": _num(r["local_fee_low"]),
                "high": _num(r["local_fee_high"]),
                "filled": str(r["fee_source"]) if str(r["fee_source"]) != "local" else None,
                "from_house": "from SFD" in str(r["fee_years"]),
            }
            if code in pencil_out.TYPES:
                cs = cost_shares(fee, p)[code]
                entry.update(units=cs["units"], per_lot=_num(cs["per_lot"]), share=_num(cs["share"], 4))
            row["types"][key] = entry
        c = comps[comps["geoid"] == geoid].set_index("fee_component")["mid"]
        parts = {k: _num(c[k]) for k in COMPONENTS if k in c.index and c[k] > 0}
        house = row["types"].get("house", {}).get("fee")
        if house is not None:
            filled = house - sum(v for v in parts.values() if v)
            if filled > 0.5:
                parts["filled"] = _num(filled)
        row["components"] = parts
        out_places.append(row)
    out_places.sort(key=lambda r: -(r["types"].get("house", {}).get("fee") or 0))
    summary = {}
    for key in TYPES.values():
        v = np.array([r["types"][key]["fee"] for r in out_places if key in r["types"]], dtype=float)
        if len(v):
            summary[key] = {
                "places": len(v),
                "min": _num(v.min()),
                "median": _num(np.median(v)),
                "max": _num(v.max()),
            }
    return {
        "dollars": "nominal" if index is None else "2025 dollars",
        "handbook_fee": _num(p["handbook_fee_per_unit_usd"]),
        "handbook_cut_share": _num(p["handbook_fee_cut_share"]),
        "summary": summary,
        "places": out_places,
        "source": "config/fees/<st>.csv (each city's official fee schedule); src/lotline/model/fee_levels.py",
    }


def all_coded_fees(states) -> pd.DataFrame:
    """Every coded state's fee rows, stacked."""
    frames = [f for f in (load_fees(s) for s in states) if f is not None]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
