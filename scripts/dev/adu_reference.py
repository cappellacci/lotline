#!/usr/bin/env python3
"""Recompute the ADU hazard's reference values in config/params/hazard.yaml from public data.

    uv run python scripts/dev/adu_reference.py
    uv run python scripts/dev/adu_reference.py --fit-set [--write]   # D-060

The mature ADU hazard comes from strong reforms in high-cost West Coast cities (adu-study-design.md: about
2-5 ADU permits per 1,000 single-family lots a year, Portland about 4). To carry it to another place, the
model needs the same effect modifiers for those reference cities, measured the same way as for the target:

- ACS 2015-2019 5-year median gross rent (B25064) and median home value (B25077) for Portland OR, Seattle WA
  and Los Angeles CA (the comparables in the calibration band), downloaded through the IO layer so each file
  is cached and logged in the manifest; converted to 2025 dollars with CPI-U (2019 dollars);
- the 30-year mortgage rate (FRED MORTGAGE30US, annual mean, from any state's `market_geo_year`) averaged over
  2015-2019, the reference rate, and its range over 2015-2023, the years the comparables' uptake covers.

It prints each city's ADU price-to-cost ratio from the pro forma (central parameters, no local fee) and the
values to copy into hazard.yaml. Portland is the reference place; the three cities spanned the calibration
range until D-060.

`--fit-set` (D-060): the calibration range from the places the ADU anchor is fitted on: today D-096/D-097's
Form A + place types fit set (`scripts/dev/adu_mx_grid.places`). Rent and home value at the eligible-parcel-
weighted 5th and 95th percentiles over fit place-years, the mortgage rate at its min and max over them
(`calibrate_adu.fit_set_range`). It prints that range, the min/max alternative and the current one; `--write`
puts it into hazard.yaml's `adu_calibration_*` entries with sources. Rerun it whenever the anchor's fit set
changes.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from lotline.adapters.national import acs
from lotline.config import CONFIG_DIR, load_params
from lotline.io import DataStore, offline
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
    idx = hazard.cost_index_by_year(market)
    ref_idx = sum(idx[y] for y in range(2015, 2020)) / 5
    print(f"real construction cost (PPI resid. inputs / CPI-U, 2025 = 1): 2015-19 mean {ref_idx:.4f}")
    ratios = [r[2] for r in rows.values()]
    values = [r[1] for r in rows.values()]
    print(
        f"calibration range: price-to-cost {min(ratios):.3f}-{max(ratios):.3f}; "
        f"home value {min(values):,.0f}-{max(values):,.0f}"
    )


FIT_SET_KEYS = {
    "adu_calibration_rent_low_usd": ("rent", "5th", "USD per month (2025)"),
    "adu_calibration_rent_high_usd": ("rent", "95th", "USD per month (2025)"),
    "adu_calibration_value_low_usd": ("home value", "5th", "USD (2025)"),
    "adu_calibration_value_high_usd": ("home value", "95th", "USD (2025)"),
    "adu_calibration_rate_low": ("rate", "lowest", "percent (30-year fixed)"),
    "adu_calibration_rate_high": ("rate", "highest", "percent (30-year fixed)"),
}


def anchor_places(store):
    """The ADU anchor's fit places today: D-096/D-097's Form A + place types set, unknown years cut
    (`adu_fit_set.d096_places`)."""
    from lotline.model import adu_fit_set as fs

    with offline.offline_build(store):
        return fs.d096_places(store)


def fit_set_entries(r: dict) -> str:
    """hazard.yaml text for the six `adu_calibration_*` entries from `calibrate_adu.fit_set_range` output."""
    lo, hi = r["years"]
    where = f"{r['places']} places, {r['place_years']} place-years, {lo}-{hi}"
    head = "scripts/dev/adu_reference.py --fit-set (D-060, on D-096/D-097's fit set)"
    out = []
    for key, (what, at, unit) in FIT_SET_KEYS.items():
        v = r[key]
        if what == "rate":
            src = f"{head}: {at} annual mean of FRED MORTGAGE30US over the anchor's fit place-years ({where})"
            val = f"{v:.2f}"
        else:
            acs_var = "gross rent" if what == "rent" else "home value"
            src = (
                f"{head}: eligible-parcel-weighted {at} percentile of ACS median {acs_var} (CPI-U, 2025 "
                f"dollars) over the ADU anchor's fit place-years ({where}). Before D-060: the West Coast "
                "reference cities' range (hazard.PRE_D060_CALIBRATION)"
            )
            val = f"{v:.0f}"
        lines = [f"{key}:", f"  value: {val}", f"  low: {val}", f"  high: {val}", f"  unit: {unit}"]
        lines.append(f'  source: "{src}"')
        if key == "adu_calibration_rent_low_usd":
            note = "Places outside the fit set's range are flagged and widened (hazard.widen); inside, none."
            lines.append(f'  notes: "{note}"')
        out.append("\n".join(lines))
    return "\n\n".join(out)


def write_fit_set(r: dict, path: Path) -> None:
    """Replace hazard.yaml's six `adu_calibration_*` blocks (one contiguous run) with `fit_set_entries`."""
    text = path.read_text()
    pat = re.compile(r"^adu_calibration_rent_low_usd:.*?(?=^# ----)", re.S | re.M)
    if not pat.search(text):
        raise SystemExit(f"{path}: adu_calibration_* block not found")
    path.write_text(pat.sub(lambda _m: fit_set_entries(r) + "\n\n", text, count=1))


def _range_line(name: str, r: dict) -> str:
    g = r.get
    return (
        f"  {name}: rent {g('adu_calibration_rent_low_usd'):,.0f}-{g('adu_calibration_rent_high_usd'):,.0f}, "
        f"value {g('adu_calibration_value_low_usd'):,.0f}-{g('adu_calibration_value_high_usd'):,.0f}, "
        f"rate {g('adu_calibration_rate_low'):.2f}-{g('adu_calibration_rate_high'):.2f}"
    )


def fit_set_main(write: bool) -> None:
    from lotline.model import calibrate_adu as cal

    r = cal.fit_set_range(anchor_places(DataStore()))
    print(
        f"D-060 fit set: {r['places']} places, {r['place_years']} place-years, "
        f"{r['years'][0]}-{r['years'][1]}"
    )
    print(_range_line("current", {k: v.value for k, v in load_params("hazard").items()}))
    print(_range_line("fit set, weighted 5th-95th", r))
    mm = r["minmax"]
    print(f"  min/max (not used): rent {mm['rent'][0]:,.0f}-{mm['rent'][1]:,.0f}, "
          f"value {mm['home_value'][0]:,.0f}-{mm['home_value'][1]:,.0f}")  # fmt: skip
    if write:
        write_fit_set(r, CONFIG_DIR / "params" / "hazard.yaml")
        print("written: config/params/hazard.yaml")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit-set", action="store_true", help="D-060: the range from the anchor's fit set")
    ap.add_argument("--write", action="store_true", help="with --fit-set: write it into hazard.yaml")
    a = ap.parse_args()
    if a.fit_set:
        fit_set_main(a.write)
    else:
        main()
