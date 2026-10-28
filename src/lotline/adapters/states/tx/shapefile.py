"""Read polygon shapefiles in a zip: centroids, areas and selected attributes (helper, no data). numpy only.

StratMap parcels arrive as zipped ESRI shapefiles: a `.shp` (geometry), a `.dbf` (attributes, one record per
shape, same order), a `.prj` (coordinate system) and sometimes a `.cpg` (text encoding). This module reads
only what the parcel table needs, streaming from the zip so a statewide file never sits in memory whole:

- **`.shp`** (ESRI Shapefile Technical Description, 1998): for each record, the polygon's **centroid** and
  **planar area** from the shoelace formula summed over all its rings. Shapefile outer rings run clockwise
  and holes counter-clockwise, so the signed sum nets holes out of both. A record whose rings sum to zero
  area (degenerate) gets the mean of its vertices. Null shapes get NaN. Polygon, PolygonZ and PolygonM
  (types 5, 15, 25) are read; Z and M values are skipped.
- **`.dbf`** (dBASE III): the header gives the record count, record length and the field table; records are
  read in chunks as fixed-width byte rows, and **only the requested fields are cut out and decoded**, so
  other fields (owner names, mailing addresses) are never decoded into text. Deleted records (flag `*`) are
  kept as rows (they stay aligned with the shapes) and marked in `_deleted`.

Field names in a `.dbf` are at most 10 characters, so a requested name also matches its first 10 characters
(`stat_land_use` ↔ `stat_land_`), case-insensitively.
"""

from __future__ import annotations

import struct
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd

POLYGON_TYPES = {5, 15, 25}
DBF_CHUNK = 200_000  # records per chunk: bounds memory on statewide files (mechanics only)


@dataclass(frozen=True)
class Layer:
    """The members of one shapefile inside a zip (paths within the zip)."""

    shp: str
    dbf: str
    prj: str | None
    cpg: str | None


def layers(zf: zipfile.ZipFile) -> list[Layer]:
    """Every shapefile in the zip (a `.shp` with a matching `.dbf`), in name order."""
    names = {n.lower(): n for n in zf.namelist()}
    out = []
    for low, name in sorted(names.items()):
        if not low.endswith(".shp"):
            continue
        stem = low[:-4]
        if stem + ".dbf" not in names:
            continue
        out.append(Layer(name, names[stem + ".dbf"], names.get(stem + ".prj"), names.get(stem + ".cpg")))
    return out


def _rings_stats(parts: np.ndarray, pts: np.ndarray) -> tuple[float, float, float]:
    """(centroid x, centroid y, signed area) over all rings; area > 0 for clockwise outer rings."""
    a_sum = cx = cy = 0.0
    bounds = list(parts) + [len(pts)]
    for i in range(len(parts)):
        r = pts[bounds[i] : bounds[i + 1]]
        if len(r) < 3:
            continue
        x, y = r[:, 0], r[:, 1]
        x1, y1 = np.roll(x, -1), np.roll(y, -1)
        cross = x * y1 - x1 * y
        a = cross.sum() / 2
        a_sum += a
        cx += ((x + x1) * cross).sum() / 6
        cy += ((y + y1) * cross).sum() / 6
    if a_sum == 0:
        return float(pts[:, 0].mean()), float(pts[:, 1].mean()), 0.0
    # clockwise rings give negative shoelace sums; flip so outer rings count positive
    return cx / a_sum, cy / a_sum, -a_sum


def read_shapes(zf: zipfile.ZipFile, member: str) -> pd.DataFrame:
    """One row per shape record: x, y (centroid, projected units) and area (projected units squared)."""
    xs, ys, areas = [], [], []
    with zf.open(member) as fh:
        header = fh.read(100)
        if len(header) < 100 or struct.unpack(">i", header[:4])[0] != 9994:
            raise ValueError(f"{member}: not a shapefile (bad file code)")
        while True:
            rec = fh.read(8)
            if len(rec) < 8:
                break
            _, words = struct.unpack(">ii", rec)
            body = fh.read(words * 2)
            shape_type = struct.unpack("<i", body[:4])[0]
            if shape_type == 0:
                xs.append(np.nan), ys.append(np.nan), areas.append(np.nan)
                continue
            if shape_type not in POLYGON_TYPES:
                raise ValueError(f"{member}: shape type {shape_type} is not a polygon")
            n_parts, n_points = struct.unpack("<ii", body[36:44])
            parts = np.frombuffer(body, dtype="<i4", count=n_parts, offset=44)
            pts = np.frombuffer(body, dtype="<f8", count=2 * n_points, offset=44 + 4 * n_parts).reshape(-1, 2)
            cx, cy, a = _rings_stats(parts, pts)
            xs.append(cx), ys.append(cy), areas.append(abs(a))
    return pd.DataFrame({"x": xs, "y": ys, "area": areas})


@dataclass(frozen=True)
class _Field:
    name: str
    kind: str
    offset: int
    length: int


def _dbf_header(fh) -> tuple[int, int, int, list[_Field]]:
    head = fh.read(32)
    n_records, header_len, record_len = struct.unpack("<IHH", head[4:12])
    raw = fh.read(header_len - 32)
    fields, offset = [], 1  # byte 0 of each record is the deletion flag
    for i in range(0, len(raw) - 1, 32):
        desc = raw[i : i + 32]
        if desc[0] == 0x0D:
            break
        name = desc[:11].split(b"\x00", 1)[0].decode("ascii", "replace").strip()
        kind, length = chr(desc[11]), desc[16]
        fields.append(_Field(name, kind, offset, length))
        offset += length
    return n_records, header_len, record_len, fields


def dbf_fields(zf: zipfile.ZipFile, member: str) -> list[str]:
    with zf.open(member) as fh:
        return [f.name for f in _dbf_header(fh)[3]]


def match_fields(available: list[str], wanted: list[str]) -> dict[str, str]:
    """Requested name → the `.dbf` field it is stored as (exact, or its 10-character truncation)."""
    low = {a.lower(): a for a in available}
    out = {}
    for w in wanted:
        hit = low.get(w.lower()) or low.get(w.lower()[:10])
        if hit:
            out[w] = hit
    return out


def read_records(
    zf: zipfile.ZipFile, member: str, wanted: list[str], encoding: str = "latin-1"
) -> Iterator[pd.DataFrame]:
    """Chunks of the requested fields (text, stripped; "" if blank) and `_deleted`; others never decoded."""
    with zf.open(member) as fh:
        n_records, _, record_len, fields = _dbf_header(fh)
        by_name = {f.name: f for f in fields}
        cols = {w: by_name[f] for w, f in match_fields([f.name for f in fields], wanted).items()}
        left = n_records
        while left > 0:
            n = min(DBF_CHUNK, left)
            buf = fh.read(n * record_len)
            n = len(buf) // record_len
            if n == 0:
                break
            rows = np.frombuffer(buf[: n * record_len], dtype=f"S{record_len}")
            raw = rows.view(np.uint8).reshape(n, record_len)
            out = {"_deleted": raw[:, 0] == ord("*")}
            for w, f in cols.items():
                cells = raw[:, f.offset : f.offset + f.length].copy().view(f"S{f.length}").ravel()
                out[w] = pd.Series(cells).str.decode(encoding, errors="replace").str.strip()
            yield pd.DataFrame(out)
            left -= n
