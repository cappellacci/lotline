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
        assert layer.parcel_field and layer.luc_field


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
