"""File geodatabase reader on synthetic geodatabases (no network, no data).

Geodatabases are written here byte by byte from the published format description (FGDB-Spec), so the
reader is checked against the format, not against itself. Hand-worked checks: varuints and signed varints;
a 10 x 10 square (centroid 105, 205; area 100); the same square with a 2 x 2 hole (area 96, centroid
unchanged); an L of two 2 x 1 rectangles (area 4, centroid 0.75, 1.25); two separate squares (centroid by
area weights); a null shape (NaN); a deleted row (absent).
"""

import struct
import zipfile

import numpy as np
import pandas as pd
import pytest

from lotline.adapters.states.tx import filegdb
from lotline.adapters.states.tx import stratmap_parcels as sm

GEOG = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]]]'
ORIGIN, SCALE = (-1000.0, -2000.0), 1000.0


# ---- writers (test only) ----------------------------------------------------------------------------------
def varuint(n: int) -> bytes:
    out = bytearray()
    while True:
        b, n = n & 0x7F, n >> 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def varint(n: int) -> bytes:
    """First byte: more-bit, sign bit, 6 data bits; then 7 data bits a byte."""
    sign, m = (0x40 if n < 0 else 0), abs(n)
    first, m = m & 0x3F, m >> 6
    out = bytearray([first | sign | (0x80 if m else 0)])
    if m:
        out += varuint(m)
    return bytes(out)


def utf16(s: str) -> bytes:
    return bytes([len(s)]) + s.encode("utf-16-le")


def square(x0, y0, side, clockwise=True):
    ring = [(x0, y0), (x0, y0 + side), (x0 + side, y0 + side), (x0 + side, y0), (x0, y0)]
    return ring if clockwise else ring[::-1]


def shape_blob(rings, origin=ORIGIN, scale=SCALE) -> bytes:
    """A 2D polygon (shape type 5): counts, bounding box, part sizes, then x/y deltas on the integer grid."""
    pts = [(round((x - origin[0]) * scale), round((y - origin[1]) * scale)) for r in rings for x, y in r]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    b = varuint(5) + varuint(len(pts)) + varuint(len(rings))
    b += varuint(min(xs)) + varuint(min(ys)) + varuint(max(xs) - min(xs)) + varuint(max(ys) - min(ys))
    for r in rings[:-1]:
        b += varuint(len(r))
    px = py = 0
    for x, y in pts:
        b += varint(x - px) + varint(y - py)
        px, py = x, y
    return varuint(len(b)) + b


def field_desc(name, kind, nullable=True, wkt=GEOG, maxlen=50):
    b = utf16(name) + b"\x00" + bytes([kind])
    flag = 5 if nullable else 4
    if kind == 4:
        b += struct.pack("<iB", maxlen, flag) + varuint(0)
    elif kind == 6:
        b += bytes([4, 2])
    elif kind == 7:
        w = wkt.encode("utf-16-le")
        b += bytes([0, 7 if nullable else 6]) + struct.pack("<h", len(w)) + w + bytes([1])
        b += struct.pack("<8d", ORIGIN[0], ORIGIN[1], SCALE, 0.001, 0, 0, 1, 1)
        b += b"\x00" + struct.pack("<Id", 1, 10.0)
    else:
        width = filegdb.FIXED_WIDTH[kind]
        b += bytes([width, flag if nullable else 2, 0])  # the default-length byte is always there
    return b


def encode_value(kind, v) -> bytes:
    if kind in (4, 12):
        raw = v.encode("utf-8")
        return varuint(len(raw)) + raw
    if kind == 7:
        return shape_blob(v)
    return struct.pack({0: "<h", 1: "<i", 2: "<f", 3: "<d", 13: "<q"}[kind], v)


def table_bytes(fields, rows, geometry_type, *, gap=b"\xde\xad\xbe\xef", spacer=b""):
    """(.gdbtable bytes, live row offsets). `fields`: [(name, kind, nullable)]; rows: dicts (None = null)."""
    descs = b"".join(field_desc(n, k, nl) for n, k, nl in fields)
    section = struct.pack("<iIh", 4, geometry_type | 0x100 | 0x200, len(fields)) + descs
    body = struct.pack("<i", len(section)) + section + gap
    data_fields = [(n, k, nl) for n, k, nl in fields if k != 6]
    nullable = [n for n, _, nl in data_fields if nl]
    out, offsets = bytearray(), []
    for r in rows:
        flags = bytearray(b"\xff" * ((len(nullable) + 7) // 8))
        content = b""
        for n, k, nl in data_fields:
            v = r.get(n)
            if nl and v is not None:
                i = nullable.index(n)
                flags[i // 8] &= ~(1 << (i % 8)) & 0xFF
            if v is not None:
                content += encode_value(k, v)
        blob = bytes(flags) + content
        offsets.append(40 + len(body) + len(out))
        out += struct.pack("<i", len(blob)) + blob + spacer
    size = 40 + len(body) + len(out)
    head = struct.pack("<iiiii", 3, len(rows), 1000, 5, 0) + struct.pack("<iqq", 0, size, 40)
    return head + body + bytes(out), offsets


def tablx_bytes(offsets, width=5, deleted=()) -> bytes:
    slots = [0 if i in deleted else o for i, o in enumerate(offsets)]
    n_blocks = (len(slots) + 1023) // 1024
    slots += [0] * (n_blocks * 1024 - len(slots))
    b = struct.pack("<iiii", 3, n_blocks, len(offsets), width)
    b += b"".join(o.to_bytes(8, "little")[:width] for o in slots)
    return b + struct.pack("<iiii", 0, n_blocks, n_blocks, 0)


PARCEL_FIELDS = [
    ("OBJECTID", 6, False), ("SHAPE", 7, True), ("PROP_ID", 4, True), ("OWNER_NAME", 4, True),
    ("LEGAL_AREA", 3, True), ("LGL_AREA_UNIT", 4, True), ("STAT_LAND_USE", 4, True),
    ("LAND_VALUE", 13, True), ("IMP_VALUE", 13, True), ("FIPS", 4, True), ("TAX_YEAR", 4, True),
    ("SHAPE_Length", 3, True), ("SHAPE_Area", 3, True),
]  # fmt: skip


def write_gdb(path, rows, *, deleted=(), width=5, spacer=b"", name="parcels"):
    """A zipped geodatabase: the catalog, a GDB_Items polygon table (system, empty) and one parcel table."""
    cat_fields = [("OBJECTID", 6, False), ("Name", 4, False), ("FileFormat", 1, False)]
    names = ["GDB_SystemCatalog", "GDB_DBTune", "GDB_SpatialRefs", "GDB_Items", "x5", "x6", "x7", "x8", name]
    cat, cat_off = table_bytes(cat_fields, [{"Name": n, "FileFormat": 0} for n in names], 0)
    items, items_off = table_bytes([("OBJECTID", 6, False), ("Shape", 7, True)], [], 4)
    parcels, off = table_bytes(PARCEL_FIELDS, rows, 4, spacer=spacer)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for stem, (tb, offs, dl) in {
            "a00000001": (cat, cat_off, ()),
            "a00000004": (items, items_off, ()),
            "a00000009": (parcels, off, deleted),
        }.items():
            zf.writestr(f"t.gdb/{stem}.gdbtable", tb)
            zf.writestr(f"t.gdb/{stem}.gdbtablx", tablx_bytes(offs, width, dl))
    return path


L_SHAPE = [(0, 0), (0, 3), (1, 3), (1, 1), (2, 1), (2, 0), (0, 0)]  # clockwise


def sample_rows():
    return [
        {"SHAPE": [square(100, 200, 10)], "PROP_ID": "1", "OWNER_NAME": "JANE DOE", "LEGAL_AREA": 0.25,
         "LGL_AREA_UNIT": "AC", "STAT_LAND_USE": "A1", "LAND_VALUE": 200_000, "IMP_VALUE": 300_000,
         "FIPS": "453", "TAX_YEAR": "2026"},
        {"SHAPE": [square(100, 200, 10), square(104, 204, 2, clockwise=False)], "PROP_ID": "2",
         "OWNER_NAME": None, "STAT_LAND_USE": "B2", "FIPS": "453"},
        {"SHAPE": [L_SHAPE], "PROP_ID": "3", "OWNER_NAME": "Peña", "FIPS": "201", "LAND_VALUE": 5},
        {"SHAPE": [square(0, 0, 1), square(10, 0, 2)], "PROP_ID": "4", "FIPS": "201"},
        {"SHAPE": None, "PROP_ID": "5", "FIPS": "201"},
        {"SHAPE": [square(-50.5, -60.25, 0.5)], "PROP_ID": "6", "STAT_LAND_USE": "Ä1", "FIPS": "201"},
    ]  # fmt: skip


def read_all(path, rows_per_chunk=filegdb.ROWS_PER_CHUNK):
    with zipfile.ZipFile(path) as zf:
        (table,) = filegdb.polygon_tables(zf)
        wanted = ["prop_id", "owner_name", "legal_area", "lgl_area_unit", "stat_land_use", "land_value",
                  "imp_value", "fips", "tax_year"]  # fmt: skip
        return pd.concat(list(filegdb.read_rows(zf, table, wanted, rows_per_chunk)), ignore_index=True)


# ---- tests ------------------------------------------------------------------------------------------------
def test_varuint_and_varint_hand_worked():
    buf = np.frombuffer(bytes([0x05, 0x81, 0x01, 0xFF, 0x7F]), dtype=np.uint8)
    val, end = filegdb._varuint_at(buf, np.array([0, 1, 3]))
    assert val.tolist() == [5, 129, 16_383] and end.tolist() == [1, 3, 5]
    assert varint(5) == b"\x05" and varint(-5) == b"\x45"
    assert varint(65) == b"\x81\x01" and varint(-65) == b"\xc1\x01"  # 1 | 1 << 6


def test_centroids_and_areas_hand_worked(tmp_path):
    df = read_all(write_gdb(tmp_path / "g.zip", sample_rows()))
    assert df.loc[0, ["x", "y", "area"]].tolist() == pytest.approx([105, 205, 100])
    assert df.loc[1, ["x", "y", "area"]].tolist() == pytest.approx([105, 205, 96])  # hole nets out
    assert df.loc[2, ["x", "y", "area"]].tolist() == pytest.approx([0.75, 1.25, 4])  # L shape
    # two parts: (0.5, 0.5) area 1 and (11, 1) area 4 -> (0.5 + 44) / 5, (0.5 + 4) / 5
    assert df.loc[3, ["x", "y", "area"]].tolist() == pytest.approx([44.5 / 5, 4.5 / 5, 5])
    assert df.loc[4, ["x", "y", "area"]].isna().all()  # null shape
    assert df.loc[5, ["x", "y", "area"]].tolist() == pytest.approx([-50.25, -60.0, 0.25])


def test_fields_decoded_only_when_requested_and_nulls_blank(tmp_path):
    df = read_all(write_gdb(tmp_path / "g.zip", sample_rows()))
    assert df["prop_id"].tolist() == ["1", "2", "3", "4", "5", "6"]
    assert df.loc[0, "legal_area"] == 0.25 and df.loc[0, "lgl_area_unit"] == "AC"
    assert df.loc[0, "land_value"] == 200_000 and df.loc[0, "imp_value"] == 300_000  # int64
    assert df.loc[1, "owner_name"] == "" and pd.isna(df.loc[1, "legal_area"])  # null -> blank / NaN
    assert df.loc[2, "owner_name"] == "Peña" and df.loc[5, "stat_land_use"] == "Ä1"  # UTF-8
    assert df.loc[2, "fips"] == "201" and df.loc[2, "land_value"] == 5  # fields after a null decode right


def test_unrequested_fields_are_skipped_not_decoded(tmp_path):
    path = write_gdb(tmp_path / "g.zip", sample_rows())
    with zipfile.ZipFile(path) as zf:
        (table,) = filegdb.polygon_tables(zf)
        df = next(filegdb.read_rows(zf, table, ["prop_id", "fips"]))
    assert set(df.columns) == {"prop_id", "fips", "x", "y", "area"}
    assert df["fips"].tolist() == ["453", "453", "201", "201", "201", "201"]


def test_deleted_rows_gaps_offset_widths_and_chunks(tmp_path):
    whole = read_all(write_gdb(tmp_path / "a.zip", sample_rows()))
    gappy = read_all(write_gdb(tmp_path / "b.zip", sample_rows(), width=4, spacer=b"\x00" * 7), 2)
    pd.testing.assert_frame_equal(whole, gappy)
    dropped = read_all(write_gdb(tmp_path / "c.zip", sample_rows(), deleted={1, 4}))
    assert dropped["prop_id"].tolist() == ["1", "3", "4", "6"]


def test_system_tables_left_out_and_names_from_catalog(tmp_path):
    path = write_gdb(tmp_path / "g.zip", sample_rows())
    with zipfile.ZipFile(path) as zf:
        assert filegdb.catalog_names(zf)["a00000004"] == "GDB_Items"
        assert filegdb.catalog_names(zf)["a00000009"] == "parcels"
        assert [t.member for t in filegdb.tables(zf) if t.geometry_type == filegdb.LAYER_POLYGON] == [
            "t.gdb/a00000004.gdbtable",
            "t.gdb/a00000009.gdbtable",
        ]
        (table,) = filegdb.polygon_tables(zf)
    assert table.member == "t.gdb/a00000009.gdbtable" and table.utf8 and table.n_rows == 6
    assert (table.xorigin, table.yorigin, table.xyscale) == (*ORIGIN, SCALE) and table.wkt == GEOG


def test_field_section_that_does_not_add_up_stops(tmp_path):
    raw, _ = table_bytes(PARCEL_FIELDS, sample_rows(), 4)
    size = struct.unpack("<i", raw[40:44])[0]
    bad = raw[:40] + struct.pack("<i", size + 3) + raw[44:]
    with pytest.raises(ValueError, match="stated size"):
        filegdb.parse_header(bad, "a.gdbtable", "a.gdbtablx")


def test_deadbeef_counted_in_the_field_section_size_is_accepted():
    raw, _ = table_bytes(PARCEL_FIELDS, [], 4)
    size = struct.unpack("<i", raw[40:44])[0]
    raw = raw[:40] + struct.pack("<i", size + 4) + raw[44:]
    table = filegdb.parse_header(raw, "a.gdbtable", "a.gdbtablx")
    assert len(table.fields) == len(PARCEL_FIELDS) - 1  # OBJECTID has no row data


def test_ten_character_names_match():
    raw, _ = table_bytes([("OBJECTID", 6, False), ("Shape", 7, True), ("stat_land_", 4, True)], [], 4)
    table = filegdb.parse_header(raw, "a.gdbtable", "a.gdbtablx")
    assert filegdb.match_fields(table, ["stat_land_use", "fips"]) == {"stat_land_use": "stat_land_"}


def test_non_polygon_shapes_stop():
    blob = np.frombuffer(varuint(1) + varuint(3) + varuint(1) + varuint(1), dtype=np.uint8)  # a point
    with pytest.raises(ValueError, match="not polygons"):
        filegdb.polygon_stats(blob, np.array([blob.size]))


def test_stratmap_reads_a_geodatabase_zip(tmp_path):
    rows = sample_rows()
    rows[0]["SHAPE"] = [square(-97.8, 30.2, 0.002)]
    path = write_gdb(tmp_path / "stratmap26.zip", rows)
    p = sm.read_roll(path, vintage=2026).set_index("parcel_id")
    assert p.loc["484531", "land_use_std"] == "SF_DETACHED"
    assert p.loc["484531", "lot_sqft"] == pytest.approx(0.25 * 43_560)
    assert p.loc["484531", "lon"] == pytest.approx(-97.799) and p.loc["484531", "lat"] == pytest.approx(
        30.201
    )
    assert p.loc["484531", "bldg_value"] == 300_000 and p.loc["482013", "land_value"] == 5
    assert not p.reset_index().astype(str).apply(lambda c: c.str.contains("JANE DOE|Peña")).any().any()
