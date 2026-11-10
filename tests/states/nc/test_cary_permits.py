"""Cary permits adapter on synthetic rows (no network, no real data).

Checks the module docstring: kept rows (building/demolition, issued, not cancelled, Town of Cary), building
type and units from the permit-type crosswalk and Housing Units, the Cary ADU rule (hand-worked phrasings),
padded PINs, final dates, reading the portal's semicolon CSV export by its labels, and that personal columns
are never read or kept.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.nc import cary_permits as cp
from lotline.io import DataStore
from lotline.schemas import assert_conforms

HEADER = [
    "Permit Number", "Description", "Status Current Mapped", "Applied Date", "Issue Date", "Completed Date",
    "CO Issued Date", "Original Address 1", "PIN", "Jurisdiction", "Total SqFt", "Housing Units",
    "Project Cost", "Permit Class Mapped", "Work Class", "Permit Type", "Permit Type Mapped", "Owner Name",
]  # fmt: skip

# number, description, status, issued, PIN, jurisdiction, units, class, work class, type, type mapped
ROWS = [
    ("C1", "NEW SFD", "Occupancy", "2021-03-01", "764681923", "TC", "1", "Residential", "New", "B101",
     "Building"),
    ("C2", "TOWNHOME LOT 4", "Occupancy", "2021-04-01", "0743543633", "TC", "", "Residential", "New", "B102",
     "Building"),
    ("C3", "APARTMENTS BLDG 2", "Occupancy", "2022-05-05", "", "TC", "48", "Residential", "New", "B105",
     "Building"),
    ("C4", "APARTMENTS BLDG 3", "Occupancy", "2022-05-06", "", "TC", "", "Residential", "New", "B105",
     "Building"),
    ("C5", "Detached ADU", "Occupancy", "2024-03-11", "764792762", "TC", "", "Residential", "Existing",
     "B438", "Building"),
    ("C6", "ADU ADDITION W/ PORCH", "Permit Issued", "2026-08-07", "765124079", "TC", "", "Residential",
     "Existing", "B434", "Building"),
    ("C7", "Remodel Lower Level for ADU", "Occupancy", "2024-11-08", "762198676", "TC", "", "Residential",
     "Existing", "B434", "Building"),
    ("C8", "CONVERT EXISTING DETACHED GARAGE TO ADU", "Occupancy", "2026-10-19", "763362156", "TC", "",
     "Residential", "Existing", "B438", "Building"),
    ("C9", "REPAIR EXISTING ADU", "Occupancy", "2025-01-01", "763362157", "TC", "", "Residential", "Existing",
     "B434", "Building"),
    ("C10", "RESIDENTIAL CARE HOME FOR 6 ADULTS", "Occupancy", "2023-10-27", "753273049", "TC", "",
     "Residential", "Existing", "B434", "Building"),
    ("C11", "DEMO SFD & ADU HOOKED TO TOWN WATER/SEWER", "Occupancy", "2026-06-24", "763687783", "TC", "",
     "Residential", "Existing", "B645", "Demolition"),
    ("C12", "SCREEN PORCH & DECK", "Occupancy", "2026-01-12", "760284365", "TC", "", "Residential",
     "Existing", "B417", "Building"),
    ("C13", "NEW SFD", "Permit Cancelled", "2021-03-02", "764681924", "TC", "1", "Residential", "New", "B101",
     "Building"),
    ("C14", "NEW SFD", "In Review", "", "764681925", "TC", "1", "Residential", "New", "B101", "Building"),
    ("C15", "HVAC CHANGE OUT RESIDENTIAL", "Occupancy", "2019-01-02", "763062468", "TC", "", "Residential",
     "Existing", "M107", "Mechanical"),
    ("C16", "INTERIOR ALTERATION", "Occupancy", "2023-02-02", "772756633", "TC", "", "Non-Residential",
     "Existing", "B435", "Building"),
    ("C17", "DETACHED ADU w/ FULL BATH", "Occupancy", "2026-04-09", "774378656", "WC", "", "Residential",
     "Existing", "B434", "Building"),
    ("C18", "NEW ACCESSORY DWELLING UNIT", "Permit Issued", "2026-10-01", "752994121", "TC", "",
     "Residential", "New", "ADU", ""),  # the ADU type carries no Permit Type Mapped
    ("C19", "FINISH BASEMENT - ADU", "Occupancy", "2026-07-23", "", "TC", "", "Non-Residential", "Existing",
     "B434", "Building"),
    ("C21", "NEW SFD", "Occupancy", "2021-06-01", "", "CC", "1", "Residential", "New", "B101", "Building"),
    ("C22", "NEW SFD", "Occupancy", "2021-06-01", "", "TOM", "1", "Residential", "New", "B101", "Building"),
    ("C20", "NEW SFD WITH ADU", "Occupancy", "2025-05-05", "726734683", "TC", "1", "Residential", "New",
     "B101", "Building"),
]  # fmt: skip


def raw_frame() -> pd.DataFrame:
    rows = []
    for num, desc, status, issued, pin, jur, units, cls, work, ptype, mapped in ROWS:
        rows.append({
            "permit_number": num, "description": desc, "status_mapped": status,
            "applied": "2020-12-01" if issued else "", "issued": issued, "completed": "", "co": "",
            "pin": pin,
            "jurisdiction": jur, "sqft": "1,200", "units": units, "cost": "$150,000.00", "class_mapped": cls,
            "work_class": work, "ptype": ptype, "ptype_mapped": mapped,
        })  # fmt: skip
    df = pd.DataFrame(rows)
    df.loc[0, ["completed", "co"]] = ["2021-09-25", "2021-10-01"]
    df.loc[1, "completed"] = "2021-12-01"
    return df


def permits() -> pd.DataFrame:
    return cp.build(raw_frame()).set_index("permit_id")


def row(p: pd.DataFrame, pid: str) -> tuple:
    r = p.loc[pid]
    return (r.building_type_std, r.units_new, r.units_confidence)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Detached ADU", "detached"),
        ("Build 625 SF Detached ADU", "detached"),
        ("2ND FL ADU OVER DET. GARAGE; DECK", "detached"),
        ("CONVERT EXISTING DETACHED GARAGE TO ADU", "detached"),  # "existing" is the garage, not the ADU
        ("FINISH BASEMENT FOR ADU; DECK REPAIRS", "internal_conversion"),
        ("Remodel Lower Level for ADU", "internal_conversion"),
        ("CONVERT BASEMENT TO ADU", "internal_conversion"),
        ("Attached ADU at Rear Yard", "attached"),
        ("ADU ADDITION W/ PORCH", "attached"),
        ("3 bedroom 1.5 bath accessory dwelling unit", "unknown"),
        ("ADU", "unknown"),
        ("REPAIR EXISTING ADU", None),
        ("REMOVE ADU KITCHEN", None),
        ("DEMO SFD & ADU HOOKED TO TOWN WATER/SEWER", None),
        ("ADU REROOF", None),
        ("RESIDENTIAL CARE HOME FOR 6 ADULTS", None),
        ("IN-LAW SUITE ADDITION", None),
        ("GUEST HOUSE", None),
        ("Utility Dwelling Unit & Deck", "attached"),  # Cary's pre-2025 name for an attached/internal ADU
        ("One Story Addition UDU", "attached"),
        ("CONV. PART OF BASEMENT TO UDU", "internal_conversion"),
        ("DETACHED GARAGE W/ UDU & SCR PORCH", "detached"),
        ("ACCESSORY DWELLING COTTAGE", "detached"),
        ("CONVERT LAUNDRY ROOM INTO 2ND KITCHEN - NOT A UDU", None),
        ("KITCHENETTE IN UNF STORAGE IN PART. FIN. BASEMENT", None),
        ("Addition - In Law Suite (Bed & Bath, Laundry)", None),
        ("FINISH UTILITYDWELLING UNIT ON 2ND FLOOR", "attached"),
        ("RENOVATION AND ADDITION W/ ACC USE DWELLING", "attached"),
        ("ADDITION/REMODEL/UDU/PORCHES", "attached"),  # "remodel" is not a conversion cue
        ("ADU; SCRN PCH; REMODEL; DECKS; UNF BSMT", "internal_conversion"),
        ("", None),
    ],
)
def test_adu_rule(text, expected):
    assert cp.adu_from_text(text) == expected


def test_conforms_and_kept_rows():
    out = cp.build(raw_frame())
    assert_conforms(out, "permits")
    ids = set(out.permit_id)
    # cancelled, not issued, trade permit, not Town of Cary (Wake County, Morrisville)
    assert not ids & {"C13", "C14", "C15", "C17", "C22"}
    assert "C21" in ids  # the Chatham side of Cary
    assert (out.jurisdiction_geoid == "3710740").all()


def test_types_and_units():
    p = permits()
    assert row(p, "C1") == ("SFD", 1, "reported")
    assert row(p, "C2") == ("TH", 1, "derived")  # no Housing Units: the type's count
    assert row(p, "C3") == ("MF5", 48, "reported")
    t, n, c = row(p, "C4")  # 5+ family without a unit count
    assert t == "MF5" and pd.isna(n) and c == "unknown"
    assert row(p, "C12") == ("OTHER", 0, "derived")
    assert row(p, "C16") == ("OTHER", 0, "derived")
    assert row(p, "C10") == ("SFD", 0, "derived")  # "adults" is not an ADU
    assert row(p, "C20") == ("SFD", 1, "reported")  # a new house naming an ADU stays one house


def test_adus():
    p = permits()
    for pid, adu_type in [("C5", "detached"), ("C6", "attached"), ("C7", "internal_conversion"),
                          ("C8", "detached")]:  # fmt: skip
        assert row(p, pid) == ("ADU", 1, "inferred")
        assert p.loc[pid, "adu_type"] == adu_type and p.loc[pid, "type_confidence"] == "inferred"
    assert bool(p.loc["C7", "is_conversion"]) and bool(p.loc["C8", "is_conversion"])
    assert row(p, "C18") == ("ADU", 1, "derived") and p.loc["C18", "type_confidence"] == "high"
    assert row(p, "C9") == ("SFD", 0, "derived")  # an existing ADU repaired
    assert row(p, "C19") == ("OTHER", 0, "derived")  # Non-Residential application: never an ADU


def test_demolition_dates_and_pins():
    p = permits()
    assert bool(p.loc["C11", "is_demolition"])
    assert (p.loc["C11", "units_new"], p.loc["C11", "units_removed"]) == (0, 1)
    assert p.loc["C1", "parcel_id"] == "0764681923"  # leading zero restored
    assert p.loc["C2", "parcel_id"] == "0743543633"
    assert pd.isna(p.loc["C3", "parcel_id"])
    assert p.loc["C1", "final_date"] == pd.Timestamp("2021-10-01")
    assert p.loc["C1", "final_date_type"] == "certificate_of_occupancy"
    assert p.loc["C2", "final_date_type"] == "completion"
    assert p.loc["C1", "issue_year"] == 2021 and p.loc["C1", "application_date"] == pd.Timestamp("2020-12-01")
    assert p.loc["C1", "valuation_usd"] == 150000.0 and p.loc["C1", "floor_area_sqft"] == 1200.0


def _export(path, sep=";") -> None:
    """Write the synthetic rows as the portal's CSV export: labelled headers, extra (personal) columns."""
    df = raw_frame()
    out = pd.DataFrame({
        "Permit Number": df.permit_number, "Description": df.description, "Status Current Mapped":
        df.status_mapped, "Applied Date": df.applied, "Issue Date": df.issued, "Completed Date": df.completed,
        "CO Issued Date": df.co, "Original Address 1": "1 MAIN ST", "PIN": df.pin,
        "Jurisdiction": df.jurisdiction,
        "Total SqFt": df.sqft, "Housing Units": df.units, "Project Cost": df.cost, "Permit Class Mapped":
        df.class_mapped, "Work Class": df.work_class, "Permit Type": df.ptype, "Permit Type Mapped":
        df.ptype_mapped, "Owner Name": "A PERSON",
    })  # fmt: skip
    assert list(out.columns) == HEADER
    out.to_csv(path, sep=sep, index=False, encoding="utf-8-sig")


@pytest.mark.parametrize("sep", [";", ","])
def test_read_export_by_labels_without_personal_columns(tmp_path, sep):
    f = tmp_path / "permit-applications.csv"
    _export(f, sep)
    raw = cp.read(f)
    assert set(raw.columns) == set(cp.COLUMNS)
    assert not {cp._key(c) for c in raw.columns} & cp.PERSONAL
    pd.testing.assert_frame_equal(cp.build(raw), cp.build(raw_frame()))


def test_privacy():
    assert not {s for v in cp.COLUMNS.values() for s in v} & cp.PERSONAL
    out = cp.build(raw_frame())
    assert not out.astype(str).apply(lambda c: c.str.contains("TOWNHOME LOT")).any().any()


def test_load_reads_the_registered_export(tmp_path):
    store = DataStore(tmp_path / "data")
    with pytest.raises(FileNotFoundError, match="manifest register"):
        cp.load("NC", store)
    f = tmp_path / "permit-applications.csv"
    _export(f)
    store.register(f, source=cp.SOURCE, url=cp.LANDING_URL, license=cp.LICENSE, vintage="2026-11-10")
    out = cp.load("NC", store)
    assert len(out) == len(ROWS) - 5


def test_registered():
    assert registry.sources_for("NC")["cary_permits"].module.TABLE == "permits"
