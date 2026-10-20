"""The D-024 missing-middle panel (model/estimate_mm.py): hand-worked examples and synthetic tables only."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lotline.build import eligible as eligible_rule
from lotline.config import CONFIG_DIR
from lotline.model import estimate_mm as mm
from lotline.model import proforma
from lotline.model.estimate_adu import nearest_roll

COLUMNS = list(pd.read_csv(CONFIG_DIR / "reforms" / "mn.csv", nrows=0).columns)


def reforms(*rows: dict) -> pd.DataFrame:
    """Coded reforms with the real CSV columns (blank where a row doesn't say) and parsed dates."""
    df = pd.DataFrame([{c: r.get(c, np.nan) for c in COLUMNS} for r in rows], columns=COLUMNS)
    for col in ("announced_date", "adoption_date", "effective_date", "end_date"):
        df[col] = pd.to_datetime(df[col])
    df["jurisdiction_geoid"] = df["jurisdiction_geoid"].astype(str)
    return df


def mm_row(geoid, effective, rid=None, **kw) -> dict:
    return {
        "reform_id": rid or f"MN-{geoid}-missing_middle-{effective[:4]}",
        "state": "MN",
        "jurisdiction_geoid": geoid,
        "theme": "missing_middle",
        "status": "in_force",
        "effective_date": effective,
        **kw,
    }


# ---------------------------------------------------------------------------------------------------------
# Dose and adoption year
# ---------------------------------------------------------------------------------------------------------


def test_units_grade_by_hand():
    assert [mm.units_grade(c) for c in (1, 2, 3, 4, 8)] == pytest.approx([0, 1 / 3, 2 / 3, 1, 1])
    assert np.isnan(mm.units_grade(np.nan))


def test_blank_shares_by_hand():
    r = reforms(
        mm_row("1", "2020-01-01", by_right="True", unit_cap=3),
        mm_row("2", "2020-01-01", by_right="True", unit_cap=2),
        mm_row("3", "2020-01-01"),
        mm_row("4", "2020-01-01", by_right="False", unit_cap=8),
    )
    p_br, grade = mm.blank_shares(r)
    assert p_br == pytest.approx(2 / 3)
    assert grade == pytest.approx((2 / 3 + 1 / 3 + 1) / 3)


def test_rule_dose_by_hand():
    d, br = mm.rule_dose({"unit_cap": 3, "by_right": np.nan}, 0.5, (0.8, 0.5), 1 / 3)
    assert d == pytest.approx(2 / 3 * (0.8 + 0.2 / 3) * 0.5)
    assert br == pytest.approx(0.8)
    # by permit only: a third of the by-right dose; a blank cap takes the coded mean grade
    assert mm.rule_dose({"unit_cap": 4, "by_right": "False"}, 1.0, (0.8, 0.5), 1 / 3) == pytest.approx(
        (1 / 3, 0)
    )
    assert mm.rule_dose({"unit_cap": np.nan, "by_right": "True"}, 1.0, (0.8, 0.5), 1 / 3)[0] == pytest.approx(
        0.5
    )
    # a rule capped under 2 units is not missing middle
    assert mm.rule_dose({"unit_cap": 1, "by_right": "True"}, 1.0, (0.8, 0.5), 1 / 3) == (0.0, 0.0)


def test_rules_in_force_on_1_july_and_the_adoption_year():
    rows = reforms(
        mm_row(
            "9", "2019-09-03", rid="a", unit_cap=2, by_right="True"
        ),  # after 1 July 2019: counts from 2020
        mm_row("9", "2022-03-01", rid="b", unit_cap=4, by_right="True", end_date="2024-01-01"),
    )
    per = mm.rules_by_year(rows, [2019, 2020, 2022, 2024], {"b": 0.5}, (1.0, 1 / 3), 1 / 3)
    assert [d for d, _ in per] == pytest.approx([0, 1 / 3, 0.5, 1 / 3])  # strongest rule in force wins
    assert mm.adoption_year(rows, 2025, {}, (1.0, 1 / 3), 1 / 3) == 2020
    permit_only = reforms(mm_row("9", "2018-01-01", unit_cap=3, by_right="False"))
    assert np.isnan(mm.adoption_year(permit_only, 2025, {}, (1.0, 1 / 3), 1 / 3))
    assert mm.rules_by_year(permit_only, [2020], {}, (1.0, 1 / 3), 1 / 3)[0][0] == pytest.approx(2 / 9)


# ---------------------------------------------------------------------------------------------------------
# Modifiers and the ADU prior
# ---------------------------------------------------------------------------------------------------------


def test_pre_permit_rate_by_hand():
    y = {2016: 2, 2017: 0, 2018: 4}
    e = {2016: 1000, 2017: 1000, 2018: 2000}
    assert mm.pre_permit_rate(y, e, 2019) == pytest.approx(np.mean([2, 0, 2]))
    assert np.isnan(mm.pre_permit_rate({2018: np.nan}, e, 2019))


def test_plex_price_to_cost_by_hand():
    p = proforma.central_params()
    sqft = 2 * p["plex_unit_sqft"]
    hard = p["hard_cost_per_sqft_usd"] * sqft  # duplexes stay under the residential code
    soft = p["soft_cost_share"] * hard
    financing = (
        p["construction_loan_rate"] * p["construction_years_irc"] * p["average_draw_share"] * (hard + soft)
    )
    rent = 1500.0
    value = (
        12 * rent * 2 * (1 - p["rental_vacancy_rate"]) * (1 - p["operating_expense_share"]) / p["cap_rate"]
    )
    assert float(mm.plex_price_to_cost(rent)) == pytest.approx(value / (hard + soft + financing))
    assert float(mm.plex_price_to_cost(2 * rent)) == pytest.approx(2 * float(mm.plex_price_to_cost(rent)))
    assert float(mm.plex_price_to_cost(rent, cost_index=1.2)) < float(mm.plex_price_to_cost(rent))


def test_adu_prior_is_the_coded_mean_in_state_band_and_year():
    df = pd.DataFrame(
        {
            "state": ["MN"] * 4 + ["NC"],
            "band": [1, 1, 1, 2, 1],
            "year": [2020] * 5,
            "adu": [1.0, 0.0, np.nan, np.nan, np.nan],
            "adu_coded": [True, True, False, False, False],
        }
    )
    # same state and band -> 0.5; other band -> the state-year mean 0.5; other state -> the year mean 0.5
    assert mm.fill_adu_prior(df).tolist() == pytest.approx([1.0, 0.0, 0.5, 0.5, 0.5])
    df.loc[1, "adu"] = 1.0
    assert mm.fill_adu_prior(df).tolist() == pytest.approx([1.0, 1.0, 1.0, 1.0, 1.0])


def test_event_bins():
    assert [mm.event_bin(k) for k in (-1, 0, 1, 2, 3, 4, 9, np.nan)] == [
        None, "k0_1", "k0_1", "k2_3", "k2_3", "k4p", "k4p", None
    ]  # fmt: skip


def test_nearest_roll_by_hand():
    e = pd.DataFrame({"year": [2012, 2018], "eligible_parcels": [10, 20]})
    assert [nearest_roll(e, y) for y in (2015, 2010, 2020)] == [10, 10, 20]


# ---------------------------------------------------------------------------------------------------------
# The panel, end to end on a synthetic store (mostly zeros, as in the real data)
# ---------------------------------------------------------------------------------------------------------

YEARS = list(range(2014, 2022))
TREATED, ZEROS, SMALL, GAP = "2700001", ["2700002", "2700003", "2700004"], "2700005", "2700006"


class FakeStore:
    def __init__(self, tables: dict[str, pd.DataFrame]):
        self.tables = tables

    def read(self, state: str, table: str):
        return self.tables.get(table).copy() if table in self.tables else None


def synthetic_store() -> FakeStore:
    places = [TREATED, *ZEROS, SMALL, GAP, mm.ST_PAUL]
    pops = {TREATED: 80000, SMALL: 900, mm.ST_PAUL: 300000}
    juris = pd.DataFrame(
        {
            "state": "MN",
            "geoid": places,
            "name": [f"Place {g}" for g in places],
            "kind": "place",
            "pop_2020": [pops.get(g, 20000) for g in places],
            "county_geoid": "27053",
        }
    )
    elig = pd.DataFrame(
        [
            {
                "state": "MN",
                "jurisdiction_geoid": g,
                "year": yr,
                "theme": th,
                "rule_version": eligible_rule.RULE_VERSION,
                "eligible_parcels": 1000 if yr == 2010 else 1200,
                "data_tier": 1,
                "denominator_source": "parcels",
                "denominator_quality": "high",
            }
            for g in places
            for yr in (2010, 2016)
            for th in ("adu", "missing_middle")
        ]
    )
    bps = []
    for g in places:
        for yr in range(2008, 2022):
            if g == GAP and yr == 2018:
                continue  # a year missing from BPS stays missing, never 0
            two = 4 if g == TREATED and yr >= 2019 else (2 if g == TREATED and yr in (2015, 2017) else 0)
            bps.append(
                {"geoid": g, "year": yr, "units_1": 10, "units_2": two, "units_3_4": 0, "units_5p": 5,
                 "bldgs_2": two // 2, "bldgs_3_4": 0}
            )  # fmt: skip
    years = range(2005, 2026)
    market = pd.DataFrame(
        {
            "geo": "national:US",
            "year": list(years),
            "cpi_u": [100.0 + 2 * i for i in range(len(years))],
            "mortgage_rate": [4.0 + 0.1 * i for i in range(len(years))],
            "ppi_resid_inputs": [100.0 + 2 * i for i in range(len(years))],
        }
    )
    acs = pd.DataFrame(
        [
            {"geo": f"place:{g}", "end_year": yr, "table_id": v[:6], "variable": v, "label": "",
             "estimate": est, "moe": 0.0}
            for g in places
            for yr in range(2010, 2024)
            for v, est in (("B25064_001", 1200.0), ("B25077_001", 3e5), ("B25003_001", 20.0 * yr - 39000))
        ]
    )  # fmt: skip
    permits = pd.DataFrame(
        {
            "source": "local_src",
            "jurisdiction_geoid": [TREATED, TREATED, ZEROS[0], TREATED],
            "issue_year": [2019, 2019, 2016, 2020],
            "building_type_std": ["U2", "DTQ", "SFD", "U3_4"],
            "units_new": [2, 4, 1, 3],
            "n_buildings": [np.nan, 2, np.nan, np.nan],
        }
    )
    return FakeStore(
        {"jurisdictions": juris, "eligible_parcels": elig, "bps_place_year": pd.DataFrame(bps),
         "market_geo_year": market, "acs_geo_year": acs, "permits": permits}
    )  # fmt: skip


def synthetic_reforms() -> dict[str, pd.DataFrame]:
    adu_row = {
        "reform_id": f"MN-{TREATED}-adu-2015",
        "state": "MN",
        "jurisdiction_geoid": TREATED,
        "theme": "adu",
        "status": "in_force",
        "effective_date": "2015-01-01",
        "by_right": "True",
        "owner_occ": "False",
        "adu_detached_allowed": "True",
        "adu_max_sqft": 800,
        "parking": "none",
    }
    return {
        "MN": reforms(
            mm_row(TREATED, "2019-01-01", unit_cap=3, by_right="True"),
            mm_row(mm.ST_PAUL, "2019-01-01", unit_cap=4, by_right="True"),
            adu_row,
        )
    }


@pytest.fixture(scope="module")
def panel() -> mm.MMPanel:
    return mm.build_panel(synthetic_store(), states=("MN",), years=YEARS, reforms=synthetic_reforms())


def test_panel_rows_exclusions_and_status(panel):
    d = panel.data
    assert set(d["place"]) == {TREATED, *ZEROS, GAP}
    assert mm.ST_PAUL in panel.excluded["holdout"] and mm.ST_PAUL not in set(d["place"])
    assert SMALL in panel.excluded["small"]
    assert len(d) == 5 * len(YEARS)
    status = d.drop_duplicates("place").set_index("place")["status"]
    assert status[TREATED] == "treated" and (status.drop(TREATED) == "uncoded").all()


def test_panel_outcome_exposure_and_dose(panel):
    d = panel.data.set_index(["place", "year"])
    assert d.loc[(TREATED, 2019), "y"] == 4 and d.loc[(TREATED, 2017), "y"] == 2
    assert np.isnan(d.loc[(GAP, 2018), "y"])  # missing BPS year
    assert d.loc[(TREATED, 2015), "eligible"] == 1000 and d.loc[(TREATED, 2016), "eligible"] == 1200
    assert d.loc[(TREATED, 2018), "dose"] == 0 and d.loc[(TREATED, 2019), "dose"] == pytest.approx(2 / 3)
    assert d.loc[(TREATED, 2019), "T"] == 2019 and np.isnan(d.loc[(ZEROS[0], 2019), "T"])
    assert d.loc[(TREATED, 2016), "adu"] == 1.0 and d.loc[(TREATED, 2016), "adu_coded"]
    assert d.loc[(ZEROS[0], 2016), "adu"] == 1.0  # prior from the one coded place in the state and year


def test_panel_modifiers_are_measured_before_adoption(panel):
    tr = panel.data[panel.data["place"] == TREATED].iloc[0]
    # pre-reform 2-4 unit rate, 2016-2018: (2 / 1200, 0, 0) per 1,000 parcels
    assert tr["pre_permits"] == pytest.approx(np.mean([2 / 1.2, 0, 0]))
    assert tr["log_value"] == pytest.approx(
        np.log(300000 * (100 + 2 * 20) / (100 + 2 * 13))
    )  # 2018 -> 2025 $
    assert tr["hh_growth"] == pytest.approx(np.log((20 * 2018 - 39000) / (20 * 2013 - 39000)))
    assert tr["pcr"] > 0
    never = panel.data[panel.data["status"] != "treated"]
    assert never[list(mm.MODIFIERS)].isna().all(axis=None)


def test_local_source_fills_zero_years_and_counts_buildings():
    p = mm.build_panel(
        synthetic_store(), states=("MN",), years=YEARS, source="local_src", reforms=synthetic_reforms()
    )
    d = p.data.set_index(["place", "year"])
    assert set(p.data["place"]) == {TREATED, ZEROS[0]}  # the places the source covers (St. Paul never)
    assert d.loc[(TREATED, 2019), "y"] == 6 and d.loc[(TREATED, 2019), "y_buildings"] == 3
    assert d.loc[(TREATED, 2020), "y"] == 3 and d.loc[(TREATED, 2018), "y"] == 0
    assert (d.loc[ZEROS[0], "y"] == 0).all()  # an SFD permit is not missing middle


def test_smoke_counts_on_a_mostly_zero_panel(panel):
    c = mm.smoke_counts(panel.data)
    assert c["places"] == 5 and c["treated"] == 1 and c["comparison_places"] == 4
    assert c["adopters_by_year"] == {2019: 1}
    assert c["all_zero_places"] == 4 and c["all_zero_comparisons"] == 4 and c["all_zero_treated"] == 0
    assert c["kept_by_place_fe"] == 1  # a place fixed-effects Poisson model would keep only the treated place
    assert c["place_years"] == 5 * len(YEARS) - 1
    assert c["zero_share_place_years"] == pytest.approx(1 - 5 / (5 * len(YEARS) - 1))
    assert c["treated_place_years_by_bin"] == {"k0_1": 2, "k2_3": 1}
    strict = mm.smoke_counts(panel.data, comparisons="coded")
    assert strict["places"] == 1 and strict["comparison_places"] == 0


def test_smoke_counts_with_90_percent_zero_places():
    rng = np.random.default_rng(0)
    rows = []
    for i in range(100):
        treated = i < 5
        for yr in range(2010, 2020):
            y = rng.poisson(3) if (treated or i >= 90) else 0
            rows.append({"place": str(i), "state": "MN", "status": "treated" if treated else "uncoded",
                         "year": yr, "y": float(y), "T": 2015.0 if treated else np.nan})  # fmt: skip
    c = mm.smoke_counts(pd.DataFrame(rows))
    assert c["all_zero_places"] == 85 and c["kept_by_place_fe"] == 15
    assert c["treated_places_by_bin"] == {"k0_1": 5, "k2_3": 5, "k4p": 5}
