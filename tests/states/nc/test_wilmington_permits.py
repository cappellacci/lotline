"""New Hanover County (Wilmington) permits adapter on synthetic rows (no network, no real data).

Checks the module docstring: which permits are kept, the building type and units of each work class, the ADU
rule (ADU terms, the county's own terms, and the vetoes: a note ruling an ADU out, an existing ADU, an ADU on
another permit, a duplex), jurisdictions by point with the DISTRICT fallback, the PID → PIN parcel join, and
that personal fields are never requested or kept.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.nc import wilmington_permits as wp
from lotline.io import DataStore
from lotline.schemas import assert_conforms

RB, ACC, ADD = "NHC Residential Building", "NHC Residential Accessory", "NHC Residential Addition"
LEGACY = " - R3SingleFamilyResidence Structure"


def ms(day: str | None) -> int | None:
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000) if isinstance(day, str) else None


# PERMIT_NUMBER, PERMIT_TYPE, WORK_CLASS, PERMIT_STATUS, ISSUE_DATE, DESCRIPTION
ROWS = [
    ("W1", RB, "NSFR", "Complete", "2024-03-01", "New Construction Single Family Home"),
    ("W2", RB, "NSFR", "Issued", "2025-04-01", "SFR - 1BR 1BA - ADU"),
    ("W3", RB, "New Single Family Residence", "Complete", "2022-05-05",
     "New Accessory Dwelling Unit above existing detached garage"),
    ("W4", ACC, "New", "Complete", "2025-06-01",
     "New detached garage/Not to be used as an accessory dwelling unit/have cooking appliances"),
    ("W5", RB, "NSFR", "Complete", "2024-07-01", "single family residence with ADU - ADU ON SEPARATE PERMIT"),
    ("W6", RB, "NSFR", "Complete", "2023-08-01", "NEW ADU / Primary dwelling permitted separately"),
    ("W7", ADD, "Addition", "Complete", "2020-09-01", "attached accessory apartment addition."),
    ("W8", ADD, "Addition", "Complete", "2025-10-01", "Renovate existing ADU to same floor plan"),
    ("W9", RB, "Converted", "Complete", "2016-02-01", "SMITH/NEW DETACHED ACCESSORY APARTMENT/SBK" + LEGACY),
    ("W10", RB, "Converted", "Complete", "2017-03-01", "ROBUCK / NEW HOUSE/RTS" + LEGACY),
    ("W11", RB, "Converted", "Complete", "2017-03-02", "KITCHEN BATH REMODEL/RTS" + LEGACY),
    ("W12", RB, "Converted", "Complete", "2017-03-03",
     "5031 - A PEACH AVE/NEW ATTACHED ACCESSORY APARTMENT - R3ResidentialOneTwoFamily Job master"),
    ("W13", RB, "NSFR", "Void", "2024-01-01", "NEW ADU"),
    ("W14", RB, "NSFR", "In Review", None, "NEW ADU"),
    ("W15", "NHC Residential Demolition", "Demolition", "Complete", "2021-01-05", "demo single family house"),
    ("W16", "NHC Residential Relocation ", "Mobile Home", "Complete", "2020-02-02", "place double wide"),
    ("W17", ACC, "New", "Complete", "2019-05-05", "24x30 detached garage"),
    ("W18", RB, "NSFR", "Complete", "2023-06-06", "DUPLEX - ADU MAIN UNIT PERMIT 23-014796"),
    ("W19", RB, "NSFR", "Expired", "2024-06-06", "NEW ADU_New construction guest house with street entry"),
    ("W20", RB, "NSFR", "Complete", "2024-06-07", "Construct new garage apartment with breezeway"),
    ("W21", RB, "Alteration/Renovation", "Complete", "2022-01-01", "Remodel kitchen and baths"),
    ("W22", "NHC Commercial Building", "New", "Complete", "2021-04-04", "New office building shell"),
    ("W23", RB, "NSFR", "Complete", "2023-02-02", "***THIS IS MAIN HOUSE ADU IS PERMIT 23-009777***"),
    ("W24", ACC, "New", "Complete", "2026-01-01", "Pool cabana for adult guests"),
]  # fmt: skip


def raw_frame() -> pd.DataFrame:
    df = pd.DataFrame(
        ROWS,
        columns=["PERMIT_NUMBER", "PERMIT_TYPE", "WORK_CLASS", "PERMIT_STATUS", "ISSUE_DATE", "DESCRIPTION"],
    )
    df["ISSUE_DATE"] = df["ISSUE_DATE"].map(ms)
    df["OBJECTID"] = range(len(df))
    df["APPLICATION_DATE"] = None
    df["FINALED_DATE"] = None
    df.loc[0, "FINALED_DATE"] = ms("2024-11-01")
    df["DISTRICT"] = "City of Wilmington"
    df["SQUARE_FEET"] = 900.0
    df["VALUATION"] = 150000.0
    df["MAIN_ZONE"] = "R-5"
    df["PID"] = [f"R0{i:04d}-001-001-000" for i in range(len(df))]
    df["Lat"] = 34.2
    df["Lon"] = -77.9
    return df


def place_for(raw: pd.DataFrame) -> pd.Series:
    """Every point in Wilmington except W17 (outside any place) and W21 (no point)."""
    place = pd.Series("3774440", index=raw.index, dtype=object)
    place[raw["PERMIT_NUMBER"] == "W17"] = None
    return place


def permits() -> pd.DataFrame:
    raw = raw_frame()
    raw.loc[raw["PERMIT_NUMBER"] == "W21", ["Lat", "Lon"]] = None
    raw.loc[raw["PERMIT_NUMBER"] == "W21", "DISTRICT"] = "New Hanover County"
    pins = {"R00000-001-001-000": "371293114-97-9735.000"}
    return wp.build(raw, place_for(raw), pins).set_index("permit_id")


def row(p: pd.DataFrame, pid: str) -> tuple:
    r = p.loc[pid]
    return (r.building_type_std, None if pd.isna(r.units_new) else int(r.units_new), r.units_confidence)


def test_conforms_and_kept_permits():
    p = permits()
    assert_conforms(p.reset_index(), "permits")
    assert {"W13", "W14"}.isdisjoint(p.index)  # void; not issued
    assert "W12" not in p.index  # converted job master: a duplicate of the structure permit
    assert len(p) == len(ROWS) - 3


def test_new_houses_and_other_work():
    p = permits()
    assert row(p, "W1") == ("SFD", 1, "derived")
    assert p.loc["W1", "type_confidence"] == "high"
    assert row(p, "W10") == ("SFD", 1, "inferred")  # converted record: "NEW HOUSE" from the description
    assert row(p, "W11") == ("SFD", 0, "derived")  # converted alteration
    assert row(p, "W21") == ("SFD", 0, "derived")
    assert row(p, "W16") == ("OTHER", 1, "derived")  # manufactured home placed
    assert row(p, "W17") == ("OTHER", 0, "derived")  # garage
    assert row(p, "W22") == ("UNKNOWN", None, "unknown")  # new commercial building, no dwelling named
    assert bool(p.loc["W15", "is_demolition"]) and p.loc["W15", "units_new"] == 0


@pytest.mark.parametrize("pid", ["W2", "W3", "W6", "W7", "W9", "W19", "W20"])
def test_adus_named_in_the_description(pid):
    p = permits()
    assert row(p, pid) == ("ADU", 1, "inferred")
    assert p.loc[pid, "type_confidence"] == "inferred"


def test_adu_kind():
    p = permits()
    assert p.loc["W9", "adu_type"] == "detached"
    assert p.loc["W7", "adu_type"] == "attached"
    assert p.loc["W2", "adu_type"] == "unknown"


@pytest.mark.parametrize(
    "pid, why",
    [
        ("W4", "a note rules an ADU out"),
        ("W5", "the ADU is on another permit"),
        ("W8", "work on an existing ADU"),
        ("W18", "a duplex"),
        ("W23", "this is the main house; the ADU has its own permit"),
        ("W24", "'adult' is not 'ADU'"),
    ],
)
def test_adu_vetoes(pid, why):
    assert permits().loc[pid, "building_type_std"] != "ADU", why


def test_is_adu_text_examples():
    yes = [
        "single family residential (ADU)",
        "CONSTRUCT ACCESSORY APARTMENT Unit A / Primary Dwelling permitted separately",
        "ADU UNIT A / SFR UNDER #23-023282",
        "BASSWAVES-IN-LAW COTTAGE BEHIND MAIN HOUSE - UNIT A",
        "Garage with 511 sf apartment over",
    ]
    no = [
        "New SFR ONLY / ADU at rear of parcel permitted separately",
        "Build new single family house and adu./New house only.",
        "** PERMIT ONLY FOR MAIN HOUSE** Second home meets ADU requirements",
        "residential addition **Accessory Dwelling Unit NEEDS TO BE PERMITED SEPARATELY**",
        "NEW SFR - construct new single family dwelling in front of existing detached ADU",
        "Shed 24x38 ***SHALL NOT BE AN ADU (Accessory Dwelling Unit)",
        "detached garage (non-adu)",
        "Build guest house on property",
    ]
    assert all(wp.is_adu_text(wp.clean_description(t)) for t in yes)
    assert not any(wp.is_adu_text(wp.clean_description(t)) for t in no)


def test_jurisdictions_by_point_then_district():
    p = permits()
    assert p.loc["W1", "jurisdiction_geoid"] == "3774440"
    assert p.loc["W17", "jurisdiction_geoid"] == "37129"  # point outside every place
    assert p.loc["W21", "jurisdiction_geoid"] == "37129"  # no point: the DISTRICT label


def test_parcels_dates_and_fields():
    p = permits()
    assert p.loc["W1", "parcel_id"] == "371293114-97-9735.000"
    assert pd.isna(p.loc["W2", "parcel_id"])  # PID not in the parcel layer
    assert p.loc["W1", "final_date"] == pd.Timestamp("2024-11-01")
    assert p.loc["W1", "final_date_type"] == "final_inspection"
    assert pd.isna(p.loc["W2", "final_date_type"])
    assert p.loc["W1", "zoning_raw"] == "R-5" and p.loc["W1", "floor_area_sqft"] == 900.0
    assert p.loc["W16", "permit_class_raw"] == "NHC Residential Relocation | Mobile Home"


def test_pid_to_pin_drops_ambiguous_pids():
    parcels = pd.DataFrame(
        {"PID": ["A", "B", "B", "C", ""], "PIN": ["3114-1", "3114-2", "3114-3", "3114-4", "3114-5"]}
    )
    assert wp.pid_to_pin(parcels) == {"A": "371293114-1", "C": "371293114-4"}


def test_privacy():
    assert not set(wp.OUT_FIELDS) & wp.PERSONAL
    out = permits()
    assert "DESCRIPTION" not in out.columns
    assert not out.astype(str).apply(lambda c: c.str.contains("ROBUCK")).any().any()


def test_load_validates(tmp_path, monkeypatch):
    from lotline import geo

    monkeypatch.setattr(wp, "download", lambda store, refresh=False: raw_frame())
    monkeypatch.setattr(
        wp, "download_parcels", lambda store, refresh=False: pd.DataFrame({"PID": [], "PIN": []})
    )
    monkeypatch.setattr(
        geo, "place_or_township", lambda lon, lat, state, store, refresh=False: place_for(raw_frame())
    )
    out = wp.load("NC", DataStore(tmp_path))
    assert len(out) == len(ROWS) - 3
    with pytest.raises(ValueError):
        wp.load("OH", DataStore(tmp_path))


def test_registered():
    assert registry.sources_for("NC")["wilmington_permits"].module.TABLE == "permits"
