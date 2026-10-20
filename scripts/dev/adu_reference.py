#!/usr/bin/env python3
"""Recompute the ADU hazard's reference values in config/params/hazard.yaml from public data.

    uv run python scripts/dev/adu_reference.py

The mature ADU hazard comes from strong reforms in high-cost West Coast cities (adu-study-design.md: about
2-5 ADU permits per 1,000 single-family lots a year, Portland about 4). To carry it to another place, the
model needs the same effect modifiers for those reference cities, measured the same way as for the target:

- ACS 2015-2019 5-year median gross rent (B25064) and median home value (B25077) for Portland OR, Seattle WA
  and Los Angeles CA (the comparables in the calibration band), downloaded through the IO layer so each file
  is cached and logged in the manifest; converted to 2025 dollars with CPI-U (2019 dollars);
- the 30-year mortgage rate (FRED MORTGAGE30US, annual mean, from any state's `market_geo_year`) averaged over
  2015-2019, the reference rate, and its range over 2015-2023, the years the comparables' uptake covers.

It prints each city's ADU price-to-cost ratio from the pro forma (central parameters, no local fee) and the
values to copy into hazard.yaml. Portland is the reference place; the three cities span the calibration range.
"""

from __future__ import annotations

from lotline.adapters.national import acs
from lotline.io import DataStore
from lotline.model import hazard, money

VINTAGE = 2019  # ACS 2015-2019: Portland's mature years before COVID (E046, E047)
PLACES = {"Portland OR": ("41", "59000"), "Seattle WA": ("53", "63000"), "Los Angeles CA": ("06", "44000")}
VARIABLES = {"rent": "B25064_001", "value": "B25077_001"}


def fetch_place(store: DataStore, key: str, state: str, place: str) -> dict[str, float]:
    get = ",".join(f"{v}E" for v in VARIABLES.values())
    url = f"{acs.BASE_URL}/{VINTAGE}/acs/acs5?get={get}&for=place:{place}&in=state:{state}"
    dest = store.raw(acs.SOURCE, VINTAGE) / f"adu_reference_{state}_{place}.json"
    header, row = acs._fetch_json(url, dest, store, refresh=False, key=key)
    rec = dict(zip(header, row, strict=True))
    return {name: float(rec[f"{var}E"]) for name, var in VARIABLES.items()}


def main() -> None:
    store = DataStore()
    market = store.read("MN", "market_geo_year")
    cpi = money.index_by_year(market, "cpi_u")
    to_year = money.base_year()
    key = acs.api_key()
    print(f"ACS {VINTAGE - 4}-{VINTAGE}, {to_year} dollars (CPI-U)")
    rows = {}
    for name, (state, place) in PLACES.items():
        raw = fetch_place(store, key, state, place)
        real = {k: float(money.deflate(v, VINTAGE, cpi, to_year).iloc[0]) for k, v in raw.items()}
        ratio = hazard.adu_price_to_cost(real["rent"], fee_per_unit=0.0)
        rows[name] = (real["rent"], real["value"], ratio)
        print(
            f"  {name:15s} rent {raw['rent']:>7,.0f} -> {real['rent']:>7,.0f}   "
            f"value {raw['value']:>9,.0f} -> {real['value']:>9,.0f}   price-to-cost {ratio:.3f}"
        )
    nat = market[market["geo"] == money.NATIONAL].set_index("year")["mortgage_rate"].dropna()
    ref_rate = float(nat.loc[2015:2019].mean())
    print(
        f"30-year mortgage rate: mean 2015-2019 {ref_rate:.2f}%, range 2015-2023 "
        f"{nat.loc[2015:2023].min():.2f}-{nat.loc[2015:2023].max():.2f}%"
    )
    ratios = [r[2] for r in rows.values()]
    values = [r[1] for r in rows.values()]
    print(
        f"calibration range: price-to-cost {min(ratios):.3f}-{max(ratios):.3f}; "
        f"home value {min(values):,.0f}-{max(values):,.0f}"
    )


if __name__ == "__main__":
    main()
