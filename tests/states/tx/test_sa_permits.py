"""San Antonio permits adapter on synthetic rows (no network, no real data).

Checks the module docstring: which permit types are kept, one row per permit number (revisions and
combination permits), ADUs from the city's ADU permit type, new houses as one unit unless the parser reads
another type, ETJ permits filed under the Bexar County remainder, dates, and privacy.
"""

import pandas as pd

from lotline import registry
from lotline.adapters.states.tx import sa_permits as sa
from lotline.io import DataStore
from lotline.schemas import assert_conforms

CITY = "1 MAIN ST, City of San Antonio, TX 78204"
ETJ = "9 RANCH RD, City of San Antonio ETJ, TX 78255"

# PERMIT TYPE, PERMIT #, PROJECT NAME, WORK TYPE, ADDRESS, SUBMITTED, ISSUED, CD
ROWS = [
    (sa.ADU, "ADP-1", "Smith casita - detached ADU", "Existing", CITY, "2021-01-07", "2022-07-27", "1"),
    (sa.ADU, "ADP-1", "Smith casita - detached ADU", "Existing", CITY, "2023-09-15", "2022-07-27", "1"),
    (sa.ADU, "ADP-2", "Garcia Residence", "Existing", CITY, "2023-02-01", "2023-03-01", "5"),
    (sa.NEW_RES, "RBP-1", "Lot 12 Block 3", "New", CITY, "2023-01-05", "2023-02-01", "4"),
    (sa.NEW_RES, "RBP-2", "New duplex", "New", CITY, "2024-01-05", "2024-02-01", "4"),
    (sa.NEW_RES, "RBP-3", "Lot 7", "New", ETJ, "2024-03-05", "2024-04-01", "0"),
    (sa.NEW_RES, "RBP-4", "Lot 8", "New", "8 HILL CT, City of San Antonio, TX 78255", "2024-03-05",
     "2024-04-01", "0"),
    ("Electrical General Permit", "RBP-1", "Lot 12 Block 3", "New", CITY, "2023-01-05", "2023-02-01", "4"),
    ("Residential Fence Permit", "FEN-1", "fence", "Existing", CITY, "2023-01-05", "2023-02-01", "4"),
    (sa.ACCESSORY[0], "ACC-1", "convert garage to accessory dwelling unit", "Existing", CITY, "2022-05-05",
     "2022-06-06", "2"),
    (sa.ACCESSORY[1], "ACC-2", "storage shed", "New", CITY, "2022-05-05", "2022-06-06", "2"),
    (sa.FOUNDATION, "FDN-1", "slab", "New", CITY, "2022-05-05", "2022-06-06", "2"),
    (sa.NEW_COMM, "COM-1", "Building No: 3; 24 apartments", "New", CITY, "2021-05-05", "2021-08-08", "8"),
    (sa.NEW_COMM, "COM-2", "Taco Palenque", "New", CITY, "2021-05-05", "2021-08-08", "8"),
    (sa.DEMOLITION, "DEM-1", "demo single family house", "Existing", CITY, "2025-01-01", "2025-01-15", "3"),
    (sa.NEW_RES, "RBP-5", "Lot 9", "New", CITY, "2025-01-01", None, "3"),
]  # fmt: skip


def raw_frame() -> pd.DataFrame:
    df = pd.DataFrame(
        ROWS,
        columns=["PERMIT TYPE", "PERMIT #", "PROJECT NAME", "WORK TYPE", "ADDRESS", "DATE SUBMITTED",
                 "DATE ISSUED", "CD"],
    )  # fmt: skip
    df["DECLARED VALUATION"] = "150000.0"
    df["AREA (SF)"] = "800"
    return df.astype("string")


def permits() -> pd.DataFrame:
    return sa.build(raw_frame()).set_index("permit_id")


def row(p: pd.DataFrame, pid: str) -> tuple:
    r = p.loc[pid]
    return (r.building_type_std, r.units_new, r.units_confidence)


def test_conforms_and_kept_types():
    out = sa.build(raw_frame())
    assert_conforms(out, "permits")
    assert "FEN-1" not in set(out.permit_id)  # fences are not kept
    assert "RBP-5" not in set(out.permit_id)  # never issued


def test_one_row_per_permit():
    p = permits()
    assert p.loc["ADP-1", "application_date"] == pd.Timestamp("2021-01-07")  # earliest revision
    assert p.loc["RBP-1", "permit_class_raw"] == f"{sa.NEW_RES} | New"  # building type wins over trade


def test_adus():
    p = permits()
    assert row(p, "ADP-1") == ("ADU", 1, "derived")
    assert p.loc["ADP-1", "type_confidence"] == "high"
    assert p.loc["ADP-1", "adu_type"] == "detached"
    assert p.loc["ADP-2", "adu_type"] == "unknown"
    assert row(p, "ACC-1") == ("ADU", 1, "inferred")
    assert bool(p.loc["ACC-1", "is_conversion"])
    assert row(p, "ACC-2") == ("OTHER", 0, "derived")


def test_new_buildings():
    p = permits()
    assert row(p, "RBP-1") == ("SFD", 1, "derived")
    assert p.loc["RBP-1", "type_confidence"] == "inferred"
    assert row(p, "RBP-2") == ("U2", 2, "inferred")
    assert row(p, "FDN-1") == ("UNKNOWN", 0, "derived")
    assert row(p, "COM-1") == ("MF5", 24, "inferred")
    t, n, c = row(p, "COM-2")
    assert t == "UNKNOWN" and pd.isna(n) and c == "unknown"


def test_demolition():
    p = permits()
    assert bool(p.loc["DEM-1", "is_demolition"])
    assert p.loc["DEM-1", "units_new"] == 0 and p.loc["DEM-1", "units_removed"] == 1


def test_etj_permits_go_to_the_county_remainder():
    p = permits()
    assert p.loc["RBP-3", "jurisdiction_geoid"] == sa.BEXAR_REMAINDER  # address says ETJ
    assert p.loc["RBP-4", "jurisdiction_geoid"] == sa.BEXAR_REMAINDER  # council district 0
    assert p.loc["RBP-1", "jurisdiction_geoid"] == sa.SAN_ANTONIO


def test_dates():
    p = permits()
    assert p.loc["RBP-1", "issue_date"] == pd.Timestamp("2023-02-01")
    assert p.loc["RBP-1", "issue_year"] == 2023 and p.loc["RBP-1", "date_precision"] == "day"


def test_privacy():
    assert not set(sa.READ_COLUMNS) & sa.PERSONAL
    out = sa.build(raw_frame())
    assert not {"ADDRESS", "PROJECT NAME"} & set(out.columns)
    assert not out.astype(str).apply(lambda c: c.str.contains("Smith|MAIN ST")).any().any()


def test_load_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(sa, "download", lambda store, refresh=False: raw_frame())
    out = sa.load("TX", DataStore(tmp_path))
    assert len(out) == 12


def test_registered():
    assert registry.sources_for("TX")["sa_permits"].module.TABLE == "permits"
