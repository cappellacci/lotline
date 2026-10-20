#!/usr/bin/env python3
"""V2-style check of the ADU hazard against places that already allow ADUs (D-019; WS-CORE sanity check).

    uv run python scripts/dev/adu_current_rules_check.py

For places that already allowed ADUs and whose permits flag them, compare, year by year over 2016-2022:
Minneapolis (ADUs since Dec 2014; owner-occupancy rule until Feb 2021), Raleigh (by right from July 2020)
and Austin (ADUs allowed for years; its ADU rules
are not coded in config/reforms/tx.csv, so it is treated as a mature Handbook-equivalent rule and flagged).

- **observed**: ADU permits from local permits that flag ADUs (Minneapolis: the larger of Met Council and city
  permits each year; Austin: city permits);
- **model**: eligible parcels × mature hazard × the largest c × ramp(years since effective) over the coded ADU
  rules in force by mid-year (as in the scenario's current-rules path), with each year's ACS rent and value
  (newest vintage <= that year, 2025 dollars) and mortgage rate. c = 1 under a Handbook-equivalent rule,
  `adu_partial_rule_share` under a restricted one (`scenarios.adu.rule_restrictions`). Range: P10-P90 over
  parameter
  draws (`scenarios.adu.draw_params`).

Durham is left out: its ADU-eligible parcel count (5 in the 2023 roll) is broken. Years 2016-2022 sit before
every holdout window (St. Paul and Charlotte are not used). Nothing is fitted:
the output is a comparison, for the analysis plan to act on.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from lotline.io import DataStore
from lotline.model import hazard, money
from lotline.model.scenarios import adu

YEARS = range(2016, 2023)
CASES = {  # name: (state, geoid, ACS geo kind); rules come from config/reforms/<st>.csv
    "Minneapolis": ("MN", "2743000", "place"),
    "Raleigh": ("NC", "3755000", "place"),
    "Austin": ("TX", "4805000", "place"),
}
MATURE_UNCODED = {"4805000"}  # ADUs allowed long before 2016 but not coded: treated as mature, flagged
DRAWS = 500


def main() -> None:
    store = DataStore()
    sets = adu.draw_params(DRAWS, 20261020)
    central = adu.central_params()
    for name, (state, geoid, kind) in CASES.items():
        reforms = adu.load_reforms(state)
        reforms = reforms[(reforms["theme"] == "adu") & (reforms["jurisdiction_geoid"] == geoid)]
        rules = [
            (adu.rule_restrictions(adu._resolved(reforms, r.reform_id))[0], r.effective_date)
            for r in reforms.itertuples()
        ]
        rules = [("partial" if fails else "handbook", eff) for fails, eff in rules]
        if geoid in MATURE_UNCODED:
            rules = [("handbook", pd.Timestamp("1990-01-01"))]
        market = store.read(state, "market_geo_year")
        cpi = money.index_by_year(market, "cpi_u")
        rate = market[market["geo"] == money.NATIONAL].set_index("year")["mortgage_rate"]
        acs = store.read(state, "acs_geo_year")
        elig = store.read(state, "eligible_parcels")
        elig = elig[(elig["theme"] == "adu") & (elig["jurisdiction_geoid"] == geoid)].set_index("year")
        parcels = float(elig["eligible_parcels"].sort_index().iloc[0])  # earliest roll: closest to 2016-22
        obs = adu.observed_adu_counts(store.read(state, "permits"), YEARS[0], YEARS[-1])
        obs = obs[obs["geoid"] == geoid].set_index("year")["adu_permits"]
        flag = " [ADU rules not coded: treated as mature]" if geoid in MATURE_UNCODED else ""
        print(f"\n{name}: {parcels:,.0f} ADU-eligible parcels (earliest roll, year {elig.index.min()}){flag}")
        print("year  rule      rent   value    rate | observed | model P10   P50   P90 | c=1 P50 | ratio")
        tot_obs = tot_mod = 0.0
        for y in YEARS:
            v = adu.acs_values(acs, pd.Series([f"{kind}:{geoid}"]), y, cpi).iloc[0]
            mid = pd.Timestamp(f"{y}-07-01")
            live = [(c, (mid - eff).days / 365.25) for c, eff in rules if eff <= mid]
            cls = live[-1][0] if live else "none"
            draws, full = [], []
            for p in sets:
                hm = float(hazard.adu_mature_hazard(v["rent"], v["home_value"], rate[y], p))
                ramp = [
                    (
                        float(adu.rule_share(pd.Series([c]), p["adu_partial_rule_share"])[0]),
                        float(hazard.ramp(a, p["adu_ramp_half_years"], p["adu_ramp_slope_years"])),
                    )
                    for c, a in live
                ]
                draws.append(parcels * hm * max((c * r for c, r in ramp), default=0.0))
                full.append(parcels * hm * max((r for _, r in ramp), default=0.0))
            p10, p50, p90 = np.percentile(draws, [10, 50, 90])
            o = float(obs.get(y, 0))
            tot_obs, tot_mod = tot_obs + o, tot_mod + p50
            print(
                f"{y}  {cls:8s} {v['rent']:>6,.0f} {v['home_value']:>8,.0f} {rate[y]:>5.2f} | {o:>8.0f} | "
                f"{p10:>9.0f} {p50:>5.0f} {p90:>5.0f} | {np.median(full):>7.0f} | {p50 / max(o, 1):>5.1f}"
            )
        hm_c = float(hazard.adu_mature_hazard(v["rent"], v["home_value"], rate[YEARS[-1]], central))
        print(f"2016-22 total: observed {tot_obs:,.0f}, model P50 {tot_mod:,.0f} ({tot_mod / tot_obs:.1f}x)")
        print(
            f"central mature hazard {YEARS[-1]}: {hm_c * 1000:.2f} per 1,000 parcels a year; "
            f"observed {YEARS[-1]}: {float(obs.get(YEARS[-1], 0)) / parcels * 1000:.2f}"
        )


if __name__ == "__main__":
    main()
