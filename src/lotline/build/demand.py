"""Local labor-demand index (causal diagram C04): a shift-share ("Bartik") job index per county and year.

The question it answers: *how fast would this county's jobs have grown if each of its industries had grown at
the national rate?* It uses only the county's industry mix **before** the study period, so it moves with
national industry booms and busts but not with anything local, such as a zoning reform (E081).

For county c, sector k and year t, with pre-period shares s and national employment N from County Business
Patterns (`adapters/national/cbp.py`):

    s_ck           = mean employment of c in k over the share years / the same for all sectors of c
    demand_bartik  = sum_k s_ck * (ln N_kt - ln N_kb)                  (b = growth base year)
    demand_bartik_loo uses N_kt - e_ckt in place of N_kt (and likewise at b): national growth with the
                   county's own jobs left out, so a big county's own boom can't feed its own index

Units are log points of employment change since the base year: 0.10 means about 10% more jobs than in the base
year, from industry mix alone. Years before the base year are negative when industries were smaller then.

Places and townships take a weighted average of their counties' values, weighted by 2020 housing units in each
county (`geoparts.county_shares`); a township lies in one county. `demand_imputed_share` is the share of the
pre-period employment behind the shares that came from suppressed CBP cells (2010-2016 data only).

Every setting comes from config/params/demand.yaml.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from lotline.config import Parameter, load_params
from lotline.io import DataStore
from lotline.schemas import validate

SOURCE = "demand"
TABLE = "market_geo_year"
MANIFEST_SOURCES = ["census_cbp", "census_geo_codes"]
COLUMNS = ["demand_bartik", "demand_bartik_loo", "demand_imputed_share"]

PROVENANCE = {
    "title": "Local demand index: shift-share employment growth from pre-period industry mix (built)",
    "landing_url": "https://www.census.gov/programs-surveys/cbp.html",
    "table": "market_geo_year",
    "cleaning": [
        "Pre-period sector shares: mean county employment by 2-digit NAICS sector over the share years "
        "(config/params/demand.yaml)",
        "demand_bartik: shares times national log employment growth by sector since the growth base year",
        "demand_bartik_loo: the same with the county's own employment removed from the national totals",
        "Places and townships: mean of their counties, weighted by 2020 housing units (geoparts)",
    ],
    "limitations": [
        "A predicted, not an observed, job change: it ignores everything local by design",
        "County level only: every place in a county gets the same index (places in two counties a blend)",
        "Leave-one-out uses suppressed cells' imputed values; national totals dwarf any county's, so the two "
        "versions differ only for the largest counties",
    ],
}


def shares(county: pd.DataFrame, first: int, last: int) -> pd.DataFrame:
    """geo, sector, share (summing to 1 per county), imputed_share: from mean employment in [first, last]."""
    pre = county[county["year"].between(first, last)]
    n_years = last - first + 1
    mean = pre.groupby(["geo", "sector"], as_index=False).agg(emp=("emp", "sum"))
    mean["emp"] /= n_years  # a missing county-sector-year is 0 employees
    imp = pre[pre["imputed"]].groupby(["geo", "sector"])["emp"].sum() / n_years
    mean["imp"] = mean.set_index(["geo", "sector"]).index.map(imp).fillna(0).to_numpy()
    mean["total"] = mean.groupby("geo")["emp"].transform("sum")
    mean["imputed_share"] = mean.groupby("geo")["imp"].transform("sum") / mean["total"]
    mean = mean[mean["total"] > 0].assign(share=lambda d: d["emp"] / d["total"])
    return mean[["geo", "sector", "share", "imputed_share"]].reset_index(drop=True)


def national_growth(nation: pd.DataFrame, base: int) -> pd.DataFrame:
    """year, sector, growth = ln N_kt - ln N_kb."""
    n = nation.pivot_table(index="year", columns="sector", values="emp", aggfunc="sum")
    if base not in n.index:
        raise ValueError(f"no national CBP data for the growth base year {base}")
    g = np.log(n) - np.log(n.loc[base])
    return g.stack().rename("growth").reset_index()


def loo_growth(county: pd.DataFrame, nation: pd.DataFrame, base: int) -> pd.DataFrame:
    """geo, year, sector, growth with the county's own employment removed from the national total."""
    n = nation.groupby(["year", "sector"])["emp"].sum().rename("N").reset_index()
    geos = county["geo"].unique()
    grid = n.merge(pd.DataFrame({"geo": geos}), how="cross")
    grid = grid.merge(county[["geo", "year", "sector", "emp"]], how="left", on=["geo", "year", "sector"])
    grid["rest"] = grid["N"] - grid["emp"].fillna(0)
    at_base = grid[grid["year"] == base].set_index(["geo", "sector"])["rest"]
    if at_base.empty:
        raise ValueError(f"no CBP data for the growth base year {base}")
    grid["growth"] = np.log(grid["rest"]) - np.log(grid.set_index(["geo", "sector"]).index.map(at_base))
    return grid[["geo", "year", "sector", "growth"]]


def county_index(county: pd.DataFrame, nation: pd.DataFrame, params: dict[str, Parameter]) -> pd.DataFrame:
    """geo (5-digit county), year, demand_bartik, demand_bartik_loo, demand_imputed_share."""
    first, last = int(params["share_first_year"].value), int(params["share_last_year"].value)
    base = int(params["growth_base_year"].value)
    s = shares(county, first, last)
    plain = s.merge(national_growth(nation, base), on="sector")
    plain = (plain["share"] * plain["growth"]).groupby([plain["geo"], plain["year"]]).sum(min_count=1)
    loo = s.merge(loo_growth(county, nation, base), on=["geo", "sector"])
    loo = (loo["share"] * loo["growth"]).groupby([loo["geo"], loo["year"]]).sum(min_count=1)
    out = pd.DataFrame({"demand_bartik": plain, "demand_bartik_loo": loo}).reset_index()
    imputed = s.drop_duplicates("geo").set_index("geo")["imputed_share"]
    return out.assign(demand_imputed_share=out["geo"].map(imputed))


def to_places(index: pd.DataFrame, county_shares: pd.DataFrame) -> pd.DataFrame:
    """Place rows (geo = 7-digit place) as the housing-unit-weighted mean of their counties' rows."""
    m = county_shares.merge(index, left_on="county_geoid", right_on="geo")
    w = m["share"]
    num = m[COLUMNS].mul(w, axis=0).groupby([m["place_geoid"], m["year"]]).sum()
    den = w.groupby([m["place_geoid"], m["year"]]).sum()
    return num.div(den, axis=0).rename_axis(["geo", "year"]).reset_index()


def assemble(index: pd.DataFrame, county_shares: pd.DataFrame, townships: list[str]) -> pd.DataFrame:
    """market_geo_year rows for counties, places and townships (a township takes its county's values)."""
    parts = [index.assign(geo="county:" + index["geo"])]
    if len(county_shares):
        parts.append(to_places(index, county_shares).assign(geo=lambda d: "place:" + d["geo"]))
    if townships:
        t = pd.DataFrame({"twp": townships, "geo": [g[:5] for g in townships]}).merge(index, on="geo")
        parts.append(t.assign(geo="cousub:" + t["twp"]).drop(columns="twp"))
    out = pd.concat(parts, ignore_index=True)[["geo", "year", *COLUMNS]]
    return out.assign(year=out["year"].astype("Int64"))


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    """Build the demand index for one state's counties, places and townships."""
    from lotline.adapters.national import cbp, geoparts
    from lotline.build import jurisdictions as jur
    from lotline.config import load_state

    cfg = load_state(state)
    params = load_params("demand")
    county, nation = cbp.load(
        cfg.fips, store, position=params["suppressed_cell_position"].value, refresh=refresh
    )
    juris = store.read(state, "jurisdictions")
    if juris is None:
        juris = jur.load(state, store, refresh=refresh)
    places = juris.loc[juris["kind"] == "place", "geoid"].tolist()
    townships = juris.loc[juris["kind"] == "township", "geoid"].tolist()
    c_shares = geoparts.county_shares(cfg.fips, places, store, refresh)
    index = county_index(county, nation, params)
    return validate(assemble(index, c_shares, townships), TABLE)
