"""MN V0 comparison functions on synthetic tables (no network, no real data)."""

import pandas as pd

from lotline.adapters.states.mn import v0_mn as v

MPLS, EDINA = "2743000", "2718188"


def _permits() -> pd.DataFrame:
    rows = [
        # source, geoid, year, type, units, class_raw
        (v.METC, EDINA, 2020, "SFD", 10, "SFD:NU"),
        (v.METC, EDINA, 2020, "TH", 6, "TH:NU"),
        (v.METC, EDINA, 2020, "DTQ", 4, "DTQ:NU"),
        (v.METC, EDINA, 2020, "MF5", 100, "MF5:NU"),
        (v.METC, EDINA, 2020, "SFD", 3, "SFD:RM"),  # removal: not new construction
        (v.METC, MPLS, 2020, "ADU", 2, "ADU:NU"),
        (v.METC, MPLS, 2020, "SFD", 5, "SFD:NU"),
        (v.CCS, MPLS, 2020, "SFD", 1, "Res:SFD:New:Closed"),
        (v.CCS, MPLS, 2020, "SFD", 1, "Res:SFD:New:Closed"),
        (v.CCS, MPLS, 2020, "U2", 2, "Res:TFD:Conversion:Closed"),  # conversion: left out
        (v.CCS, MPLS, 2020, "ADU", 1, "Res:SFD:Remodel:Closed"),  # ADUs of any work type
        (v.CCS, MPLS, 2020, "SFD", 1, "Res:SFD:New:Cancelled"),
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "source",
            "jurisdiction_geoid",
            "issue_year",
            "building_type_std",
            "units_new",
            "permit_class_raw",
        ],
    )
    return df.assign(
        units_new=df["units_new"].astype("Int64"),
        parcel_id=pd.NA,
        issue_date=pd.NaT,
        is_demolition=False,
        permit_id=[f"p{i}" for i in range(len(df))],
    )


BPS = pd.DataFrame(
    {
        "geoid": [EDINA, MPLS],
        "year": [2020, 2020],
        "units_1": [20, 5],
        "units_2": [2, 0],
        "units_3_4": [0, 0],
        "units_5p": [100, 0],
    }
)


def test_metc_classes_and_new_construction_only():
    m = v.metc_new_units(_permits()).set_index(["jurisdiction_geoid", "size_class"])["local"]
    assert m[(EDINA, "1 unit")] == 16  # SFD + TH, removals left out
    assert m[(EDINA, "2-4 units")] == 4 and m[(EDINA, "5+ units")] == 100
    assert m[(MPLS, "ADU")] == 2


def test_compare_and_summary():
    cmp = v.compare(v.metc_new_units(_permits()), v.bps_units(BPS)).set_index(
        ["jurisdiction_geoid", "size_class"]
    )
    assert round(cmp.loc[(EDINA, "1 unit"), "gap"], 6) == -0.2
    assert cmp.loc[(EDINA, "2-4 units"), "gap"] == 1.0
    s = v.summarize_gaps(cmp.reset_index(), min_units=20).set_index("class")
    assert s.loc["1 unit", "within_10pct"] == "0%" and s.loc["5+ units", "within_10pct"] == "100%"


def test_ccs_new_buildings_dedupe_and_adus():
    c = v.ccs_new_units(_permits()).set_index("size_class")["ccs"]
    assert c["1 unit"] == 2  # cancelled left out
    assert "2-4 units" not in c.index  # the conversion is not a new building
    assert c["ADU"] == 1


def test_adu_table_published_and_breaks():
    adu = v.adu_by_year(_permits())
    assert adu.set_index("year").loc[2020].tolist() == [2, 2, 1]
    series = pd.DataFrame({"year": [2016, 2017, 2018, 2019], "x": [0, 20, 8, 21]})
    assert v.regime_breaks(series, "x") == {
        "first_year": 2017,
        "jumps": [2018],
    }  # 2019: previous year under 10
    pub = v.adu_vs_published(
        pd.DataFrame(
            {"year": [2016], "metc_metro": [150], "metc_minneapolis": [100], "ccs_minneapolis": [116]}
        )
    )
    assert pub.loc[0, "ratio"] == 0.5 and pub.loc[1, "ccs_inferred"] == 116
