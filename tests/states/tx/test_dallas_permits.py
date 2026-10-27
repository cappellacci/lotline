"""Dallas permits adapter on synthetic rows (no network, no real data).

Checks the module docstring: kept statuses, one row per permit number, building type and units from the
land-use crosswalk and UNITS (old 10/20 house codes read as one house), multifamily from UNITS of 2 or more,
ADUs from the description parser, additions, dates and zoning, and that personal fields are never requested
or kept.
"""

import pandas as pd

from lotline import registry
from lotline.adapters.states.tx import dallas_permits as dp
from lotline.io import DataStore
from lotline.schemas import assert_conforms

N, A = dp.NEW, dp.ADDITION
SF, TF, MF = " SINGLE FAMILY DWELLING", " TWO FAMILY DWELLING", " MULTI-FAMILY DWELLING"


def ms(day: str | None) -> int | None:
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000) if isinstance(day, str) else None


# PERMIT_No, ACTIVITY, LAND_USE, Type, UNITS, ISSUE_DATE, status, description
ROWS = [
    (1001, N, SF, "Single Family", 1, "2022-03-01", "Complete", "1111-CONSTRUCT NEW SFD 12 ELM ST"),
    (1002, N, SF, "Single Family", 0, "2022-04-01", "Issued", "new house"),
    (1003, N, SF, "Single Family", 20, "1979-05-05", "Complete", "GR CONSTR ONE FAM DWELL"),
    (1004, N, TF, "Single Family", 2, "2023-05-05", "Complete", "DUPLEX"),
    (1005, N, TF, "Single Family", 0, "2023-05-06", "Expired", "duplex"),
    (1006, N, MF, "Multi Family", 471, "2023-07-01", "Complete", "AREA 1A 1113-NEW CONSTRUCTION"),
    (1007, N, MF, "Multi Family", 4, "2021-02-02", "Complete", "fourplex"),
    (1008, N, MF, "Multi Family", 0, "2021-03-03", "Complete", "building 3"),
    (1009, N, SF, "Single Family", 1, "2020-06-06", "Complete", "New accessory dwelling unit at 9 OAK"),
    (1010, A, SF, "Single Family", 0, "2019-07-07", "Complete", "add bedroom"),
    (1011, A, SF, "Single Family", 0, "2019-08-08", "Complete", "convert garage to accessory dwelling unit"),
    (1012, N, SF, "Single Family", 1, "2018-09-09", "Cancelled", "SFD"),
    (1013, N, SF, "Single Family", 1, None, "Issued", "SFD"),
    (1014, N, SF, "Single Family", 1, "2018-10-10", "Other", "SFD"),
    (1015, N, " DUPLEX/TOWNHOUSE DWELLING", "Commercial", 0, "2017-01-01", "Complete",
     "NEW 4-UNIT APARTMENT BUILDING"),
    (1001, N, SF, "Single Family", 1, "2022-03-01", "Complete", "1111-CONSTRUCT NEW SFD 12 ELM ST"),
]  # fmt: skip


def raw_frame() -> pd.DataFrame:
    df = pd.DataFrame(
        ROWS,
        columns=["PERMIT_No", "ACTIVITY", "LAND_USE", "Type", "UNITS", "ISSUE_DATE", "Grouped_Status",
                 "WORK_DESCRIPTION"],
    )  # fmt: skip
    df["PERMIT_No"] = df["PERMIT_No"].astype(float)  # the layer stores permit numbers as doubles
    df["ISSUE_DATE"] = df["ISSUE_DATE"].map(ms)
    df["CREATED_DATE"] = df["ISSUE_DATE"].map(lambda v: v - 30 * 86_400_000 if v else None)
    df["OBJECTID"] = range(len(df))
    df["PERMIT_TYPE"] = dp.BUILDING
    df["VALUE"] = 250000.0
    df["AREA"] = 1800.0
    df["BASE_ZONING"] = "R-7.5(A)"
    df["UNITS"] = df["UNITS"].astype(float)
    return df


def permits() -> pd.DataFrame:
    return dp.build(raw_frame()).set_index("permit_id")


def row(p: pd.DataFrame, pid: str) -> tuple:
    r = p.loc[pid]
    return (r.building_type_std, r.units_new, r.units_confidence)


def test_conforms_statuses_and_one_row_per_permit():
    out = dp.build(raw_frame())
    assert_conforms(out, "permits")
    ids = list(out.permit_id)
    assert ids.count("1001") == 1
    assert {"1012", "1013", "1014"}.isdisjoint(ids)  # cancelled, never issued, application only
    assert {"1002", "1005"} <= set(ids)  # issued, and expired
    assert (out.jurisdiction_geoid == "4819000").all()


def test_dwellings_use_units_when_it_fits_else_the_type():
    p = permits()
    assert row(p, "1001") == ("SFD", 1, "reported")
    assert row(p, "1002") == ("SFD", 1, "derived")
    assert row(p, "1003") == ("SFD", 1, "derived")  # old 1970s code of 20 units on a house
    assert row(p, "1004") == ("U2", 2, "reported")
    assert row(p, "1005") == ("U2", 2, "derived")


def test_multifamily_from_units():
    p = permits()
    assert row(p, "1006") == ("MF5", 471, "reported")  # as reported; D-008 grouping is downstream (#221)
    assert row(p, "1007") == ("U3_4", 4, "reported")
    t, n, c = row(p, "1008")
    assert t == "UNKNOWN" and pd.isna(n) and c == "unknown"
    assert row(p, "1015") == ("U3_4", 4, "inferred")  # land use not in the crosswalk: the parser


def test_adus_and_additions():
    p = permits()
    assert row(p, "1009") == ("ADU", 1, "inferred")
    assert row(p, "1010") == ("SFD", 0, "derived")
    assert row(p, "1011") == ("ADU", 1, "inferred")
    assert bool(p.loc["1011", "is_conversion"])


def test_dates_and_zoning():
    p = permits()
    assert p.loc["1001", "issue_date"] == pd.Timestamp("2022-03-01")
    assert p.loc["1001", "application_date"] == pd.Timestamp("2022-01-30")
    assert p.loc["1001", "issue_year"] == 2022 and p.loc["1001", "date_precision"] == "day"
    assert p.loc["1001", "zoning_raw"] == "R-7.5(A)"


def test_privacy():
    assert not set(dp.OUT_FIELDS) & dp.PERSONAL
    out = dp.build(raw_frame())
    assert "WORK_DESCRIPTION" not in out.columns
    assert not out.astype(str).apply(lambda c: c.str.contains("ELM ST|9 OAK")).any().any()


def test_load_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(dp, "download", lambda store, refresh=False: raw_frame())
    out = dp.load("TX", DataStore(tmp_path))
    assert len(out) == 12  # 16 rows: one repeat, three not issued


def test_registered():
    assert registry.sources_for("TX")["dallas_permits"].module.TABLE == "permits"
