"""Data dashboard: the summary rules in `lotline.dashboard.summarize` on small hand-worked fixtures.

Each test states the rule from the module docstring (docs/data_dashboard.md) and checks it on numbers small
enough to work by hand. The end-to-end test builds a made-up state "ZZ" from config and processed tables only,
which is the promise that a new (fifth) state needs no dashboard code.
"""

import json

import pandas as pd
import pytest

from lotline.adapters.national import pep
from lotline.dashboard import render
from lotline.dashboard import summarize as sm
from lotline.io import DataStore


def _parcels(rows):
    return pd.DataFrame(
        rows, columns=["jurisdiction_geoid", "county_geoid", "vintage", "land_use_std", "zoning_raw"]
    )


# ------------------------------------------------------------------------------------- latest roll rule
def test_latest_vintage_is_per_jurisdiction_not_per_file():
    # J1 only appears in the 2023 roll (like St. Paul); J2 is in 2023 and 2026 -> its 2026 rows count.
    df = _parcels(
        [
            ("9900001", "99001", 2023, "SF_DETACHED", None),
            ("9900001", "99001", 2023, "SF_DETACHED", "R1"),
            ("9900002", "99001", 2023, "SF_DETACHED", None),
            ("9900002", "99001", 2026, "DUPLEX", ""),
            ("9900002", "99001", 2026, "SF_DETACHED", "R2"),
            (None, "99003", 2026, None, None),
        ]
    )
    out = sm.parcel_counts_from_frame(df, "src_a")
    j1 = out[out["jkey"] == "9900001"]
    j2 = out[out["jkey"] == "9900002"]
    assert set(j1["vintage"]) == {2023} and j1["n"].sum() == 2
    assert set(j2["vintage"]) == {2026} and j2["n"].sum() == 2
    # zoned = a non-blank zoning code: one in J1 ("R1"), one in J2 ("R2"; "" is not zoned)
    assert j1.loc[j1["zoned"], "n"].sum() == 1 and j2.loc[j2["zoned"], "n"].sum() == 1
    # no jurisdiction -> counted under its county, land use unknown, never dropped
    un = out[out["jkey"] == "unassigned:99003"]
    assert un["n"].sum() == 1 and un["land_use_std"].iloc[0] == "UNKNOWN"


def test_source_without_zoning_column_counts_nothing_as_zoned():
    df = _parcels([("9900001", "99001", 2024, "SF_DETACHED", None)]).drop(columns="zoning_raw")
    assert not sm.parcel_counts_from_frame(df, "s")["zoned"].any()


# ----------------------------------------------------------------------------------- one source per place
def _counts(rows):
    return pd.DataFrame(
        rows, columns=["source", "jkey", "county_geoid", "vintage", "land_use_std", "zoned", "n"]
    )


def test_configured_source_wins_else_largest():
    counts = _counts(
        [
            ("assessor", "9900001", "99001", 2026, "SF_DETACHED", True, 90),
            ("regional", "9900001", "99001", 2026, "SF_DETACHED", False, 100),
            ("regional", "9900002", "99001", 2026, "SF_DETACHED", False, 40),
            ("statewide", "9900002", "99001", 2025, "SF_DETACHED", False, 50),
            ("statewide", "9900003", "99003", 2025, "SF_DETACHED", False, 7),
        ]
    )
    prefs = {"9900001": "assessor", "*": "regional"}
    ch = sm.choose_sources(counts, prefs).set_index("jkey")
    assert ch.at["9900001", "source"] == "assessor"  # named for it, though smaller
    assert ch.at["9900002", "source"] == "regional"  # "*" default, though statewide is larger
    assert ch.at["9900003", "source"] == "statewide"  # default has no parcels there -> largest
    used = sm.chosen_counts(counts, ch.reset_index())
    assert used["n"].sum() == 90 + 40 + 7  # never added across sources


# -------------------------------------------------------------------------------------------- population
def test_unincorporated_population_is_county_remainder_floored_at_zero():
    jur = pd.DataFrame(
        {
            "geoid": ["9900001", "9900002", "99001", "9900003", "99003"],
            "county_geoid": ["99001", "99001", "99001", "99003", "99003"],
            "kind": ["place", "place", "county_unincorporated", "place", "county_unincorporated"],
            "pop_2020": [600, 300, None, 500, None],
        }
    )
    county_pop = pd.Series({"99001": 1000.0, "99003": 400.0})
    out = sm.jurisdiction_population(jur, county_pop).set_index("geoid")
    assert out.at["99001", "pop"] == 100  # 1000 - 600 - 300
    assert out.at["99003", "pop"] == 0  # 400 - 500, floored
    assert out.at["99001", "pop_estimated"] and not out.at["9900001", "pop_estimated"]


# ---------------------------------------------------------------------------------------------- eligible
def test_latest_eligible_prefers_a_roll_count_over_a_later_scaled_year():
    e = pd.DataFrame(
        {
            "jurisdiction_geoid": ["9900001"] * 3,
            "theme": ["adu"] * 3,
            "year": [2023, 2024, 2025],
            "eligible_parcels": [100, 110, 120],
            "denominator_source": ["parcels", "parcels", "parcels_scaled_acs"],
            "denominator_quality": ["high"] * 3,
        }
    )
    row = sm.latest_eligible(e).iloc[0]
    assert (row["year"], row["eligible_parcels"]) == (2024, 110)


# ----------------------------------------------------------------------------------------------- reforms
def test_reform_events_use_effective_date_then_adoption():
    r = pd.DataFrame(
        {
            "reform_id": ["a", "b", "c"],
            "jurisdiction_geoid": ["9900001", "9900002", "99"],
            "theme": ["adu", "missing_middle", "fees"],
            "status": ["in_force"] * 3,
            "adoption_date": ["2019-01-01", "2020-05-01", ""],
            "effective_date": ["2019-03-01", "", ""],
            "coder_agreement": ["agree", "", "single_coder"],
            "component": ["x" * 500, "short", ""],
            "source_url": ["https://a;https://b", "", ""],
        }
    )
    ev = {e["id"]: e for e in sm.reform_events(r, {"9900001": "Alpha", "99": "Zedland"})}
    assert ev["a"]["date"] == "2019-03-01" and ev["a"]["date_basis"] == "effective"
    assert ev["b"]["date"] == "2020-05-01" and ev["b"]["date_basis"] == "adoption"
    assert ev["c"]["date"] is None and ev["c"]["place"] == "Zedland"
    assert ev["b"]["coder_agreement"] == "single_coder"  # blank means one coder
    assert len(ev["a"]["component"]) == sm.COMPONENT_CHARS and ev["a"]["source_url"] == "https://a"


# ------------------------------------------------------------------------------------------------ growth
def test_growth_series_and_county_growth_hand_worked():
    popdf = pd.DataFrame(
        {
            "geo": ["state:99", "state:99", "county:99001", "county:99001"],
            "year": [2010, 2012, 2010, 2012],
            "population": [1000, 1100, 400, 420],
        }
    )
    hu = pd.DataFrame(
        {
            "geo": ["state:99", "county:99001", "county:99001"],
            "year": [2010, 2010, 2012],
            "units": [500, 200, 210],
        }
    )
    permits = pd.DataFrame(
        {
            "county_geoid": ["99001", "99001", "99001"],
            "year": [2010, 2011, 2012],
            "units_1": [5, 6, 7],
            "units_2": [0, 2, 0],
            "units_3_4": [0, 0, 0],
            "units_5p": [0, 0, 10],
            "imputed_units": [0, 0, 0],
        }
    )
    s = {r["year"]: r for r in sm.growth_series("99", popdf, hu, permits)}
    assert (
        s[2010]["population"] == 1000 and s[2010]["housing_units"] == 500 and s[2012]["housing_units"] is None
    )
    assert s[2011]["units_1"] == 6 and s[2011]["population"] is None
    cg = sm.county_growth(popdf, hu, permits, 2010, 2012).loc["99001"]
    assert (cg["pop_start"], cg["pop_end"], cg["hu_start"], cg["hu_end"]) == (400, 420, 200, 210)
    assert cg["permits"] == 6 + 2 + 7 + 10  # 2011 and 2012 only: permits after the start year


def test_bps_units_flags_imputed_units():
    b = pd.DataFrame(
        {
            "county_geoid": ["99001", "99001"],
            "year": [2020, 2020],
            "units_1": [3, 4],
            "units_2": [0, 2],
            "units_3_4": [0, 0],
            "units_5p": [0, 0],
            "imputed": [False, True],
        }
    )
    out = sm.bps_units(b).iloc[0]
    assert out["units_1"] == 7 and out["imputed_units"] == 6


# --------------------------------------------------------------------------------------------------- PEP
PEP_2020 = (
    "SUMLEV,REGION,DIVISION,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2010,POPESTIMATE2019,POPESTIMATE2020\n"
    "040,1,1,99,000,Zedland,Zedland,1000,1090,1095\n"
    "050,1,1,99,001,Zedland,Alpha County,400,410,411\n"
    "010,0,0,00,000,United States,United States,1,1,1\n"
)


def test_pep_parse_keeps_states_and_counties_and_years_of_its_vintage():
    out = pep.parse(PEP_2020, 2020)
    assert set(out["geo"]) == {"state:99", "county:99001"}
    # vintage 2020 supplies 2010-2019 only: 2020 comes from vintage 2025 (splice rule)
    assert sorted(out.loc[out["geo"] == "state:99", "year"]) == [2010, 2019]
    assert out.loc[(out["geo"] == "county:99001") & (out["year"] == 2010), "name"].iloc[0] == "Alpha County"


# ------------------------------------------------------------------------------------------------ render
def test_render_embeds_json_that_cannot_close_its_script_tag():
    page = render.render({"x": "</script><b>"}, template="<script>/*__LOTLINE_DATA__*/</script>")
    assert "</script><b>" not in page
    body = page[len("<script>") : -len("</script>")]
    assert json.loads(body.replace("<\\/", "</")) == {"x": "</script><b>"}
    with pytest.raises(ValueError):
        render.render({}, template="no placeholder")


def test_real_template_has_the_placeholder():
    assert render.PLACEHOLDER in render.TEMPLATE.read_text()


# ---------------------------------------------------------------------------- a new state, config only
def test_new_state_needs_only_config_and_processed_tables(tmp_path):
    cfg = tmp_path / "config"
    (cfg / "states").mkdir(parents=True)
    (cfg / "reforms").mkdir()
    (cfg / "states" / "zz.yaml").write_text(
        "state: ZZ\nname: Zedland\nfips: '99'\nbps_region: Test\nparcel_sources: {'*': regional}\n"
    )
    (cfg / "reforms" / "zz.csv").write_text(
        "reform_id,state,jurisdiction_geoid,theme,status,adoption_date,effective_date,coder_agreement,component,"
        "source_url\nZZ-1,ZZ,9900001,adu,in_force,2021-01-01,2021-02-01,agree,ADUs by right,https://x\n"
    )
    store = DataStore(tmp_path / "data")
    jur = pd.DataFrame(
        {
            "geoid": ["9900001", "9900002", "99001"],
            "name": ["Alpha city", "Beta city", "Alpha County Unincorporated Area"],
            "bps_id": ["1", "2", "3"],
            "county_geoid": ["99001"] * 3,
            "state": ["ZZ"] * 3,
            "kind": ["place", "place", "county_unincorporated"],
            "pop_2020": pd.array([600, 300, None], dtype="Int64"),
            "in_bps": [True] * 3,
            "data_tier": pd.array([2, 3, 3], dtype="Int64"),
        }
    )
    for table, df in {
        "jurisdictions": jur,
        "parcels": _parcels([("9900001", "99001", 2026, "SF_DETACHED", None)] * 3),
    }.items():
        folder = store.processed("ZZ", table)
        folder.mkdir(parents=True)
        df.to_parquet(folder / ("regional.parquet" if table == "parcels" else f"{table}.parquet"))
    popdf = pd.DataFrame(
        {
            "geo": ["county:99001", "state:99"],
            "name": ["Alpha County", "Zedland"],
            "year": [2020, 2020],
            "population": [1000, 1000],
            "vintage": [2025, 2025],
        }
    )

    s = sm.summarize_state("ZZ", store, pep=popdf, config_dir=cfg, points=False)
    t = s["totals"]
    assert (t["jurisdictions"], t["jurisdictions_covered"], t["parcels"]) == (3, 1, 3)
    assert t["population"] == 1000  # 600 + 300 + the 100 estimated for the unincorporated area
    assert t["population_covered_share"] == 0.6
    assert s["reforms"][0]["place"] == "Alpha city" and t["reforms_by_theme"] == {"adu": 1}
    assert s["counties"][0]["name"] == "Alpha County"
    json.dumps(s)  # the page embeds it as JSON


def test_lots_estimated_counts_census_fallback_jurisdictions():
    """Three towns: two on the Census fallback, one on a parcel roll -> 2. No basis column -> 0."""
    js = pd.DataFrame({"eligible_adu_basis": ["acs_sf_fallback", "parcels", "acs_sf_fallback", None]})
    assert sm.lots_estimated(js) == 2
    assert sm.lots_estimated(pd.DataFrame({"name": ["a"]})) == 0
