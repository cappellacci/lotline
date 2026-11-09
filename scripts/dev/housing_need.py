#!/usr/bin/env python3
# ruff: noqa: E501  (transcribed source tables and their citations read better unwrapped)
"""Build config/params/housing_need.yaml: the denominators for "% of need" (WS-ENGINE brief; analysis plan D-057).

    uv run python scripts/dev/housing_need.py          # rewrites config/params/housing_need.yaml

Two kinds of entry, never mixed on the page (`model/aggregate.py` carries the kind on every share):

- `household_growth_5y_<st>` (onboarded states MN, NC, TX, OH, OR): households the state's own projection
  implies over the forecast window. No state demographer publishes households, so it is **derived** (D-057,
  Ben 2026-11-06): the demographer's population change over the window times households per person in ACS
  2020-2024 (B11001_001 / B01003_001), i.e. constant headship. The window follows D-061: July 1 of the year
  before the window's first year to July 1 of its last year, so mid-2026 -> mid-2031 for 2027-2031
  (`window_years`). A year the demographer does not publish is read on the straight line between the
  nearest published years (`population_at`; Ben 2026-11-08). Texas's low/high come from its low and high migration
  scenarios; the other states publish one series, so low = high = value. A state whose projection falls
  (Ohio) gets a negative entry and `aggregate.headline_kind` falls back to the shortage.
- `shortage_stock_<st>` (every state and DC): Up for Growth, Housing Underproduction in the U.S. 2024 (2022
  data) is the value. The second estimate is Freddie Mac's Feb 2020 state deficit (2018 data, static estimate,
  Exhibit 3), published only as a share of stock, times ACS 2014-2018 housing units (B25001_001). low/high are
  the two estimates' min and max. Where Freddie shows a surplus (share <= 0), UfG stands alone (low = high).
  Zillow's deficit is national and metro only, so it is not used (D-057).

The published tables are small and are transcribed here with their URLs (`UFG_2022`, `FREDDIE_2018_PCT`,
`POPULATION`; the projection files themselves are downloaded through `lotline.io.http.fetch` under raw/
state_pop_projections/ when the points are checked); ACS comes through the census_acs5 fetch (manifest-logged, cached under LOTLINE_DATA_DIR).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from lotline.adapters.national import acs
from lotline.config import load_params
from lotline.io import DataStore
from lotline.model import baseline

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "config" / "params" / "housing_need.yaml"

FIPS = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC",
    "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT",
    "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY",
}  # fmt: skip

UFG_URL = (
    "https://upforgrowth.org/wp-content/uploads/2024/10/"
    "2024_FINAL_UFG-Dataset-Metropolitan-State-Underproduction-.xlsx"
)
# Up for Growth 2024 dataset, sheet "States", column 2022_UNDERPRODUCTION(3), rounded to whole homes
# (51 rows sum to 3,853,992; the report's national figure is 3.85 million)
UFG_2022 = {
    "AL": 16130, "AK": 4205, "AZ": 112091, "AR": 4327, "CA": 839774, "CO": 104837, "CT": 33841, "DE": 12011,
    "DC": 15340, "FL": 244091, "GA": 124406, "HI": 12130, "ID": 35000, "IL": 153016, "IN": 40589, "IA": 11186,
    "KS": 13879, "KY": 25404, "LA": 2988, "ME": 18743, "MD": 93986, "MA": 115651, "MI": 110881, "MN": 98383,
    "MS": 610, "MO": 29061, "MT": 13522, "NE": 15437, "NV": 35598, "NH": 26292, "NJ": 154051, "NM": 30054,
    "NY": 247512, "NC": 41743, "ND": 1153, "OH": 60782, "OK": 8186, "OR": 78468, "PA": 105393, "RI": 17056,
    "SC": 9256, "SD": 4964, "TN": 38269, "TX": 319524, "UT": 51959, "VT": 5744, "VA": 105212, "WA": 138085,
    "WV": 3182, "WI": 67750, "WY": 2242,
}  # fmt: skip

FREDDIE_URL = "https://www.freddiemac.com/fmac-resources/research/pdf/202002-Insight-12.pdf"
# Freddie Mac, "The Housing Supply Shortage: State of the States" (Feb 27, 2020), Exhibit 3: deficit as % of
# the state's housing stock, static estimate (no interstate migration), 2018 data; negative = oversupplied
FREDDIE_2018_PCT = {
    "AL": -4.45, "AK": 3.00, "AZ": 3.71, "AR": -6.23, "CA": 5.74, "CO": 5.09, "CT": 2.49, "DE": 0.23,
    "DC": 9.55, "FL": 5.13, "GA": 0.28, "HI": 1.34, "ID": 3.13, "IL": -0.16, "IN": 1.04, "IA": -2.44,
    "KS": 0.00, "KY": -0.89, "LA": 0.17, "ME": -0.13, "MD": 3.40, "MA": 4.44, "MI": 0.37, "MN": 5.37,
    "MS": -0.21, "MO": -1.86, "MT": 0.77, "NE": -2.61, "NV": 1.55, "NH": 3.47, "NJ": -0.03, "NM": 0.60,
    "NY": 2.33, "NC": 3.66, "ND": -3.82, "OH": -3.63, "OK": -1.27, "OR": 8.80, "PA": -1.96, "RI": 1.09,
    "SC": -0.22, "SD": -0.51, "TN": -2.46, "TX": 4.81, "UT": 2.48, "VT": -0.88, "VA": 1.65, "WA": 1.93,
    "WV": -7.12, "WI": 0.13, "WY": -0.98,
}  # fmt: skip

# State demographers' population projections, July 1 (persons): the published years around the window, per
# scenario. Each source's 2025 and 2030 were checked against the file on 2026-11-09 (D-061 open item 2).
POPULATION = {
    "MN": {
        "source": "Minnesota State Demographic Center, Long-Term Population Projections (May 2024; statewide tab "
        "corrected 2024-07-01), sheet 'statewide total & components', TotPop (annual)",
        "url": "https://mn.gov/admin/assets/2024-Minnesota-Long-Term-Population-Projections%20v3_tcm36-626199_tcm36-626199.xlsx",
        "vintage": "2024-05 (base 2020 Census)",
        "mid": {2025: 5_804_400, 2026: 5_830_008, 2030: 5_923_535, 2031: 5_944_374},
    },
    "NC": {
        "source": "NC Office of State Budget and Management, county/state population projections, Vintage 2025B "
        "(Population Summary, row STATE; July 1, five-year steps)",
        "url": "https://www.osbm.nc.gov/facts-figures/population-demographics/state-demographer/"
        "countystate-population-projections",
        "vintage": "Vintage 2025B (based on Vintage 2024 estimates; page updated 2026-05-26)",
        "mid": {2025: 11_171_526, 2030: 11_695_306, 2035: 12_171_710},
    },
    "TX": {
        "source": "Texas Demographic Center, Vintage 2024 population projections, state totals by migration "
        "scenario (mid = value, low and high scenarios = range); 2040 = the sum of the 254 counties in the "
        "Center's projections table (api/Tpepp/Projections/Totals/<scenario>, 2026-11-09)",
        "url": "https://www.demographics.texas.gov/Projections/2024/",
        "vintage": "Vintage 2024 (state released 2025-03)",
        "mid": {2025: 31_669_507, 2030: 33_546_497, 2040: 37_076_260},
        "low": {2025: 31_620_140, 2030: 33_241_070, 2040: 36_165_691},
        "high": {2025: 31_754_955, 2030: 34_066_155, 2040: 38_510_570},
        "check": "The projections table's 2030 equals 33,546,497 (mid) exactly; its low and high 2030 "
        "(33,231,860 and 34,057,438) differ from the state-total file's by about 9,000 (0.03%), so the low and "
        "high 2031 carry that much uncertainty",
    },
    "OH": {
        "source": "Ohio Department of Development, Office of Research, 2020-2050 population projections "
        "(Projections-by-County.xlsx, row Ohio, Total_TOT; five-year steps)",
        "url": "https://dam.assets.ohio.gov/raw/upload/development.ohio.gov/research/pop1/Projections-by-County.xlsx",
        "vintage": "2020-2050 series (2023 report; base 2020 Census)",
        "mid": {2025: 11_765_739, 2030: 11_694_767, 2035: 11_574_119},
    },
    "OR": {
        "source": "Oregon Office of Economic Analysis, state population forecast, Appendix C (July 1 population, "
        "annual)",
        "url": "https://www.oregon.gov/das/oea/Documents/appendixc.pdf",
        "vintage": "OEA forecast file of 2026-08 (2025 is an estimate, later years a forecast)",
        "mid": {2025: 4_301_164, 2026: 4_314_400, 2030: 4_399_300, 2031: 4_419_100},
    },
}

HEADSHIP_YEAR = 2024  # ACS 2020-2024, the newest 5-year release
STOCK_YEAR = 2018  # ACS 2014-2018: the year of Freddie Mac's 2018 data
ACS_TERMS = "https://www.census.gov/data/developers/data-sets/acs-5year.html"


def acs_state(year: int, variables: list[str], store: DataStore) -> dict[str, dict[str, float]]:
    """Every state's ACS 5-year estimates for `variables`, through the census_acs5 fetch (cached, logged)."""
    get = ",".join(f"{v}E" for v in variables)
    url = f"{acs.BASE_URL}/{year}/acs/acs5?get=NAME,{get}&for=state:*"
    dest = store.raw(acs.SOURCE, year) / f"us_state_{'_'.join(variables)}.json"
    payload = acs._fetch_json(url, dest, store, False, acs.api_key())
    head, rows = payload[0], payload[1:]
    out = {}
    for row in rows:
        rec = dict(zip(head, row, strict=True))
        st = FIPS.get(rec["state"])
        if st:
            out[st] = {v: float(rec[f"{v}E"]) for v in variables}
    return out


def window_years(params: dict | None = None) -> tuple[int, int]:
    """(start, end) July-1 years of the household-growth window: the year before the forecast window's first
    year and its last year (D-061). By hand: origin 2025, lead 1, horizon 5 -> window 2027-2031 -> (2026, 2031).
    """
    origin = int((params or load_params("aggregate"))["results_origin_year"].value)
    _, horizon, first = baseline.window(origin)
    return first - 1, first + horizon - 1


def population_at(points: dict[int, float], year: int) -> float:
    """July-1 population in `year`: the published value, else the straight line between the nearest published
    years on either side. By hand: {2025: 100, 2030: 110, 2035: 130} -> 2026: 102, 2031: 114."""
    if year in points:
        return float(points[year])
    lo = max((y for y in points if y < year), default=None)
    hi = min((y for y in points if y > year), default=None)
    if lo is None or hi is None:
        raise ValueError(f"{year} is outside the published years {sorted(points)}")
    return points[lo] + (points[hi] - points[lo]) * (year - lo) / (hi - lo)


def household_growth(st: str, headship: float, years: tuple[int, int] | None = None) -> dict:
    spec = POPULATION[st]
    y0, y1 = years or window_years()
    pop = {
        k: (population_at(spec[k], y0), population_at(spec[k], y1))
        for k in ("mid", "low", "high")
        if k in spec
    }
    growth = {k: (b - a) * headship for k, (a, b) in pop.items()}
    value = round(growth["mid"])
    low, high = round(growth.get("low", growth["mid"])), round(growth.get("high", growth["mid"]))
    rng = "low/high from the low and high migration scenarios" if "low" in spec else "one series: low = high"
    return {
        "value": value,
        "low": low,
        "high": high,
        "unit": f"households, mid-{y0} to mid-{y1}",
        "source": f"{spec['source']}: {spec['url']} ; times households per person, ACS 2020-2024 B11001_001 / "
        f"B01003_001 ({ACS_TERMS}); derived, analysis plan D-057",
        "notes": f"kind: household_growth_5y; vintage: {spec['vintage']}; ACS {HEADSHIP_YEAR - 4}-{HEADSHIP_YEAR}. "
        f"Population {pop['mid'][0]:,.0f} (July {y0}) -> {pop['mid'][1]:,.0f} (July {y1}) (change "
        f"{pop['mid'][1] - pop['mid'][0]:+,.0f}; {_how(spec['mid'], (y0, y1))}) "
        f"x {headship:.4f} households per person (constant headship: no state demographer publishes "
        f"households). {rng}."
        + (f" {spec['check']}." if "check" in spec else "")
        + (" Negative: the projection falls, so the headline uses the shortage." if value <= 0 else ""),
    }


def _how(points: dict[int, float], years: tuple[int, int]) -> str:
    """How each window year was read: published, or interpolated between which published years."""
    parts = []
    for y in years:
        if y in points:
            parts.append(f"{y} published")
        else:
            lo = max(p for p in points if p < y)
            hi = min(p for p in points if p > y)
            parts.append(f"{y} interpolated {lo}-{hi}")
    return ", ".join(parts)


def shortage(st: str, stock_2018: float) -> dict:
    ufg = UFG_2022[st]
    pct = FREDDIE_2018_PCT[st]
    if pct > 0:
        fm = round(pct / 100 * stock_2018)
        low, high = min(ufg, fm), max(ufg, fm)
        second = (
            f"Freddie Mac {pct:.2f}% of stock x {stock_2018:,.0f} homes (ACS 2014-2018 B25001_001) = {fm:,}; "
            "low/high = min/max of the two"
        )
    else:
        low = high = ufg
        second = f"Freddie Mac shows {pct:.2f}% (no deficit), so Up for Growth stands alone: low = high"
    return {
        "value": ufg,
        "low": low,
        "high": high,
        "unit": "homes (estimated shortage of the housing stock)",
        "source": f"Up for Growth, Housing Underproduction in the U.S. 2024, state table, 2022 underproduction: "
        f"{UFG_URL} ; Freddie Mac, The Housing Supply Shortage: State of the States (2020-02-27), Exhibit 3: "
        f"{FREDDIE_URL} ; analysis plan D-057",
        "notes": f"kind: shortage_stock; vintage: Up for Growth 2024 report (2022 data); Freddie Mac 2020 "
        f"(2018 data, static estimate). {second}. National estimates differ ~1.5x on method alone and the "
        "existence of a shortage is disputed (CRS IN12628, Dec 2025; evidence register), hence a range.",
    }


def main() -> None:
    store = DataStore()
    hh = acs_state(HEADSHIP_YEAR, ["B11001_001", "B01003_001"], store)
    stock = acs_state(STOCK_YEAR, ["B25001_001"], store)
    params: dict[str, dict] = {}
    for st in POPULATION:
        headship = hh[st]["B11001_001"] / hh[st]["B01003_001"]
        params[f"household_growth_5y_{st.lower()}"] = household_growth(st, headship)
    for st in sorted(UFG_2022):
        params[f"shortage_stock_{st.lower()}"] = shortage(st, stock[st]["B25001_001"])
    ca = FREDDIE_2018_PCT["CA"] / 100 * stock["CA"]["B25001_001"]
    print(f"check: Freddie Mac CA {ca:,.0f} (the Insight says about 820,000)")
    header = (
        "# Housing need: the denominators for '% of need' (model/aggregate.py; analysis plan D-057).\n"
        "# GENERATED by scripts/dev/housing_need.py from the sources named in each entry; edit the script, not\n"
        "# this file. Two kinds, never mixed: household_growth_5y_<st> (derived from the state demographer's\n"
        "# population projection, onboarded states) and shortage_stock_<st> (every state and DC). The kind and\n"
        "# vintage open each entry's notes.\n\n"
    )
    OUT.write_text(header + yaml.safe_dump(params, sort_keys=False, width=200, allow_unicode=True))
    for k, v in params.items():
        if k.startswith("household") or k.endswith(("_mn", "_nc", "_tx", "_oh", "_or")):
            print(f"{k:28s} {v['value']:>10,}  [{v['low']:,} - {v['high']:,}]")


if __name__ == "__main__":
    main()
