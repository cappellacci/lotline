#!/usr/bin/env python3
"""Run analysis plan D-056: does the ACS fallback stand in for real eligible-parcel counts?

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
3. `model.eligible_proxy.proxy_test`: r_s, k, leave-one-out k_(-s) and q_s, σ, and D-056's verdict.

Also written (D-056 "checks reported with the run"): per-jurisdiction pairs, the share of each state's
parcel-based count in "rest of county" (`county_unincorporated`) jurisdictions.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from lotline.calibrate.data_steps import proxy_pairs as pairs
from lotline.config import load_params
from lotline.io import DataStore
from lotline.model.eligible_proxy import PASS_BAND, proxy_test

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "eligible-proxy"
STATES = ("MN", "NC", "TX", "OH", "OR")
MAIN_THEME = "adu"
# data dashboard: share of parcels with unknown land use, which makes E_s itself uncertain (D-056)
UNKNOWN_LAND_USE = {"TX": 0.365, "NC": 0.192}


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
    print(f"\nD-056 verdict (theme {MAIN_THEME}): {summary['verdict'].upper()}")


if __name__ == "__main__":
    main()
