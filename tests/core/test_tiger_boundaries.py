"""TIGER/Line 2025 boundaries: the shapefile reader and the incorporated-places filter (synthetic)."""

import io
import struct
import zipfile

import httpx
import pytest

from lotline.adapters.national import tiger_boundaries as tb
from lotline.io import http, shapefile
from lotline.io.store import DataStore


# ---- a tiny polygon shapefile zip, written by hand ----
def shp_bytes(shapes):
    """`shapes`: list of ring lists ([[x, y], ...] per ring) or None for a null shape."""
    recs = b""
    for i, rings in enumerate(shapes, 1):
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
            content += struct.pack(f"<{2 * len(pts)}d", *[c for p in pts for c in p])
        recs += struct.pack(">2i", i, len(content) // 2) + content
    header = struct.pack(">7i", 9994, 0, 0, 0, 0, 0, (100 + len(recs)) // 2)
    header += struct.pack("<2i", 1000, 5) + struct.pack("<8d", *([0.0] * 8))
    return header + recs


def dbf_bytes(rows, fields):
    """`fields`: [(name, width)] of character fields; `rows`: list of dicts."""
    rec_len = 1 + sum(w for _, w in fields)
    header_len = 32 + 32 * len(fields) + 1
    out = struct.pack("<B3BIHH20x", 3, 26, 1, 1, len(rows), header_len, rec_len)
    for name, w in fields:
        out += name.encode().ljust(11, b"\0") + b"C" + b"\0" * 4 + bytes([w, 0]) + b"\0" * 14
    out += b"\r"
    for r in rows:
        out += b" " + b"".join(str(r[n]).encode().ljust(w) for n, w in fields)
    return out + b"\x1a"


def zip_bytes(stem, rows, fields, shapes):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{stem}.shp", shp_bytes(shapes))
        z.writestr(f"{stem}.dbf", dbf_bytes(rows, fields))
        z.writestr(f"{stem}.prj", "GEOGCS[NAD83]")
    return buf.getvalue()


SQUARE = [[0.0, 0.0], [0.0, 10.0], [10.0, 10.0], [10.0, 0.0], [0.0, 0.0]]
HOLE = [[2.0, 2.0], [4.0, 2.0], [4.0, 4.0], [2.0, 4.0], [2.0, 2.0]]
ISLAND = [[20.0, 0.0], [20.0, 5.0], [25.0, 5.0], [20.0, 0.0]]
FIELDS = [("GEOID", 7), ("NAME", 20), ("CLASSFP", 2), ("FUNCSTAT", 1)]
ROWS = [
    {"GEOID": "3918000", "NAME": "Columbus city", "CLASSFP": "C1", "FUNCSTAT": "A"},
    {"GEOID": "3901000", "NAME": "Ada village", "CLASSFP": "C5", "FUNCSTAT": "A"},
    {"GEOID": "3912345", "NAME": "Some CDP", "CLASSFP": "U1", "FUNCSTAT": "S"},
    {"GEOID": "3986660", "NAME": "Air base", "CLASSFP": "M2", "FUNCSTAT": "I"},
]
SHAPES = [[SQUARE, HOLE], [ISLAND], [SQUARE], [ISLAND]]


def test_the_reader_returns_attributes_and_rings(tmp_path):
    z = tmp_path / "t.zip"
    z.write_bytes(zip_bytes("t", ROWS[:2] + [ROWS[2]], FIELDS, [[SQUARE, HOLE], None, [ISLAND]]))
    recs = shapefile.read_zip(z)
    assert [r["GEOID"] for r in recs] == ["3918000", "3901000", "3912345"]
    assert recs[0]["NAME"] == "Columbus city" and recs[0]["rings"] == [SQUARE, HOLE]
    assert recs[1]["rings"] is None  # a null shape


def test_the_reader_refuses_a_non_polygon_file(tmp_path):
    z = tmp_path / "t.zip"
    z.write_bytes(zip_bytes("t", ROWS[:1], FIELDS, [[SQUARE]]))
    data = shapefile._member(zipfile.ZipFile(z), ".shp")
    with pytest.raises(ValueError, match="not a polygon"):
        shapefile.read_polygons(data[:32] + (1).to_bytes(4, "little") + data[36:])


def test_load_polygons_keeps_incorporated_places_only(tmp_path, monkeypatch):
    payload = zip_bytes("tl_2025_39_place", ROWS, FIELDS, SHAPES)
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=payload, headers={"content-type": "application/zip"})

    monkeypatch.setattr(http, "client", lambda **kw: httpx.Client(transport=httpx.MockTransport(handler)))
    store = DataStore(tmp_path)
    df = tb.load_polygons("OH", store, "place")
    assert seen == ["https://www2.census.gov/geo/tiger/TIGER2025/PLACE/tl_2025_39_place.zip"]
    assert df["geoid"].tolist() == ["3901000", "3918000"]  # sorted; the CDP and the military area are dropped
    assert df.columns.tolist() == ["geoid", "name", "funcstat", "rings"]
    assert df["rings"].iloc[1] == [SQUARE, HOLE]
    assert tb.cached("OH", store, "place") and not tb.cached("OH", store, "cousub")
    tb.load_polygons("OH", store, "place")
    assert len(seen) == 1  # the second load reads the cached zip
    with pytest.raises(ValueError, match="level"):
        tb.load_polygons("OH", store, "cdp")
