#!/usr/bin/env python3
"""Run analysis plan D-053: does the ACS fallback stand in for real eligible-parcel counts?

    uv run python scripts/dev/eligible_proxy_test.py         # writes reports/eligible-proxy/

For each state with both denominators (MN, NC, TX, OH, OR) and each theme (ADU is the test; missing middle a
check):

1. E_s: Σ eligible parcels counted from a roll (`denominator_source == "parcels"`, current rule version), each
   jurisdiction at its newest roll year, from the processed `eligible_parcels` table (holdouts already removed
   by the adapters; nothing here reads an outcome).
2. A_s: Σ ACS one-unit detached homes (`build/eligible.from_acs`, rebuilt from the processed ACS and
   jurisdiction tables exactly as `eligible.load` builds it) for the same jurisdictions, at the ACS end year
   the eligible-year rule pairs with that roll (`eligible._nearest_acs_year`: the nearest end year, the later
   on a tie, within `scale_max_year_gap`). A jurisdiction with no ACS year in reach is left out of both sums.
3. `model.eligible_proxy.proxy_test`: r_s, k, leave-one-out k_(-s) and q_s, σ, and D-053's verdict.

Also written (D-053 "checks reported with the run"): per-jurisdiction pairs, the share of each state's
parcel-based count in "rest of county" (`county_unincorporated`) jurisdictions.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from lotline.adapters.national import geoparts
from lotline.build import eligible
from lotline.config import load_params, load_state
from lotline.io import DataStore
from lotline.model.eligible_proxy import PASS_BAND, proxy_test

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "eligible-proxy"
STATES = ("MN", "NC", "TX", "OH", "OR")
MAIN_THEME = "adu"
# data dashboard: share of parcels with unknown land use, which makes E_s itself uncertain (D-053)
UNKNOWN_LAND_USE = {"TX": 0.365, "NC": 0.192}


def acs_rows(state: str, store: DataStore) -> pd.DataFrame:
    """`from_acs` for every jurisdiction, built as `eligible.load` builds it (no network: cached inputs)."""
    juris = store.read(state, "jurisdictions")
    acs = store.read(state, "acs_geo_year")
    cfg = load_state(state)
    places = juris.loc[juris["kind"] == "place", "geoid"].tolist()
    townships = juris.loc[juris["kind"] == "township", "geoid"].tolist()
    c_shares = geoparts.county_shares(cfg.fips, places, store)
    t_shares = geoparts.township_shares(cfg.fips, places, townships, store)
    return eligible.from_acs(acs, juris, county_shares=c_shares, township_shares=t_shares)


def pairs(state: str, store: DataStore, max_gap: float) -> pd.DataFrame:
    """One row per parcel-counted jurisdiction and theme: newest roll's count and the paired ACS homes."""
    elig = store.read(state, "eligible_parcels")
    rolls = elig[(elig["denominator_source"] == "parcels") & (elig["rule_version"] == eligible.RULE_VERSION)]
    newest = rolls.sort_values("year").groupby(["jurisdiction_geoid", "theme"]).tail(1)
    acs = acs_rows(state, store)
    series = {
        k: g.set_index("year")["eligible_parcels"] for k, g in acs.groupby(["jurisdiction_geoid", "theme"])
    }
    juris = store.read(state, "jurisdictions").set_index("geoid")
    out = []
    for r in newest.itertuples():
        s = series.get((r.jurisdiction_geoid, r.theme))
        a = (
            eligible._nearest_acs_year(int(r.year), sorted(int(y) for y in s.index), max_gap)
            if s is not None
            else None
        )
        out.append(
            {
                "state": state,
                "jurisdiction_geoid": r.jurisdiction_geoid,
                "name": juris["name"].get(r.jurisdiction_geoid),
                "kind": juris["kind"].get(r.jurisdiction_geoid),
                "theme": r.theme,
                "roll_year": int(r.year),
                "acs_end_year": a,
                "parcels": int(r.eligible_parcels),
                "acs_homes": float(s[a]) if a is not None else float("nan"),
            }
        )
    return pd.DataFrame(out)


def main() -> None:
    store = DataStore()
    max_gap = load_params("eligibility")["scale_max_year_gap"].value
    OUT.mkdir(parents=True, exist_ok=True)
    allp = pd.concat([pairs(s, store, max_gap) for s in STATES], ignore_index=True)
    allp.to_csv(OUT / "by_jurisdiction.csv", index=False)
    used = allp.dropna(subset=["acs_end_year"])
    summary: dict = {"band": list(PASS_BAND), "states": list(STATES), "main_theme": MAIN_THEME, "themes": {}}
    for theme, g in used.groupby("theme"):
        totals = g.groupby("state", sort=False)[["parcels", "acs_homes"]].sum().reindex(STATES).reset_index()
        res = proxy_test(totals)
        rest = g[g["kind"] == "county_unincorporated"].groupby("state")["parcels"].sum()
        t = res.table.assign(
            theme=theme,
            jurisdictions=g.groupby("state").size().reindex(STATES).to_numpy(),
            dropped_no_acs_year=allp[(allp["theme"] == theme) & allp["acs_end_year"].isna()]
            .groupby("state")
            .size()
            .reindex(STATES, fill_value=0)
            .to_numpy(),
            rest_of_county_share=(
                rest.reindex(STATES, fill_value=0) / totals.set_index("state")["parcels"]
            ).to_numpy(),
            unknown_land_use_share=[UNKNOWN_LAND_USE.get(s) for s in STATES],
        )
        t.to_csv(OUT / f"ratios_{theme}.csv", index=False)
        summary["themes"][theme] = {
            "k": res.k,
            "sigma": res.sigma,
            "k_low": res.k * math.exp(-res.sigma),
            "k_high": res.k * math.exp(res.sigma),
            "passed": res.passed,
            "rows": t.to_dict(orient="records"),
        }
    summary["verdict"] = "pass" if summary["themes"][MAIN_THEME]["passed"] else "fail"
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    for theme, v in summary["themes"].items():
        print(f"\n{theme}: k={v['k']:.3f}  sigma={v['sigma']:.3f}  passed={v['passed']}")
        print(pd.DataFrame(v["rows"]).round(3).to_string(index=False))
    print(f"\nD-053 verdict (theme {MAIN_THEME}): {summary['verdict'].upper()}")


if __name__ == "__main__":
    main()
