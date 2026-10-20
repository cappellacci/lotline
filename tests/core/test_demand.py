"""Shift-share local demand index (build/demand.py) and its CBP inputs, on hand-worked synthetic data."""

from math import log

import pandas as pd
import pytest

from lotline.adapters.national import cbp
from lotline.build import demand
from lotline.config import Parameter, load_params
from lotline.schemas import validate


def _params(first=2010, last=2011, base=2011, position=0.5):
    def p(v, lo=None, hi=None):
        return Parameter(
            value=v, low=v if lo is None else lo, high=v if hi is None else hi, unit="", source="t"
        )

    return {
        "share_first_year": p(first),
        "share_last_year": p(last),
        "growth_base_year": p(base),
        "suppressed_cell_position": p(position, 0, 1),
    }


def _rows(geo, data):
    """data: {(year, sector): emp} -> CBP-shaped rows."""
    return pd.DataFrame(
        [
            {"geo": geo, "year": y, "sector": k, "emp": float(e), "imputed": False}
            for (y, k), e in data.items()
        ]
    )


# Two industries, hand-worked. County A: X = 60, 80 and Y = 40, 20 in 2010-2011, so mean 70 and 30 and
# shares 0.7 and 0.3. National X grows 1000 -> 1200 and Y shrinks 500 -> 400 from 2011 to 2013.
COUNTY = _rows(
    "27001",
    {(2010, "X"): 60, (2011, "X"): 80, (2013, "X"): 100, (2010, "Y"): 40, (2011, "Y"): 20, (2013, "Y"): 10},
)
NATION = _rows(
    "US",
    {
        (2010, "X"): 900,
        (2011, "X"): 1000,
        (2013, "X"): 1200,
        (2010, "Y"): 600,
        (2011, "Y"): 500,
        (2013, "Y"): 400,
    },
)


def test_shares_are_pre_period_means():
    s = demand.shares(COUNTY, 2010, 2011).set_index("sector")["share"]
    assert s["X"] == pytest.approx(0.7)
    assert s["Y"] == pytest.approx(0.3)


def test_two_industry_bartik_by_hand():
    out = demand.county_index(COUNTY, NATION, _params()).set_index("year")
    expected = 0.7 * log(1200 / 1000) + 0.3 * log(400 / 500)  # = 0.0607
    assert out.loc[2013, "demand_bartik"] == pytest.approx(expected)
    assert out.loc[2013, "demand_bartik"] == pytest.approx(0.06068, abs=1e-5)
    assert out.loc[2011, "demand_bartik"] == pytest.approx(0.0)  # zero in the base year
    assert out.loc[2010, "demand_bartik"] == pytest.approx(0.7 * log(900 / 1000) + 0.3 * log(600 / 500))


def test_two_industry_leave_one_out_by_hand():
    out = demand.county_index(COUNTY, NATION, _params()).set_index("year")
    # rest of nation: X 1000-80 = 920 -> 1200-100 = 1100; Y 500-20 = 480 -> 400-10 = 390
    expected = 0.7 * log(1100 / 920) + 0.3 * log(390 / 480)
    assert out.loc[2013, "demand_bartik_loo"] == pytest.approx(expected)
    assert out.loc[2011, "demand_bartik_loo"] == pytest.approx(0.0)


def test_leave_one_out_uses_only_the_other_counties():
    # A two-county nation: A booms in X, B is flat. Without leave-one-out, A's own boom raises its index;
    # with it, A's index is B's growth alone (0), and B's is A's growth weighted by B's mix.
    a = _rows("27001", {(2011, "X"): 100, (2013, "X"): 300, (2011, "Y"): 100, (2013, "Y"): 100})
    b = _rows("27003", {(2011, "X"): 100, (2013, "X"): 100, (2011, "Y"): 300, (2013, "Y"): 300})
    nation = (
        pd.concat([a, b])
        .groupby(["year", "sector"], as_index=False)["emp"]
        .sum()
        .assign(geo="US", imputed=False)
    )
    out = demand.county_index(pd.concat([a, b]), nation, _params(2011, 2011, 2011)).set_index(["geo", "year"])
    assert out.loc[("27001", 2013), "demand_bartik"] == pytest.approx(0.5 * log(400 / 200))
    assert out.loc[("27001", 2013), "demand_bartik_loo"] == pytest.approx(0.0)
    assert out.loc[("27003", 2013), "demand_bartik_loo"] == pytest.approx(0.25 * log(300 / 100))


def test_missing_county_sector_row_is_zero_employees():
    county = COUNTY[~((COUNTY["year"] == 2010) & (COUNTY["sector"] == "Y"))]  # no Y establishments in 2010
    s = demand.shares(county, 2010, 2011).set_index("sector")["share"]
    assert s["X"] == pytest.approx(70 / 80)  # X mean 70, Y mean (0 + 20) / 2 = 10


def test_imputed_share_reports_suppressed_employment():
    county = COUNTY.copy()
    county.loc[(county["year"] == 2010) & (county["sector"] == "Y"), "imputed"] = True
    s = demand.shares(county, 2010, 2011)
    assert s["imputed_share"].iloc[0] == pytest.approx(20 / 100)  # (40 / 2) of a mean total of 100


def test_places_are_housing_weighted_and_townships_take_their_county():
    index = pd.DataFrame(
        {
            "geo": ["39001", "39003"],
            "year": [2013, 2013],
            "demand_bartik": [0.10, 0.40],
            "demand_bartik_loo": [0.10, 0.40],
            "demand_imputed_share": [0.0, 0.5],
        }
    )
    shares = pd.DataFrame(
        {
            "place_geoid": ["3900100", "3900100", "3900200"],
            "county_geoid": ["39001", "39003", "39001"],
            "share": [2 / 3, 1 / 3, 1.0],
        }
    )
    out = validate(demand.assemble(index, shares, ["3900110000"]), "market_geo_year").set_index("geo")
    assert out.loc["place:3900100", "demand_bartik"] == pytest.approx(2 / 3 * 0.10 + 1 / 3 * 0.40)
    assert out.loc["place:3900200", "demand_bartik"] == pytest.approx(0.10)
    assert out.loc["cousub:3900110000", "demand_bartik"] == pytest.approx(0.10)
    assert out.loc["county:39003", "demand_imputed_share"] == pytest.approx(0.5)


def test_missing_base_year_is_an_error():
    with pytest.raises(ValueError, match="base year"):
        demand.county_index(COUNTY, NATION, _params(base=2012))


# CBP parsing


def test_parse_fills_suppressed_cells_inside_the_flag_range():
    payload = [
        ["EMP", "EMP_F", "NAICS2007", "NAICS2007", "state", "county"],
        ["0", "b", "21    ", "21    ", "27", "001"],  # withheld: 20-99 employees
        ["58149", None, "55    ", "55    ", "27", "053"],
        ["0", "a", "21    ", "21    ", "27", "999"],  # statewide: dropped
    ]
    for position, fill in [(0.5, 59.5), (0.0, 20.0), (1.0, 99.0)]:
        out = cbp.parse(payload, 2010, position)
        assert out["geo"].tolist() == ["27001", "27053"]
        assert out["sector"].tolist() == ["21", "55"]
        assert out["emp"].tolist() == [fill, 58149.0]
        assert out["imputed"].tolist() == [True, False]


def test_parse_national_and_noise_years():
    payload = [["EMP", "NAICS2017", "us"], ["6311264", "23", "1"]]
    out = cbp.parse(payload, 2020, 0.5)
    assert out.to_dict("records") == [
        {"geo": "US", "year": 2020, "sector": "23", "emp": 6311264.0, "imputed": False}
    ]


def test_urls_follow_the_vintage():
    old, new = cbp.url(2010, "for=us:*"), cbp.url(2020, "for=us:*")
    assert "EMP_F" in old and "NAICS2007=31-33" in old
    assert "EMP_F" not in new and "NAICS2017=44-45" in new
    assert cbp.naics_var(2012) == cbp.naics_var(2016) == "NAICS2012"
    assert "LFO=001&EMPSZES=001" in new


def test_params_file_loads():
    p = load_params("demand")
    assert p["share_first_year"].value <= p["share_last_year"].value <= p["growth_base_year"].value
    assert 0 <= p["suppressed_cell_position"].value <= 1
