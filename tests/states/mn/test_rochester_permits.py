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
        assert set(df.columns) == set(rp.COLUMNS) | {"report_month"}
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


# The old permit system's extract (2005-09 to 2007-10): system field names, one row per permit. Positions
# 9-13, 15, 17 and 18 hold the street address, subdivision, owner and contractor.
LEGACY_HEAD = ["BPWTYP", "BPWTCD", "BPWVAL", "BPWIYY", "BPWIMM", "BPWIDD", "BPWYER", "BPWCNB", "BPWBLD",
               "LMWSNO", "LMWSTQ", "LMWSNM", "LMWDIR", "LMWAPT", "BPWATD", "LMWSBN", "BPWUNT", "BPWOWN",
               "BPWCNT"]  # fmt: skip
LEGACY_ROWS = [
    ["R101", "RBPR", "150000", "5", "9", "15", "5", "4450", None, "5777", None, "DOGWOOD CT", "NW", None,
     "SINGLE FAMILY DWELLING", "CRIMSON RIDGE", "1", "JANE DOE", "BUILDER CO"],
    ["R100", "RBPR", "120000", "6", "2", "3", "6", "0538", None, "12", None, "OAK ST", "NE", None,
     "SINGLE FAMILY DWELLING (ATTACHED DWELLINGS)", "SUB", "1", "JOHN ROE", "X"],
    ["R105", "RBPC", "9000000", "6", "5", "1", "6", "2307", None, "1", None, "ELM AVE", "SE", None,
     "MULTI-FAMILY BUILDING (5 OR MORE UNITS)", "SUB", "48", "OWNER LLC", "X"],
    ["R645", "RXDR", "5000", "7", "1", "9", "7", "0100", None, "3", None, "PINE ST", "SW", None,
     "DEMOLITION (SINGLE FAMILY DWELLING)", "SUB", "0", "X", "X"],
    ["R501", "RXSG", "2000", "7", "1", "10", "7", "0101", None, "4", None, "MAIN ST", "SW", None,
     "SIGN (BUSINESS)", "SUB", "0", "X", "X"],
]  # fmt: skip


@pytest.fixture
def legacy_grid() -> pd.DataFrame:
    return pd.DataFrame([LEGACY_HEAD, *LEGACY_ROWS], dtype="object")


def test_read_legacy_reads_only_listed_fields(legacy_grid):
    df = rp.read_legacy(legacy_grid)
    assert set(df.columns) == set(rp.COLUMNS) | {"units_reported"}
    assert not df.isin(["JANE DOE", "BUILDER CO", "DOGWOOD CT", "5777", "CRIMSON RIDGE"]).any().any()
    assert df["permit_id"].tolist() == ["L05-4450", "L06-0538", "L06-2307", "L07-0100", "L07-0101"]
    assert df["issue_date"].tolist()[:2] == ["2005-09-15", "2006-02-03"]
    assert df["code"].tolist() == ["101", "102", "105", "645", "501"]  # R100 (attached) read as 102


def test_legacy_rows_build(legacy_grid):
    out = rp.build(rp.read_legacy(legacy_grid)).set_index("permit_id")
    assert "rst-L07-0101" not in out.index  # sign permit: dropped
    assert out.loc["rst-L05-4450", "building_type_std"] == "SFD"
    assert out.loc["rst-L06-0538", "building_type_std"] == "TH"
    mf = out.loc["rst-L06-2307"]
    assert (mf["building_type_std"], mf["units_new"], mf["units_confidence"]) == ("MF5", 48, "reported")
    assert bool(out.loc["rst-L07-0100", "is_demolition"])
    assert out["parcel_id"].isna().all()
    assert not (out["building_type_std"] == "ADU").any()


def test_xls_sheets_are_read_with_xlrd_and_dispatch_legacy(monkeypatch, tmp_path, legacy_grid):
    seen = {}

    def fake_read_excel(path, **kw):
        seen["engine"] = kw["engine"]
        return legacy_grid

    monkeypatch.setattr(rp.pd, "read_excel", fake_read_excel)
    folder = tmp_path / "2006.02"
    folder.mkdir()
    df = rp.read_sheet(folder / "detail_report.xls")
    assert seen["engine"] == "xlrd"
    assert (df["report_month"] == "2006.02").all() and len(df) == 5


def test_blank_issue_dates_take_the_report_month(sheets):
    raw = rp.read_sheet(sheets[0]).assign(report_month="2024.03")
    raw.loc[raw["permit_id"] == "R24-0003RB", "issue_date"] = pd.NA
    out = rp.build(raw).set_index("permit_id")
    row = out.loc["rst-R24-0003RB"]
    assert row["issue_date"] == pd.Timestamp("2024-03-01") and row["date_precision"] == "month"
    assert out.loc["rst-R24-0001RB", "date_precision"] == "day"


def test_mixed_date_formats_across_sheets(sheets, legacy_grid):
    # legacy rows ("2005-09-15") stacked with later sheets ("2024-03-05 00:00:00") keep their day dates
    raw = pd.concat([rp.read_legacy(legacy_grid), rp.read_sheet(sheets[0])], ignore_index=True)
    out = rp.build(raw)
    assert (out["date_precision"] == "day").all()
