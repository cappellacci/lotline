"""Medford TRAKiT permits adapter on synthetic fixtures (no network, no real data).

Checks the module docstring's method: the ADU subtype on new construction is the flag, remodels of an
existing ADU are not ADUs, a house + ADU permit becomes two rows (co-built for D-041), dropped statuses and
cities, types and units, and that load() keeps Oregon blind before V9's release.
"""

import importlib

import pandas as pd

from lotline import registry
from lotline.model import calibrate_adu as ca
from lotline.schemas import assert_conforms
from lotline.validation import holdout

md = importlib.import_module("lotline.adapters.states.or.medford_permits")
D041 = {"exclude_cobuilt": True, "window": 1, "report_rate": 1.0}


def ms(day):
    return float("nan") if day is None or pd.isna(day) else pd.Timestamp(day).value // 10**6


# OBJECTID, PERMIT_NO, PermitType, PermitSubType, STATUS, ISSUED, SITE_APN, SITE_CITY, DESCRIPTION
ROWS = [
    (
        1,
        "BRNW21-1",
        "RESIDENTIAL NEW",
        "ADU REDUCED SDC",
        "C OF O ISSUED",
        "2021-03-01",
        "371W01AA100",
        "MEDFORD",
        "CONVERT DETACHED GARAGE TO ADU 1/1",
    ),
    (
        2,
        "BRNW21-2",
        "RESIDENTIAL NEW",
        "ADU",
        "ISSUED",
        "2021-05-01",
        "371W01AA200",
        "MEDFORD",
        "1 STY / 1, 1",
    ),
    (
        3,
        "BRNW22-3",
        "RESIDENTIAL NEW",
        "SFR W/ ADU REDUCED SDC",
        "C OF O ISSUED",
        "2022-02-01",
        "371W01AA300",
        "MEDFORD",
        "2 STY : 3/2.5 W/ ADU 1/1 ON TOP OF GARAGE",
    ),
    (
        4,
        "NSMF23-4",
        "RESIDENTIAL NEW MASTER WITH ADU REDUCED SDC",
        "ADDITIONAL",
        "FINALED",
        "2023-01-10",
        "371W01AA400",
        "MEDFORD",
        "2 STY - SFR 3/2.5 ADU 1/1 - MASTER",
    ),
    (
        5,
        "BRRM22-5",
        "RESIDENTIAL REMODEL",
        "ADU",
        "FINALED",
        "2022-06-01",
        "371W01AA500",
        "MEDFORD",
        "FIRE DAMAGE REMODEL",
    ),  # an existing ADU
    (
        6,
        "BRNW22-6",
        "RESIDENTIAL NEW",
        "SFR",
        "C OF O ISSUED",
        "2022-07-01",
        "371W01AA600",
        "MEDFORD",
        "1 STY : 3/2",
    ),
    (
        7,
        "BRNW22-7",
        "RESIDENTIAL NEW",
        "DUPLEX",
        "ISSUED",
        "2022-07-01",
        "371W01AA700",
        "",
        "2 STY Units 1 & 2",
    ),
    (
        8,
        "BRNW25-8",
        "RESIDENTIAL NEW",
        "COTTAGE",
        "ISSUED",
        "2025-05-01",
        "371W01AA800",
        "MEDFORD",
        "Bldg 1 of 6",
    ),
    (9, "BRNW22-9", "RESIDENTIAL NEW", "ADU", "VOIDED", "2022-07-01", "371W01AA900", "MEDFORD", "ADU"),
    (
        10,
        "BRNW22-10",
        "RESIDENTIAL NEW",
        "ADU",
        "ISSUED",
        "2022-07-01",
        "362W01AA100",
        "CENTRAL POINT",
        "ADU",
    ),
    (11, "BRNW22-11", "RESIDENTIAL NEW", "ADU", "APPROVED", None, "371W01AA110", "MEDFORD", "ADU"),
    (
        12,
        "BRNW22-12",
        "RESIDENTIAL NEW",
        "GARAGE OR CARPORT",
        "FINALED",
        "2022-08-01",
        "371W01AA120",
        "MEDFORD",
        "NEW CARPORT",
    ),
    (
        13,
        "BDEM22-13",
        "DEMOLITION",
        "DEMO SFR OR DUPLEX",
        "FINALED",
        "2022-01-05",
        "371W01AA600",
        "MEDFORD",
        "",
    ),
]
COLS = [
    "OBJECTID",
    "PERMIT_NO",
    "PermitType",
    "PermitSubType",
    "STATUS",
    "ISSUED",
    "SITE_APN",
    "SITE_CITY",
    "DESCRIPTION",
]


def raw() -> pd.DataFrame:
    df = pd.DataFrame(ROWS, columns=COLS)
    df["ISSUED"] = df["ISSUED"].map(ms)
    df["APPLIED"] = df["ISSUED"] - 86_400_000 * 30
    df["FINALED"] = df["ISSUED"] + 86_400_000 * 200
    for c in set(md.FIELDS) - set(df.columns):
        df[c] = None
    return df[md.FIELDS]


def permits() -> pd.DataFrame:
    return md.build(raw()).set_index("permit_id")


def test_conforms_and_never_requests_personal_fields():
    assert_conforms(md.build(raw()), "permits")
    assert not md.PERSONAL & set(md.FIELDS)


def test_adu_flag_on_new_construction_only():
    p = permits()
    adu = set(p.index[p["building_type_std"] == "ADU"])
    assert adu == {"BRNW21-1", "BRNW21-2", "BRNW22-3#adu", "NSMF23-4#adu"}
    assert p.loc["BRRM22-5", "building_type_std"] == "OTHER" and p.loc["BRRM22-5", "units_new"] == 0
    assert p.loc["BRNW21-1", "adu_type"] == "detached"  # from the description
    assert p.loc["BRNW21-2", "adu_type"] == "unknown"
    assert p.loc["BRNW22-3#house", "building_type_std"] == "SFD" and p.loc["NSMF23-4#house", "units_new"] == 1


def test_dropped_rows_types_and_units():
    p = permits()
    for gone in ("BRNW22-9", "BRNW22-10", "BRNW22-11"):  # voided, Central Point, never issued
        assert gone not in p.index
    assert (
        p.loc["BRNW22-7", "building_type_std"] == "U2" and p.loc["BRNW22-7", "units_new"] == 2
    )  # blank city
    assert p.loc["BRNW25-8", "building_type_std"] == "DTQ"
    assert p.loc["BRNW22-12", "building_type_std"] == "OTHER" and p.loc["BRNW22-12", "units_new"] == 0
    assert bool(p.loc["BDEM22-13", "is_demolition"]) and p.loc["BDEM22-13", "units_new"] == 0
    assert (p["jurisdiction_geoid"] == md.MEDFORD).all()


def test_d041_counts_drop_cobuilt_adus():
    """2021: two standalone ADUs. 2022: BRNW22-3's ADU is co-built with its house. 2023: NSMF23-4 likewise."""
    p = md.build(raw())
    got = ca.adu_counts(p, 2020, 2025, D041).set_index("year")["adu_permits"].to_dict()
    assert got[2021] == 2 and got.get(2022, 0) == 0 and got.get(2023, 0) == 0
    flagged = ca.adu_counts(p, 2020, 2025, D041 | {"exclude_cobuilt": False}).set_index("year")["adu_permits"]
    assert flagged.to_dict()[2022] == 1 and flagged.to_dict()[2023] == 1


def test_load_respects_an_unreleased_holdout(monkeypatch):
    monkeypatch.setattr(md, "download", lambda store, refresh=False: raw())
    (v9,) = holdout.holdouts_for("OR")
    unreleased = v9.model_copy(update={"released_on": None, "released_note": None})
    monkeypatch.setattr(holdout, "holdouts_for", lambda state: [unreleased])
    assert md.load("OR", store=None).empty


def test_registered_for_oregon():
    assert "medford_permits" in registry.sources_for("OR")
