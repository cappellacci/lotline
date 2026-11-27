"""A minimal reader for ESRI shapefiles of polygons, enough for Census TIGER/Line boundaries.

Reads the `.shp` (polygon records, shape type 5) and `.dbf` (attributes) members of a zip, with the standard
library only, so boundaries need no GIS dependency. Each record gives its attributes and its rings as lists of
`[x, y]` pairs, in the file's own coordinates (TIGER/Line: longitude and latitude, NAD83).

Format reference: ESRI Shapefile Technical Description (1998), and the dBASE III table layout.
"""

from __future__ import annotations

import struct
import zipfile
from pathlib import Path

POLYGON = 5
NULL_SHAPE = 0


def _member(z: zipfile.ZipFile, ext: str) -> bytes:
    names = [n for n in z.namelist() if n.lower().endswith(ext)]
    if len(names) != 1:
        raise ValueError(f"expected one {ext} file in the zip, found {names}")
    return z.read(names[0])


def read_dbf(data: bytes) -> list[dict[str, str]]:
    """Every record of a dBASE table, as {field: stripped text}; deleted records are skipped."""
    n_rec, header_len, rec_len = struct.unpack("<IHH", data[4:12])
    fields, pos = [], 32
    while data[pos] != 0x0D:  # field descriptors end with a carriage return
        name = data[pos : pos + 11].split(b"\0", 1)[0].decode("ascii")
        fields.append((name, data[pos + 16]))
        pos += 32
    rows = []
    for i in range(n_rec):
        rec = data[header_len + i * rec_len : header_len + (i + 1) * rec_len]
        if rec[:1] == b"*":  # deleted
            continue
        row, off = {}, 1
        for name, length in fields:
            row[name] = rec[off : off + length].decode("latin-1").strip()
            off += length
        rows.append(row)
    return rows


def read_polygons(data: bytes) -> list[list[list[list[float]]] | None]:
    """The rings of every record of a polygon `.shp` ([[x, y], ...] per ring); None for a null shape."""
    if struct.unpack(">i", data[0:4])[0] != 9994:
        raise ValueError("not a shapefile (bad file code)")
    shape_type = struct.unpack("<i", data[32:36])[0]
    if shape_type != POLYGON:
        raise ValueError(f"shape type {shape_type} is not a polygon (5)")
    out, pos = [], 100
    while pos < len(data):
        content_words = struct.unpack(">i", data[pos + 4 : pos + 8])[0]
        rec = data[pos + 8 : pos + 8 + 2 * content_words]
        pos += 8 + 2 * content_words
        kind = struct.unpack("<i", rec[0:4])[0]
        if kind == NULL_SHAPE:
            out.append(None)
            continue
        if kind != POLYGON:
            raise ValueError(f"record of shape type {kind} in a polygon file")
        n_parts, n_points = struct.unpack("<ii", rec[36:44])
        parts = list(struct.unpack(f"<{n_parts}i", rec[44 : 44 + 4 * n_parts]))
        xy = struct.unpack(f"<{2 * n_points}d", rec[44 + 4 * n_parts : 44 + 4 * n_parts + 16 * n_points])
        bounds = parts + [n_points]
        out.append(
            [[[xy[2 * k], xy[2 * k + 1]] for k in range(bounds[j], bounds[j + 1])] for j in range(n_parts)]
        )
    return out


def read_zip(path: Path) -> list[dict]:
    """Attributes plus `rings` for every record of the polygon shapefile inside a zip."""
    with zipfile.ZipFile(path) as z:
        attrs = read_dbf(_member(z, ".dbf"))
        rings = read_polygons(_member(z, ".shp"))
    if len(attrs) != len(rings):
        raise ValueError(f"{path.name}: {len(attrs)} attribute rows but {len(rings)} shapes")
    return [a | {"rings": r} for a, r in zip(attrs, rings, strict=True)]
