"""Rochester monthly permit sheets → `permits`, on hand-built synthetic sheets (no real data).

Checks: header labels that change from month to month map to the same columns and personal columns are
never read; repeated rows collapse; trade permits drop; construction codes give type and units; the ADU rule
(named, not negated, not "future", not existing) and the two-family-with-ADU split into a house row and an
ADU row; the folder listing is walked recursively and keeps one sheet per month.
"""

import json

import httpx
import openpyxl
import pandas as pd
import pytest

from lotline.adapters.states.mn import rochester_permits as rp

HEADER_A = ["", "Permit Type", "Category\n", "Alteration Description", "Addition Description", "Permit ID",
            "Date of Issue", "Parcel\n", "Address\n", "Quadrant\n", "Construction Type Code",
            "Principal Building Use", "Occupancy", "Valuation\n", "Work Description", "Contractor",
            "Owner"]  # fmt: skip
# 2019-02-style labels: "Type of Permit", "Permit #", "Issue Date", "Const Type Code", and "Construction"
# (the contractor) where the occupancy usually is.
HEADER_B = ["", "Type of Permit", "Category", "Alteration Description", "Addition Description", "Permit #",
            "Issue Date", "Parcel #", "Address", "Quadrant", "Const Type Code", "Principal Bldg Use",
            "Valuation", "Work Description", "Construction", "Owner"]  # fmt: skip

ROWS_A = [
    # ptype, category, alt, add, id, date, parcel, address, quad, code, use, occ, val, desc, contractor, owner
    ("Residential Bldg", "New", None, None, "R24-0001RB", "2024-03-05", "012345", "1 A ST", "NW", "101", None,
     "IRC-1 - Single-Family Dwelling", "350000", "New single family dwelling", "BUILDER CO", "JANE DOE"),
    ("Residential Bldg", "New", None, None, "R24-0001RB", "2024-03-05", "012345", "1 A ST", "NW", "101", None,
     "IRC-1 - Single-Family Dwelling", "350000", "New single family dwelling", "BUILDER CO", "JANE DOE"),
    ("Residential Bldg", "New", None, None, "R24-0002RB", "2024-03-06", "012346", "2 A ST", "NW", "103", None,
     "IRC-2 - Two-Family Dwelling", "500000",
     "Two-family dwelling (SFD with attached ADU), finished basement",
     "BUILDER CO", "JOHN ROE"),
    ("Residential Bldg", "Accessory Structure", None, None, "R24-0003RB", "2024-03-07", "012347", "3 A ST",
     "SE", "997", None, None, "120000", "One bedroom accessory dwelling unit over a 3-car garage", "X", "Y"),
    ("Residential Bldg", "Accessory Structure", None, None, "R24-0004RB", "2024-03-08", "012348", "4 A ST",
     "SE", "997", None, None, "60000", "Three car garage with future living quarter (future ADU)", "X", "Y"),
    ("Residential Bldg", "Alteration", "Other", None, "R24-0005RB", "2024-03-09", "012349", "5 A ST", "SW",
     "434", None, None, "8000", "Repairs to existing basement ADU", "X", "Y"),
    ("Residential Trade", "Electrical", None, None, "R24-0006RE", "2024-03-10", "012347", "3 A ST", "SE",
     None, None, None, "2000", "Electrical work for a new ADU", "X", "Y"),
    ("Demolition", "Residential", None, None, "R24-0007DM", "2024-03-11", "012350", "6 A ST", "NE", "645",
     None, None, "9000", "Demolish single family house", "X", "Y"),
    ("Residential Bldg", "New", None, None, "R24-0008RB", "not a date", "012351", "7 A ST", "NE", "101", None,
     None, "1", "Bad date row", "X", "Y"),
]  # fmt: skip
ROWS_B = [
    ("Residential Bldg", "Addition", None, "Room Addition", "R19-0100RB", "2019-02-14", "054321", "8 B ST",
     "NW", "434", None, "40000", "Addition to home - attached ADU", "SOMEONE", "OWNER NAME"),
    ("Multi-Family Bldg", "New", None, None, "R19-0101MFB", "2019-02-15", "054322", "9 B ST", "NW", "105",
     "Residential", "9000000", "New 48 unit apartment building", "X", "Y"),
]  # fmt: skip


def write_sheet(path, header, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([])
    ws.append(["", "", "", "City of Rochester Monthly Detail Report"])
    ws.append([])
    ws.append([])
    ws.append(header)
    for r in rows:
        ws.append(["", *r])
    wb.save(path)


@pytest.fixture
def sheets(tmp_path):
    a, b = tmp_path / "a.xlsx", tmp_path / "b.xlsx"
    write_sheet(a, HEADER_A, ROWS_A)
    write_sheet(b, HEADER_B, ROWS_B)
    return a, b


def test_header_map_never_reads_personal_columns():
    m = rp.header_map(HEADER_B)
    assert set(m.values()) == set(rp.COLUMNS) - {"occupancy"}
    assert HEADER_B.index("Construction") not in m  # the contractor, despite its name
    assert HEADER_B.index("Owner") not in m and HEADER_B.index("Address") not in m
    m = rp.header_map(HEADER_A)
    assert set(m.values()) == set(rp.COLUMNS)
    assert all(HEADER_A[i] not in ("Contractor", "Owner", "Address\n") for i in m)


def test_read_sheet_keeps_only_listed_columns(sheets):
    for path in sheets:
        df = rp.read_sheet(path)
        assert set(df.columns) == set(rp.COLUMNS)
        assert not df.isin(["JANE DOE", "OWNER NAME", "1 A ST", "BUILDER CO"]).any().any()


@pytest.fixture
def permits(sheets):
    raw = pd.concat([rp.read_sheet(p) for p in sheets], ignore_index=True)
    return rp.build(raw).set_index("permit_id")


def test_rows_collapse_and_trade_and_bad_dates_drop(permits):
    assert "rst-R24-0006RE" not in permits.index  # trade permit
    assert "rst-R24-0008RB" not in permits.index  # no valid issue date
    assert permits.index.is_unique
    assert set(permits["jurisdiction_geoid"]) == {rp.ROCHESTER}


def test_types_and_units_from_code(permits):
    sfd = permits.loc["rst-R24-0001RB"]
    assert (sfd["building_type_std"], sfd["units_new"], sfd["units_confidence"]) == ("SFD", 1, "derived")
    assert sfd["parcel_id"] == "rst-012345"
    mf = permits.loc["rst-R19-0101MFB"]
    assert mf["building_type_std"] == "MF5" and pd.isna(mf["units_new"])
    demo = permits.loc["rst-R24-0007DM"]
    assert bool(demo["is_demolition"]) and demo["units_removed"] == 1 and demo["units_new"] == 0


def test_adu_rule(permits):
    adu = permits[permits["building_type_std"] == "ADU"]
    assert set(adu.index) == {"rst-R24-0002RB-ADU", "rst-R24-0003RB", "rst-R19-0100RB"}
    assert (adu["units_new"] == 1).all() and (adu["type_confidence"] == "inferred").all()
    # the two-family-with-ADU permit: the house keeps its row, the ADU gets its own
    house = permits.loc["rst-R24-0002RB"]
    assert (house["building_type_std"], house["units_new"]) == ("SFD", 1)
    assert permits.loc["rst-R24-0003RB", "adu_type"] == "detached"  # "garage"
    assert permits.loc["rst-R19-0100RB", "adu_type"] == "attached"
    # "future ADU" and work on an existing ADU are not new ADUs
    assert permits.loc["rst-R24-0004RB", "building_type_std"] == "OTHER"
    assert permits.loc["rst-R24-0005RB", "building_type_std"] == "OTHER"


@pytest.mark.parametrize(
    "text, kind",
    [
        ("Addition to home - attached ADU", "attached"),
        ("Upper level finish with kitchen and bathroom for ADU in detached garage", "detached"),
        ("Basement finish incl. mother-in-law suite [non-rental]", None),
        ("Garage with future ADU above", None),
        ("Garage only. NOT AN ADU", None),
        ("Remodel existing basement ADU", None),
        ("Legalize existing basement ADU", "internal_conversion"),
    ],
)
def test_adu_named(text, kind):
    assert rp.adu_named(text) == kind


def test_sheet_entries_walks_folders_and_keeps_one_per_month():
    tree = {
        rp.ROOT_FOLDER: [
            {"entryId": 10, "type": 0, "name": "*Archive"},
            {"entryId": 20, "type": 0, "name": "2026"},
        ],
        10: [{"entryId": 11, "type": 0, "name": "2024"}],
        11: [
            {"entryId": 101, "type": -2, "name": "2024.01 Detail Report Spreadsheet", "extension": "xlsx"},
            {"entryId": 102, "type": -2, "name": "2024.01 Detail Report", "extension": "pdf"},
            {"entryId": 103, "type": -2, "name": "2024.02 Detail Report Spreadsheet", "extension": "XLSX"},
        ],
        20: [
            {"entryId": 201, "type": -2, "name": "2026.01  Detail Report Spreadsheet", "extension": "xlsx"},
            {"entryId": 202, "type": -2, "name": "2016.05 Detail Report Spreadsheet", "extension": "xls"},
        ],
    }  # fmt: skip

    def handler(request: httpx.Request) -> httpx.Response:
        folder = json.loads(request.content)["folderId"]
        return httpx.Response(200, json={"data": {"results": tree[folder]}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        entries = rp.sheet_entries(http)
    assert [(e["month"], e["docid"], e["extension"]) for e in entries] == [
        ("2016.05", 202, "xls"),
        ("2024.01", 101, "xlsx"),
        ("2024.02", 103, "xlsx"),
        ("2026.01", 201, "xlsx"),
    ]
