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
