"""Ohio statewide parcels adapter on a synthetic fixture (no network, no real data).

Checks the methodology in the module docstring: DTE land-use crosswalk (incl. the unplatted-acreage codes),
lot size from LandArea with the polygon-area fallback, county vintage dates, parcel IDs and de-duplication,
privacy, and that load() stays off until parcels can be placed in a city or township.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.oh import oh_parcels as op
from lotline.schemas import LAND_USES, assert_conforms


def _ms(day: str) -> int:
    return int(pd.Timestamp(day).value // 1_000_000)


# County, LocalParcelID, StateLUC, LandArea (acres), Shape__Area (sq ft), CurrentTo
ROWS = [
    ("Franklin", "010-000001-00", "510: Res-Single Family", 0.0, 5000.0, "2023-09-26"),
    ("Franklin", "010-000002-00", "511: Res-Custom Code", None, 20000.0, "2023-09-26"),
    ("Franklin", "010-000003-00", "553: Res-Custom Code", 0.0, 1200.0, "2023-09-26"),
    ("Franklin", "010-000004-00", None, None, 900.0, None),
    ("Franklin", None, None, None, 300000.0, None),  # polygon with no auditor record
    ("Franklin", "010-000005-00", "520: Res-Two Family", 0.0, 4000.0, "2023-09-26"),
    ("Franklin", "010-000005-00", "520: Res-Two Family", 0.0, 3500.0, "2023-09-26"),  # stacked duplicate
    ("Hamilton", "0010001000100", "510: Res-Single Family", 0.25, 11000.0, "2023-08-02"),
    ("Hamilton", "0010001000200", "401: Com-Apartment- 4 to 19", 0.5, 21000.0, "2023-08-02"),
    ("Hamilton", "0010001000300", "999", 0.1, 4000.0, "2023-08-02"),
]


@pytest.fixture
def raw() -> pd.DataFrame:
    df = pd.DataFrame(ROWS, columns=["County", "LocalParcelID", "StateLUC", "LandArea", "Shape__Area", "cur"])
    df["CurrentTo"] = [_ms(d) if isinstance(d, str) else None for d in df.pop("cur")]
    df["OBJECTID"] = range(1, len(df) + 1)
    df["StateParcelID"] = None
    return df


@pytest.fixture
def parcels(raw) -> pd.DataFrame:
    return op.build(raw).set_index("parcel_id")


def test_ids_counties_and_dedup(parcels):
    assert len(parcels) == 8  # no-ID polygon dropped; stacked duplicate kept once
    assert parcels.loc["39049010-000005-00", "lot_sqft"] == 4000.0  # the larger polygon is kept
    assert set(parcels.county_geoid) == {"39049", "39061"}
    assert parcels.jurisdiction_geoid.isna().all()  # assigned later, from the centroids


def test_land_use_crosswalk(parcels):
    lu = parcels["land_use_std"]
    assert lu["39049010-000001-00"] == "SF_DETACHED"
    assert lu["39049010-000002-00"] == "SF_DETACHED"  # 511: single-family on an unplatted tract
    assert lu["39049010-000003-00"] == "UNKNOWN"  # county custom code: not guessed
    assert lu["39049010-000004-00"] == "UNKNOWN"  # blank class
    assert lu["39049010-000005-00"] == "DUPLEX"
    assert lu["390610010001000200"] == "MULTIFAMILY_5P"
    assert lu["390610010001000300"] == "UNKNOWN"


def test_lot_size_prefers_land_area_then_polygon(parcels):
    assert parcels.loc["390610010001000100", "lot_sqft"] == pytest.approx(0.25 * 43_560)
    assert parcels.loc["39049010-000001-00", "lot_sqft"] == 5000.0  # LandArea 0 → polygon area
    assert parcels.loc["39049010-000002-00", "lot_sqft"] == 20000.0  # LandArea missing → polygon area


def test_vintage_is_the_county_export_date(parcels):
    fr = parcels[parcels.county_geoid == "39049"]
    assert (fr.vintage_date == pd.Timestamp("2023-09-26")).all()  # incl. the row without CurrentTo
    assert (parcels[parcels.county_geoid == "39061"].vintage == 2023).all()


def test_crosswalks_are_complete_and_valid():
    xwalk = op.luc_crosswalk()
    assert set(xwalk.values()) <= set(LAND_USES)
    assert xwalk["510"] == "SF_DETACHED" and xwalk["500"] == "VACANT_RESIDENTIAL"
    assert all(len(code) == 3 and code.isdigit() for code in xwalk)
    fips = op.county_fips()
    assert len(fips) == 88 and fips["Franklin"] == "39049" and fips["Hamilton"] == "39061"


def test_unknown_county_fails_loudly(raw):
    raw.loc[0, "County"] = "Atlantis"
    with pytest.raises(ValueError, match="Atlantis"):
        op.build(raw)


def test_personal_fields_never_requested():
    assert not op.PERSONAL & set(op.OUT_FIELDS)


def test_resolve_jurisdictions_uses_only_known_geoids():
    county = pd.Series(["39049"] * 5)
    found = pd.Series(["3918000", "3904910000", "3999999", "3904999999", None])
    cousub = pd.Series(["3904918000", "3904910000", "3904920000", "3904999999", None])
    known = {"3918000", "3904910000", "3904920000", "39049"}
    geoid, how = op.resolve_jurisdictions(county, found, cousub, known)
    assert geoid.tolist() == ["3918000", "3904910000", "3904920000", "39049", "39049"]
    assert how.tolist() == ["place", "township", "township_of_place", "county_fallback", "county_fallback"]


def test_load_assigns_jurisdictions_and_applies_snapshot_holdout(raw, monkeypatch):
    raw["lon"], raw["lat"] = -83.0, 40.0
    monkeypatch.setattr(op, "download", lambda store, refresh=False: raw)

    def no_rows(store, layer, refresh=False):
        cols = [layer.parcel_field, layer.luc_field, layer.year_built_field, layer.exempt_luc_field]
        return pd.DataFrame(columns=[c for c in cols if c])

    monkeypatch.setattr(op, "download_county", no_rows)
    monkeypatch.setattr(op, "apply_montgomery_cama", lambda df, store: (df, {}))
    monkeypatch.setattr(op, "apply_warren", lambda df, store: df)
    monkeypatch.setattr(
        op,
        "download_franklin_roll",
        lambda store, date, refresh=False: pd.DataFrame(columns=["PARCEL ID", "LUC"]),
    )
    monkeypatch.setattr(
        op,
        "assign_jurisdictions",
        lambda df, state, store: (df.assign(jurisdiction_geoid=df["county_geoid"]), None),
    )
    calls = []
    real = op.holdout.apply

    def spy(df, state, **kw):
        calls.append(kw)
        return real(df, state, **kw)

    monkeypatch.setattr(op.holdout, "apply", spy)
    out = op.load("OH", store=None)
    assert "oh_parcels" in registry.sources_for("OH")
    assert calls[0]["snapshot"] is True and calls[0]["geoid_col"] == "jurisdiction_geoid"
    assert len(out) == 8 and out["lon"].eq(-83.0).all()
    assert_conforms(out, "parcels")


def test_oid_chunks_cover_the_range_half_open():
    assert op.chunks(1, 250_000, size=100_000) == [(0, 100_000), (100_000, 200_000), (200_000, 300_000)]
    assert op.chunks(100_000, 100_000, size=100_000) == [(100_000, 200_000)]


def test_download_queries_each_county_by_oid_range(raw, monkeypatch):
    seen = []

    def fake(url, **kw):
        seen.append(kw["where"])
        county = kw["where"].split("'")[1]
        return raw[raw.County == county] if "OBJECTID>=0 " in kw["where"] else raw.iloc[0:0]

    monkeypatch.setattr(op, "oid_range", lambda store, refresh=False: (1, 150_000))
    monkeypatch.setattr(op, "download_layer", fake)
    out = op.download(store=None, counties=["Hamilton"])
    assert seen == [
        "County='Hamilton' AND OBJECTID>=0 AND OBJECTID<100000",
        "County='Hamilton' AND OBJECTID>=100000 AND OBJECTID<200000",
    ]
    assert len(out) == 3


def test_county_without_export_date_takes_the_snapshot_date(raw):
    raw.loc[raw.County == "Hamilton", "CurrentTo"] = None
    out = op.build(raw, snapshot_date="2026-10-19").set_index("parcel_id")
    ham = out[out.county_geoid == "39061"]
    assert (ham.vintage_date == pd.Timestamp("2026-10-19")).all() and (ham.vintage == 2026).all()
    assert (out[out.county_geoid == "39049"].vintage == 2023).all()


SUMMIT = op.CountyLayer(
    name="summit",
    url="https://example.test/0",
    license="test",
    as_of="2025-03-25",
    parcel_field="PARCELID",
    luc_field="USECD",
    year_built_field="RESYRBLT",
)


def test_county_attributes_dedupe_and_clean_years():
    raw = pd.DataFrame(
        {
            "PARCELID": ["2809199", "2809199", "0106462", "0100001", None, "0100002"],
            "USECD": ["510", "510", "640", "520", "510", None],
            "RESYRBLT": [1986, 1986, None, 0, 1950, 1650],
        }
    )
    a = op.county_attributes(raw, "39153", SUMMIT).set_index("parcel_id")
    assert list(a.index) == ["391532809199", "391530106462", "391530100001", "391530100002"]  # pairs once
    assert a.loc["391532809199", "year_built"] == 1986
    assert pd.isna(a.loc["391530100001", "year_built"])  # 0 is unknown, not year 0
    assert pd.isna(a.loc["391530100002", "year_built"])  # before 1700: a data error
    assert pd.isna(a.loc["391530100002", "luc"])


def test_apply_county_attributes_fills_only_unknown_land_use():
    parcels = pd.DataFrame(
        {
            "parcel_id": ["391532809199", "391530100001", "391530199999", "39049010-000001-00"],
            "land_use_std": ["UNKNOWN", "SF_DETACHED", "UNKNOWN", "SF_DETACHED"],
            "land_use_raw": [None, "510: Res-Single Family", None, "510: Res-Single Family"],
        }
    )
    attrs = pd.DataFrame(
        {
            "parcel_id": ["391532809199", "391530100001", "391530199999"],
            "luc": ["510", "520", "553"],  # 553: a county custom code, not in the crosswalk
            "year_built": pd.array([1986, 1920, pd.NA], dtype="Int64"),
        }
    )
    out = op.apply_county_attributes(parcels, attrs, "summit").set_index("parcel_id")
    assert out.loc["391532809199", "land_use_std"] == "SF_DETACHED"
    assert out.loc["391532809199", "land_use_raw"] == "510 (summit county layer)"
    assert out.loc["391530100001", "land_use_std"] == "SF_DETACHED"  # a known statewide code is kept
    assert out.loc["391530199999", "land_use_std"] == "UNKNOWN"  # unmapped county code stays unknown
    assert out.loc["391530100001", "year_built"] == 1920 and out.loc["391532809199", "year_built"] == 1986
    assert pd.isna(out.loc["39049010-000001-00", "year_built"])  # other counties untouched


def test_four_digit_county_codes_read_as_dte_classes():
    cuyahoga = op.COUNTY_LAYERS["39035"]
    raw = pd.DataFrame(
        {
            "parcel_id": ["00101003", "00101004", "00101005"],
            "tax_luc": ["5100", None, None],
            "ext_luc": [None, "6411", None],  # exempt parcel: its use is in the exempt code
            "min_age": [1962, None, None],
        }
    )
    a = op.county_attributes(raw, "39035", cuyahoga)
    assert a["luc"].tolist()[:2] == ["510", "641"] and pd.isna(a["luc"].iloc[2])
    assert op.luc_crosswalk()["641"] == "INSTITUTIONAL"
    assert a["parcel_id"].iloc[0] == "3903500101003" and a["year_built"].iloc[0] == 1962


def test_county_layers_are_attribute_only():
    for geoid, layer in op.COUNTY_LAYERS.items():
        assert len(geoid) == 5 and geoid.startswith("39")
        assert layer.parcel_field and (layer.luc_field or layer.year_built_field)  # something to fill


def test_one_vintage_per_jurisdiction():
    df = pd.DataFrame(
        {
            "jurisdiction_geoid": ["3978050", "3978050", "3901000"],
            "vintage_date": pd.to_datetime(["2023-08-01", "2026-10-19", "2026-10-19"]),
            "vintage": pd.array([2023, 2026, 2026], dtype="Int64"),
        }
    )
    out = op.one_vintage_per_jurisdiction(df)
    assert out["vintage"].tolist() == [2026, 2026, 2026]  # Twinsburg's Cuyahoga parcel joins the 2026 roll
    assert (out["vintage_date"] == pd.Timestamp("2026-10-19")).all()


def test_dwelling_cards_keep_the_earliest_year_and_map_parcel_ids():
    franklin = op.CountyLayer(
        name="franklin",
        url="https://example.test/Dwelling.xlsx",
        license="test",
        as_of="test",
        parcel_field="PARCEL ID",
        year_built_field="YRBLT",
        table="Sheet1",
        parcel_regex=r"^(\d{3}-\d{6})",
    )
    raw = pd.DataFrame(
        {
            "PARCEL ID": ["010-000002-00", "010-000002-00", "010-000003-00", "bad"],
            "YRBLT": [1925, 2021, 0, 1950],  # a house (1925) and a carriage house (2021) on one parcel
        }
    )
    a = op.county_attributes(raw, "39049", franklin).set_index("parcel_id")
    assert list(a.index) == ["39049010-000002", "39049010-000003"]  # suffix dropped; unparseable ID dropped
    assert a.loc["39049010-000002", "year_built"] == 1925
    assert pd.isna(a.loc["39049010-000003", "year_built"]) and a["luc"].isna().all()  # year built only


def test_read_county_file_reads_only_named_columns_from_a_workbook(tmp_path):
    path = tmp_path / "Dwelling.xlsx"
    pd.DataFrame({"PARCEL ID": ["010-000002-00"], "YRBLT": [1925], "OWNER": ["not read"]}).to_excel(
        path, index=False
    )
    layer = op.CountyLayer(
        name="t",
        url="https://example.test/Dwelling.xlsx",
        license="test",
        as_of="test",
        parcel_field="PARCEL ID",
        year_built_field="YRBLT",
        table=0,
    )
    df = op.read_county_file(path, layer, ["PARCEL ID", "YRBLT"])
    assert list(df.columns) == ["PARCEL ID", "YRBLT"] and df["PARCEL ID"].iloc[0] == "010-000002-00"


def _placed_roll() -> pd.DataFrame:
    """A placed statewide roll: Franklin 2023 (A wholly inside; B 1 house of 2 in Franklin) plus Delaware."""
    rows = [
        # parcel_id, county, jurisdiction, land use, lot, year built
        ("39049010-000001", "39049", "A", "SF_DETACHED", 5000.0, 1950),
        ("39049010-000002", "39049", "A", "DUPLEX", 4000.0, 1920),
        ("39049010-000003", "39049", "A", "SF_DETACHED", 6000.0, 2001),
        ("39049020-000001", "39049", "B", "SF_DETACHED", 7000.0, 1990),
        ("39049030-000001", "39049", "A", "COMMERCIAL", 9000.0, pd.NA),
        ("39049030-000002", "39049", "C", "COMMERCIAL", 9000.0, pd.NA),
        ("39041000-000001", "39041", "B", "SF_DETACHED", 8000.0, 2005),
    ]
    df = pd.DataFrame(
        rows,
        columns=["parcel_id", "county_geoid", "jurisdiction_geoid", "land_use_std", "lot_sqft", "year_built"],
    )
    df["year_built"] = df["year_built"].astype("Int64")
    df["state"], df["vintage"], df["vintage_date"] = "OH", 2023, pd.Timestamp("2023-09-26")
    df["vintage"] = df["vintage"].astype("Int64")
    df["land_use_raw"], df["lon"], df["lat"], df["source"] = "x", -83.0, 40.0, "oh_parcels"
    return df


def _archive(*rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["PARCEL ID", "LUC"])


def test_franklin_roll_places_by_roll_then_dominant_district():
    current = _placed_roll().query("county_geoid == '39049'")
    raw = _archive(
        ("010-000001-00", "510"),
        ("010-000001-01", "510"),  # second card of the same parcel: one row
        ("010-000002-00", "510"),  # a duplex in 2023, a house in 2018: the archive's own code counts
        ("010-999999-00", "500"),  # not in the roll; district 010 is all A (3 of 3) → A, lot unknown
        ("030-999999-00", "510"),  # district 030 is half A, half C → dropped
        ("BAD", "510"),
    )
    out = op.franklin_roll(raw, "2018-12-17", current).set_index("parcel_id")
    assert list(out.index) == ["39049010-000001", "39049010-000002", "39049010-999999"]
    assert (out["vintage"] == 2018).all() and (out["vintage_date"] == pd.Timestamp("2018-12-17")).all()
    assert out["jurisdiction_geoid"].tolist() == ["A", "A", "A"]
    assert out["land_use_std"].tolist() == ["SF_DETACHED", "SF_DETACHED", "VACANT_RESIDENTIAL"]
    assert (
        out.loc["39049010-000001", "lot_sqft"] == 5000.0 and out.loc["39049010-000001", "year_built"] == 1950
    )
    assert pd.isna(out.loc["39049010-999999", "lot_sqft"])
    assert out.loc["39049010-000002", "land_use_raw"] == "510 (Franklin Auditor 2018-12-17)"

    # year built for a parcel missing from the roll comes from the dwelling file; the roll's own wins
    years = pd.Series({"39049010-999999": 2017, "39049010-000001": 1800}, dtype="Int64")
    filled = op.franklin_roll(raw, "2018-12-17", current, year_built=years).set_index("parcel_id")
    assert filled.loc["39049010-999999", "year_built"] == 2017
    assert filled.loc["39049010-000001", "year_built"] == 1950


def test_franklin_yearly_rolls_only_for_places_wholly_in_the_county():
    df = _placed_roll()
    raw = _archive(("010-000001-00", "510"), ("020-000001-00", "510"), ("010-000003-00", "500"))
    out = op.franklin_yearly_rolls(df, {"2019-12-18": raw, "2023-12-26": raw})
    added = out[out["vintage"] == 2019]
    # A has 2 of 2 houses in Franklin → yearly rolls; B has 1 of 2 (Delaware) → none
    assert set(added["jurisdiction_geoid"]) == {"A"} and len(added) == 2
    # the statewide roll's own year (2023) is not read twice; the original rows are untouched
    assert (out["vintage"] == 2023).sum() == len(df)
    assert_conforms(out, "parcels")
    assert op.franklin_yearly_rolls(df[df["county_geoid"] != "39049"], {"2019-12-18": raw}).equals(
        df[df["county_geoid"] != "39049"]
    )


def test_franklin_share_counts_houses_only():
    share = op.franklin_share(_placed_roll())
    assert share.to_dict() == {"A": 1.0, "B": 0.5}


def _fixed_line(fields: dict[int, str], width: int) -> bytes:
    """A fixed-width record: {1-based start: value}, space-padded to `width`, CRLF-terminated."""
    buf = bytearray(b" " * width)
    for start, value in fields.items():
        buf[start - 1 : start - 1 + len(value)] = value.encode()
    return bytes(buf) + b"\r\n"


def _cama_zip(path, pardat_rows, dwell_rows, folder="Cama_Files_20260930\\"):
    import zipfile

    pardat = b"".join(_fixed_line({1: pid, 239: luc}, 608) for pid, luc in pardat_rows)
    # a DWELL record spills its maintenance date onto two short lines, as in the real export
    dwell = b"".join(_fixed_line({1: pid, 59: yr}, 643) + b"02-JAN-25\r\n\r\n" for pid, yr in dwell_rows)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(folder + "PARDAT.DAT", pardat)  # 2026: Windows-style folder; 2011-2025: at the root
        z.writestr(folder + "DWELL.DAT", dwell)
    return path


def test_read_cama_reads_only_named_fields(tmp_path):
    path = _cama_zip(tmp_path / "c.zip", [("A01 00101 0001", "510"), ("R72 01209 0070", "613")], [])
    pardat = op.read_cama(path, "PARDAT.DAT", op.CAMA_PARDAT)
    assert pardat.to_dict("list") == {"parid": ["A01 00101 0001", "R72 01209 0070"], "luc": ["510", "613"]}
    old = _cama_zip(tmp_path / "o.zip", [("A01 00101 0001", "510")], [], folder="")
    assert op.read_cama(old, "PARDAT.DAT", op.CAMA_PARDAT)["luc"].tolist() == ["510"]
    # no owner, mailing or address field is in either layout
    assert {"parid", "luc"} == set(op.CAMA_PARDAT) and {"parid", "yrblt"} == set(op.CAMA_DWELL)


def test_montgomery_attributes_keep_the_earliest_dwelling_and_valid_years(tmp_path):
    path = _cama_zip(
        tmp_path / "c.zip",
        [("A01 00101 0001", "510"), ("A01 00101 0002", "500"), ("A01 00101 0003", "520")],
        [("A01 00101 0001", "1925"), ("A01 00101 0001", "1999"), ("A01 00101 0003", "0")],
    )
    a = op.montgomery_attributes(
        op.read_cama(path, "PARDAT.DAT", op.CAMA_PARDAT), op.read_cama(path, "DWELL.DAT", op.CAMA_DWELL)
    ).set_index("parcel_id")
    assert list(a.index) == ["39113A01 00101 0001", "39113A01 00101 0002", "39113A01 00101 0003"]
    assert a.loc["39113A01 00101 0001", "year_built"] == 1925  # two cards: the earliest
    assert pd.isna(a.loc["39113A01 00101 0002", "year_built"])  # vacant: no dwelling
    assert pd.isna(a.loc["39113A01 00101 0003", "year_built"])  # 0 is not a year
    assert a["luc"].tolist() == ["510", "500", "520"]


def test_drop_never_in_cama_only_touches_montgomery():
    df = pd.DataFrame(
        {
            "parcel_id": ["39113A01 00101 0001", "39113R72 01209 9999", "39049010-000001"],
            "county_geoid": ["39113", "39113", "39049"],
        }
    )
    out = op.drop_never_in_cama(df, {"39113A01 00101 0001"})
    # the Montgomery parcel in no CAMA year goes; Franklin is untouched
    assert out["parcel_id"].tolist() == ["39113A01 00101 0001", "39049010-000001"]


def test_registered_cama_reads_snapshot_dates_from_the_manifest(tmp_path):
    class Entry:
        def __init__(self, path):
            self.path = path

    class Store:
        root = tmp_path

        def registered(self, source):
            assert source == op.SOURCE
            return [
                Entry("raw/oh_parcels/montgomery_cama_20260930/Cama_Files_20260930.zip"),
                Entry("raw/oh_parcels/montgomery_cama_20110201/Cama_Files_20110201.zip"),
                Entry("raw/oh_parcels/2026-10-19/county_franklin/Dwelling.xlsx"),
            ]

    files = op.registered_cama(Store())
    assert list(files) == ["2011-02-01", "2026-09-30"]
    assert files["2026-09-30"] == tmp_path / "raw/oh_parcels/montgomery_cama_20260930/Cama_Files_20260930.zip"


def test_montgomery_yearly_rolls_place_by_roll_then_district():
    roll = pd.DataFrame(
        {
            "state": "OH",
            "parcel_id": ["39113R72 00001 0001", "39113R72 00001 0002", "39113A01 00001 0001"],
            "vintage": pd.Series([2023] * 3, dtype="Int64"),
            "vintage_date": pd.Timestamp("2023-06-01"),
            "jurisdiction_geoid": ["3921000", "3921000", "39113"],
            "county_geoid": "39113",
            "land_use_std": "SF_DETACHED",
            "land_use_raw": "x",
            "lot_sqft": 5000.0,
            "year_built": pd.Series([1920, 1950, 1980], dtype="Int64"),
            "lon": -84.2,
            "lat": 39.76,
            "source": "oh_parcels",
        }
    )
    codes = pd.DataFrame(
        {"parcel_id": ["39113R72 00001 0001", "39113R72 00009 0009"], "code": ["510", "500"]}
    )
    out = op.county_yearly_rolls(
        roll,
        {"2012-12-01": codes, "2023-11-30": codes},
        county="39113",
        label="Montgomery CAMA",
        district=op._montgomery_district,
    )
    added = out[out["vintage"] == 2012].set_index("parcel_id")
    # matched parcel keeps its roll jurisdiction; the parcel not in the roll takes district R72's (Dayton)
    assert added["jurisdiction_geoid"].to_dict() == {
        "39113R72 00001 0001": "3921000",
        "39113R72 00009 0009": "3921000",
    }
    assert added.loc["39113R72 00009 0009", "land_use_std"] == "VACANT_RESIDENTIAL"
    assert (out["vintage"] == 2023).sum() == 3  # the statewide roll's year is not read twice
    assert_conforms(out, "parcels")


def test_warren_parcel_numbers_are_zero_padded_and_codes_read():
    raw = pd.DataFrame(
        {
            "PARNUM": [1304760020.0, 1712400017.1, None, 701202005.0],
            "USE_CODE_DSC": ["510-SINGLE FAMILY DWG (PLATTED)", "550-CONDOMINIUM", "500-X", "595-T.I.F."],
        }
    )
    a = op.warren_attributes(raw)
    # 1304760020 → "01304760020"; the fractional and missing PARNUMs are skipped
    assert a["parcel_id"].tolist() == ["3916501304760020", "3916500701202005"]
    assert a["luc"].tolist() == ["510", "595"] and a["year_built"].isna().all()
