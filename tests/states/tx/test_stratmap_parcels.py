"""StratMap parcels adapter, shapefile reader and projection helper on synthetic files (no network, no data).

Shapefiles are written here byte by byte from the ESRI and dBASE layouts, so the reader is checked against
the format, not against itself. Hand-worked checks: a 10 x 10 square (centroid 5, 5; area 100); the same
square with a 2 x 2 hole (area 96, centroid unchanged); an L of two rectangles (centroid by area weights);
the Albers origin maps to the false easting and northing.
"""

import struct
import zipfile

import numpy as np
import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.tx import projection, shapefile
from lotline.adapters.states.tx import stratmap_parcels as sm
from lotline.config import load_params
from lotline.io import DataStore
from lotline.schemas import assert_conforms

TX_ALBERS = (
    'PROJCS["NAD_1983_Texas_Centric_Mapping_System_Albers",GEOGCS["GCS_North_American_1983",'
    'DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],'
    'UNIT["Degree",0.0174532925199433]],PROJECTION["Albers"],PARAMETER["False_Easting",1500000.0],'
    'PARAMETER["False_Northing",6000000.0],PARAMETER["Central_Meridian",-100.0],'
    'PARAMETER["Standard_Parallel_1",27.5],PARAMETER["Standard_Parallel_2",35.0],'
    'PARAMETER["Latitude_Of_Origin",18.0],UNIT["Meter",1.0]]'
)
GEOG = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]]]'
ALBERS = dict(lat1=27.5, lat2=35.0, lat0=18.0, lon0=-100.0, fe=1_500_000.0, fn=6_000_000.0)


# ---- writers (test only) ----------------------------------------------------------------------------------
def square(x0, y0, side):
    """A clockwise ring (shapefile outer ring)."""
    return [(x0, y0), (x0, y0 + side), (x0 + side, y0 + side), (x0 + side, y0), (x0, y0)]


def shp_bytes(shapes: list[list[list[tuple[float, float]]] | None]) -> bytes:
    chunks = []
    for i, rings in enumerate(shapes, start=1):
        if rings is None:
            content = struct.pack("<i", 0)
        else:
            pts = [p for r in rings for p in r]
            parts, k = [], 0
            for r in rings:
                parts.append(k)
                k += len(r)
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            content = struct.pack("<i4d2i", 5, min(xs), min(ys), max(xs), max(ys), len(rings), len(pts))
            content += struct.pack(f"<{len(parts)}i", *parts)
            content += b"".join(struct.pack("<2d", *p) for p in pts)
        chunks.append(struct.pack(">2i", i, len(content) // 2) + content)
    recs = b"".join(chunks)
    header = struct.pack(">7i", 9994, 0, 0, 0, 0, 0, (100 + len(recs)) // 2)
    header += struct.pack("<2i4d4d", 1000, 5, 0, 0, 0, 0, 0, 0, 0, 0)
    return header + recs


def dbf_bytes(fields: list[tuple[str, int]], rows: list[dict], deleted: set[int] = frozenset()) -> bytes:
    record_len = 1 + sum(n for _, n in fields)
    header_len = 32 + 32 * len(fields) + 1
    out = struct.pack("<B3BIHH20x", 3, 126, 10, 26, len(rows), header_len, record_len)
    for name, n in fields:
        out += name.encode("ascii").ljust(11, b"\x00") + b"C" + b"\x00" * 4 + bytes([n, 0]) + b"\x00" * 14
    out += b"\x0d"
    records = [
        (b"*" if i in deleted else b" ")
        + b"".join(str(r.get(name, "")).encode("latin-1")[:n].ljust(n) for name, n in fields)
        for i, r in enumerate(rows)
    ]
    return out + b"".join(records) + b"\x1a"


DBF_FIELDS = [
    ("prop_id", 12), ("geo_id", 20), ("owner_name", 30), ("fips", 5), ("county", 12), ("tax_year", 4),
    ("stat_land_", 6), ("loc_land_u", 6), ("legal_area", 12), ("lgl_area_u", 6), ("gis_area", 12),
    ("gis_area_u", 6), ("land_value", 12), ("imp_value", 12), ("year_built", 4), ("mail_addr", 30),
]  # fmt: skip


def write_zip(path, shapes, rows, prj=GEOG, deleted=frozenset(), name="stratmap_test"):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(f"{name}.shp", shp_bytes(shapes))
        zf.writestr(f"{name}.dbf", dbf_bytes(DBF_FIELDS, rows, deleted))
        zf.writestr(f"{name}.prj", prj)
    return path


# ---- projection ------------------------------------------------------------------------------------------
def test_albers_origin_maps_to_false_origin_and_round_trips():
    x, y = projection.albers_forward(-100.0, 18.0, **ALBERS)
    assert x == pytest.approx(1_500_000.0) and y == pytest.approx(6_000_000.0)
    lon = np.array([-106.5, -97.74, -94.1, -100.0])
    lat = np.array([31.76, 30.27, 33.4, 26.0])
    x, y = projection.albers_forward(lon, lat, **ALBERS)
    back_lon, back_lat = projection.from_wkt(TX_ALBERS)(x, y)
    np.testing.assert_allclose(back_lon, lon, atol=1e-9)
    np.testing.assert_allclose(back_lat, lat, atol=1e-9)
    assert projection.equal_area_sqm_per_unit2(TX_ALBERS) == 1.0


def test_geographic_web_mercator_and_unsupported():
    lon, lat = projection.from_wkt(GEOG)(np.array([-97.0]), np.array([30.0]))
    assert (lon[0], lat[0]) == (-97.0, 30.0)
    merc = (
        'PROJCS["WGS_1984_Web_Mercator_Auxiliary_Sphere",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
        'SPHEROID["WGS_1984",6378137.0,298.257223563]]],PROJECTION["Mercator_Auxiliary_Sphere"],'
        'PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],'
        'UNIT["Meter",1.0]]'
    )
    a = 6378137.0
    lon, lat = projection.from_wkt(merc)(np.array([a * np.radians(-97.0)]), np.array([0.0]))
    assert lon[0] == pytest.approx(-97.0) and lat[0] == pytest.approx(0.0)
    assert projection.equal_area_sqm_per_unit2(merc) is None
    with pytest.raises(ValueError, match="unsupported projection"):
        projection.from_wkt(merc.replace("Mercator_Auxiliary_Sphere", "Transverse_Mercator"))


def test_web_mercator_true_area_factor_hand_worked():
    merc = (
        'PROJCS["WGS_1984_Web_Mercator_Auxiliary_Sphere",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
        'SPHEROID["WGS_1984",6378137.0,298.257223563]]],PROJECTION["Mercator_Auxiliary_Sphere"],'
        'UNIT["Meter",1.0]]'
    )
    # e^2 = f (2 - f) = 0.00669438 (WGS84); at 0: 1 - e^2; at 60 N: 0.25 (1 - e^2) / (1 - 0.75 e^2)^2
    got = projection.sqm_per_unit2(merc, [0.0, 60.0])
    assert got == pytest.approx([0.99330562, 0.25 * 0.99330562 / (1 - 0.75 * 0.00669438) ** 2], rel=1e-7)
    assert got[1] == pytest.approx(0.25, rel=0.01)  # close to the sphere's cos^2
    assert (
        projection.sqm_per_unit2(TX_ALBERS, [30.0]) == 1.0 and projection.sqm_per_unit2(GEOG, [30.0]) is None
    )
    # lot size from the polygon when no stated area: 1,000 squared units at 0 N -> 993.3 m^2
    df = pd.DataFrame({"area": [1000.0, 1000.0], "legal_area": ["", "0.5"], "lgl_area_unit": ["", "AC"]})
    lots = sm.lot_sqft(df, projection.sqm_per_unit2(merc, [0.0, 0.0]))
    assert lots.tolist() == pytest.approx([993.30562 * sm.SQFT_PER_SQM, 0.5 * 43_560])


# ---- shapefile reader ------------------------------------------------------------------------------------
def test_centroids_and_areas_hand_worked(tmp_path):
    hole = [(4, 4), (6, 4), (6, 6), (4, 6), (4, 4)]  # counter-clockwise: a hole
    ell = [square(0, 0, 2), [(2, 0), (2, 1), (6, 1), (6, 0), (2, 0)]]  # two clockwise rings
    shapes = [[square(0, 0, 10)], [square(0, 0, 10), hole], ell, None]
    path = write_zip(tmp_path / "s.zip", shapes, [{"prop_id": str(i)} for i in range(4)])
    with zipfile.ZipFile(path) as zf:
        (layer,) = shapefile.layers(zf)
        s = shapefile.read_shapes(zf, layer.shp)
    assert s.loc[0, ["x", "y", "area"]].tolist() == pytest.approx([5, 5, 100])
    assert s.loc[1, ["x", "y", "area"]].tolist() == pytest.approx([5, 5, 96])
    # L: a 2 x 2 square (centroid 1, 1; area 4) and a 4 x 1 strip (centroid 4, 0.5; area 4)
    assert s.loc[2, ["x", "y", "area"]].tolist() == pytest.approx([2.5, 0.75, 8])
    assert s.loc[3, ["x", "y", "area"]].isna().all()


def test_dbf_reads_only_requested_fields_by_truncated_name(tmp_path):
    rows = [{"prop_id": "1", "owner_name": "JANE DOE", "stat_land_": "A1", "mail_addr": "1 MAIN"}]
    path = write_zip(tmp_path / "s.zip", [[square(0, 0, 1)]], rows, deleted={0})
    with zipfile.ZipFile(path) as zf:
        (layer,) = shapefile.layers(zf)
        (chunk,) = list(shapefile.read_records(zf, layer.dbf, ["prop_id", "stat_land_use"]))
    assert list(chunk.columns) == ["_deleted", "prop_id", "stat_land_use"]
    assert chunk.loc[0, "stat_land_use"] == "A1" and bool(chunk.loc[0, "_deleted"])


# ---- adapter ---------------------------------------------------------------------------------------------
def base_row(**kw):
    r = {"prop_id": "100", "geo_id": "G100", "fips": "453", "county": "TRAVIS", "tax_year": "2026",
         "stat_land_": "A1", "legal_area": "0.25", "lgl_area_u": "AC", "land_value": "200000",
         "imp_value": "300000", "year_built": "1995", "owner_name": "JANE DOE",
         "mail_addr": "1 MAIN ST"}  # fmt: skip
    r.update(kw)
    return r


def rows_and_shapes():
    rows = [
        base_row(),
        base_row(prop_id="101", stat_land_="B2", legal_area="5000", lgl_area_u="SQFT", year_built="0"),
        base_row(
            prop_id="102", stat_land_="", loc_land_u="R1", legal_area="", gis_area="", year_built="2031"
        ),
        base_row(prop_id="103", stat_land_="C1", legal_area="", gis_area="1", gis_area_u="ACRES"),
        base_row(prop_id="104", stat_land_="ZZ", fips="48201"),
        base_row(prop_id="105", legal_area="0.1"),  # a second, smaller polygon of property 105
        base_row(prop_id="105", legal_area="0.2"),
        base_row(prop_id="", geo_id="GEO9", stat_land_="D1"),
        base_row(prop_id="106", fips=""),
        base_row(prop_id="107", tax_year="0"),  # no roll year: the registration's vintage
        base_row(prop_id="108", tax_year="2025"),  # an older county roll inside the release: same roll
    ]
    shapes = [[square(-97.8 + i / 1000, 30.2, 0.0005 * (2 if i == 6 else 1))] for i in range(len(rows))]
    return rows, shapes


def built(tmp_path, prj=GEOG):
    rows, shapes = rows_and_shapes()
    path = write_zip(tmp_path / "s.zip", shapes, rows, prj=prj)
    return sm.read_roll(path, vintage=2026).set_index("parcel_id")


def test_build_land_use_lots_years_values(tmp_path):
    p = built(tmp_path)
    assert p.loc["48453100", "land_use_std"] == "SF_DETACHED"  # A1 -> category A
    assert p.loc["48453100", "lot_sqft"] == pytest.approx(0.25 * 43_560)
    assert p.loc["48453101", "lot_sqft"] == pytest.approx(5000)
    assert pd.isna(p.loc["48453101", "year_built"])  # 0 is "none"
    assert p.loc["48453102", "land_use_std"] == "UNKNOWN" and p.loc["48453102", "land_use_raw"] == "R1"
    assert pd.isna(p.loc["48453102", "lot_sqft"]) and pd.isna(p.loc["48453102", "year_built"])  # 2031 > roll
    assert p.loc["48453103", "lot_sqft"] == pytest.approx(43_560)  # gis_area in acres
    assert p.loc["48201104", "land_use_std"] == "UNKNOWN"  # unknown code; county from a 5-digit fips
    assert p.loc["48453GEO9", "land_use_std"] == "AGRICULTURAL"  # geo_id when prop_id is blank
    assert p.loc["48453100", "value_basis"] == "appraisal" and p.loc["48453100", "bldg_value"] == 300000
    assert p.loc["48453100", "year_built"] == 1995 and p.loc["48453100", "vintage"] == 2026
    assert (
        p.loc["48453107", "vintage"] == 2026 and p.loc["48453108", "vintage"] == 2026
    )  # one roll per release
    assert (
        sm.read_roll(tmp_path / "s.zip", vintage=None).set_index("parcel_id").loc["48453108", "vintage"]
        == 2025
    )


def test_one_row_per_property_keeps_the_largest_polygon(tmp_path):
    p = built(tmp_path)
    assert p.index.tolist().count("48453105") == 1
    assert p.loc["48453105", "lot_sqft"] == pytest.approx(0.2 * 43_560)
    assert "48453106" not in p.index and not any(
        i.startswith("48<NA>") for i in p.index
    )  # no county: dropped


def test_area_from_the_polygon_on_an_equal_area_projection(tmp_path):
    x, y = projection.albers_forward(-97.7, 30.3, **ALBERS)
    side = 20.0  # metres
    rows = [base_row(legal_area="", gis_area="")]
    path = write_zip(tmp_path / "a.zip", [[square(float(x), float(y), side)]], rows, prj=TX_ALBERS)
    p = sm.read_roll(path, vintage=2026)
    assert p.loc[0, "lot_sqft"] == pytest.approx(side * side * sm.SQFT_PER_SQM)
    assert p.loc[0, "lon"] == pytest.approx(-97.7, abs=1e-3) and p.loc[0, "lat"] == pytest.approx(
        30.3, abs=1e-3
    )


def test_privacy_owner_and_address_never_kept(tmp_path):
    assert not set(sm.FIELDS) & sm.PERSONAL
    p = built(tmp_path).reset_index()
    assert not p.astype(str).apply(lambda c: c.str.contains("JANE DOE|MAIN ST")).any().any()


def test_resolve_jurisdictions_place_else_county():
    county = pd.Series(["48453", "48453", "48201"])
    place = pd.Series(["4805000", "4899999", None], dtype=object)
    got = sm.resolve_jurisdictions(county, place, {"4805000", "48453", "48201"})
    assert got.tolist() == ["4805000", "48453", "48201"]


def test_resolve_jurisdictions_drops_county_remainders_that_are_not_jurisdictions():
    # 48001 (Anderson) has no remainder jurisdiction: its unincorporated parcels belong to no jurisdiction
    county = pd.Series(["48001", "48001", "48453"])
    place = pd.Series(["4803000", None, None], dtype=object)
    got = sm.resolve_jurisdictions(county, place, {"4803000", "48453"})
    assert got.iloc[0] == "4803000"
    assert pd.isna(got.iloc[1])
    assert got.iloc[2] == "48453"


def test_zip_without_shapefile_or_geodatabase_stops(tmp_path):
    path = tmp_path / "g.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("readme.txt", b"x")
    with pytest.raises(FileNotFoundError, match="no shapefile"):
        sm.read_roll(path, vintage=2026)


def test_load_without_registration_explains_register(tmp_path):
    with pytest.raises(FileNotFoundError, match="lotline manifest register"):
        sm.load("TX", DataStore(tmp_path))


def test_load_registered_zip_assigns_and_validates(tmp_path, monkeypatch):
    rows, shapes = rows_and_shapes()
    src = write_zip(tmp_path / "stratmap26-landparcels_48_lp.zip", shapes, rows)
    store = DataStore(tmp_path / "data")
    store.register(src, source=sm.SOURCE, url=sm.LANDING_URL, license=sm.LICENSE, vintage="2025-06")
    store.register(
        src, source=sm.SOURCE, url=sm.LANDING_URL, license=sm.LICENSE, vintage="2026-09"
    )  # not read
    juris = pd.DataFrame({"geoid": ["4805000", "48453", "48201"]})
    monkeypatch.setattr(store, "read", lambda state, table: juris)
    from lotline import geo

    monkeypatch.setattr(
        geo, "place_or_township", lambda lon, lat, state, store: pd.Series("4805000", index=lon.index)
    )
    out = sm.load("TX", store)
    assert_conforms(out, "parcels")
    assert set(out.jurisdiction_geoid) == {"4805000"}
    assert len(out) == 9  # eleven rows: property 105 twice, one without a county


def test_load_reads_only_the_named_rolls(tmp_path):
    rows, shapes = rows_and_shapes()
    src = write_zip(tmp_path / "stratmap22-landparcels_48_lp.zip", shapes, rows)
    store = DataStore(tmp_path / "data")
    store.register(src, source=sm.SOURCE, url=sm.LANDING_URL, license=sm.LICENSE, vintage="2022-07")
    assert "2022-07" not in sm.ROLLS
    with pytest.raises(FileNotFoundError, match="none of the rolls read"):
        sm.load("TX", store)


def test_partial_county_parts_dropped_with_their_jurisdictions():
    def roll(counts):  # {(county, jurisdiction): n parcels}
        rows = [(c, j) for (c, j), n in counts.items() for _ in range(n)]
        return pd.DataFrame(rows, columns=["county_geoid", "jurisdiction_geoid"])

    # release 0: Harris (48201) has 66 against 100 in release 1 -> 0.66, partial; Houston also has 10
    # parcels in Fort Bend (48157), which is complete (10 of 10) but goes with Houston; Galveston (48167) 0.9
    r0 = roll(
        {("48201", "4835000"): 50, ("48201", "48201"): 16, ("48157", "4835000"): 10, ("48167", "48167"): 9}
    )
    r1 = roll(
        {("48201", "4835000"): 80, ("48201", "48201"): 20, ("48157", "4835000"): 10, ("48167", "48167"): 10}
    )
    (k0, k1), dropped = sm.drop_partial_counties([r0, r1], 0.8)
    assert set(k0["jurisdiction_geoid"]) == {"48167"} and len(k1) == len(r1)
    assert dropped.to_dict("records") == [
        {"release": 0, "county_geoid": "48201", "parcels": 66, "other_release_parcels": 100, "share": 0.66}
    ]
    (only,), none = sm.drop_partial_counties([r0], 0.8)  # one release: nothing to compare against
    assert len(only) == len(r0) and none.empty
    assert load_params("parcels")["min_county_roll_completeness"].value == 0.8


def test_registered_as_tx_source():
    assert registry.sources_for("TX")["stratmap_parcels"].module.TABLE == "parcels"


def test_county_land_use_fills_unknown_from_listed_codes(tmp_path):
    path = tmp_path / "county.csv"
    path.write_text(
        "county_geoid,code,meaning,land_use_std,confidence,source_url,note,applied\n"
        "48491,RES,Residential single family,SF_DETACHED,high,https://example.org,,yes\n"
        "48491,L,Land,VACANT_RESIDENTIAL,low,https://example.org,,no\n"
        "48167,RL,Residential lot (land type),SF_DETACHED,medium,https://example.org,,no\n"
        "48201,Z1,Unclear,UNKNOWN,medium,https://example.org,,yes\n"
    )
    local = sm.load_county_land_use(path)
    assert local == {"48491|RES": "SF_DETACHED"}  # rows not applied, and UNKNOWN rows, are not used
    std = pd.Series(["UNKNOWN", "UNKNOWN", "COMMERCIAL", "UNKNOWN"])
    county = pd.Series(["48491", "48491", "48491", "48453"])
    code = pd.Series(["RES", "L", "RES", "RES"])
    got = sm.county_land_use(std, county, code, local)
    # only an UNKNOWN parcel in the listed county with a listed code changes
    assert got.tolist() == ["SF_DETACHED", "UNKNOWN", "COMMERCIAL", "UNKNOWN"]
