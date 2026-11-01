"""Read polygon tables in a zipped Esri file geodatabase: centroids, areas, selected fields. numpy only.

StratMap's statewide parcel zips hold one file geodatabase (a `.gdb` folder) rather than shapefiles. This
module reads what the parcel table needs straight from the zip, written from the published, reverse-engineered
format description (Even Rouault, "FGDB-Spec", https://github.com/rouault/dump_gdbtable/wiki/FGDB-Spec; no
code was taken from GDAL or any other reader). Like `shapefile`, it streams the table in chunks, so a 6 GB
table never sits in memory whole.

**Files.** Each table `aXXXXXXXX` is a `.gdbtable` (header, field descriptions, row blobs) and a `.gdbtablx`
(the byte offset of every row, 0 for a deleted one, in 4- to 6-byte little-endian integers). Rows are read
in file order from the offsets, so free space between rows is skipped and deleted rows never appear.

**Fields.** The field section lists each field's name, type and flags. Field types read: 16-, 32- and 64-bit
integers, 32- and 64-bit floats, dates (days since 1899-12-30), strings, GUIDs, XML, binary and the
geometry. A raster field stops with an error. The geometry field carries the coordinate system (ESRI WKT)
and the integer grid: `x = X / xyscale + xorigin`. One detail differs from the description, as observed in
StratMap's 2026 file and checked by the parse ending exactly at the section's stated size: fixed-width fields
always carry the default-value length byte, not only when flag bit 2 is set. Some writers (StratMap 2022)
count the 4-byte `DE AD BE EF` marker after the fields in that size; both are accepted.

**Rows.** Each row is a 4-byte length, one null bit per nullable field (1 = null), then the present fields in
order. Strings are a varuint byte length and the text (UTF-8 when layer flag bit 8 is set, else UTF-16).
**Only requested fields are decoded**; the others (owner names, addresses) are stepped over by their length.
All of this is done for a whole chunk of rows at once with numpy, field by field.

**Polygons.** A geometry is a varuint length, then varuints and varints (7 data bits a byte, high bit = more
to come; a varint's first byte keeps a sign bit and 6 data bits): shape type, point count, part count,
[curve count for "general" shapes with the curve flag], bounding box, the point count of each part but the
last, then each point as x and y deltas from the previous point. Z, M and curve descriptions follow the
points and are not needed. From the points, the **centroid** and **planar area** come from the shoelace
formula over all rings, holes netting out by their opposite winding, as in `shapefile`. Curves count as
straight segments between their end points. Arithmetic runs on coordinates relative to each polygon's first
point, so large map coordinates lose no precision. A polygon with zero net area gets the mean of its points;
an empty or null shape gets NaN.
"""

from __future__ import annotations

import struct
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd

LAYER_POLYGON = 4  # layer geometry type (field section flags & 0xff)
POLYGON_SHAPES = {5, 15, 19, 25, 51}  # shape types: polygon, polygon ZM / Z / M, general polygon
CURVES_FLAG = 0x20000000  # general shapes: a curve count follows the part count
ROWS_PER_CHUNK = 50_000  # bounds memory on statewide tables (mechanics only)
FIXED_WIDTH = {0: 2, 1: 4, 2: 4, 3: 8, 5: 8, 10: 16, 11: 16, 13: 8, 14: 8, 15: 8, 16: 10}
NUMERIC_DTYPE = {0: "<i2", 1: "<i4", 2: "<f4", 3: "<f8", 13: "<i8", 15: "<f8"}
DATE_TYPES = {5, 14, 16}  # float64 days since 1899-12-30 (16 adds a 2-byte UTC offset)
VARIABLE = {4, 7, 8, 12}  # string, geometry, binary, XML: varuint length then bytes
DATE_ORIGIN = pd.Timestamp("1899-12-30")


@dataclass(frozen=True)
class Field:
    name: str
    kind: int
    nullable: bool


@dataclass(frozen=True)
class Table:
    """One `.gdbtable` in the zip: its fields (OBJECTID left out, it has no row data) and geometry grid."""

    member: str
    tablx: str
    n_rows: int
    utf8: bool
    geometry_type: int
    fields: tuple[Field, ...]
    wkt: str | None = None
    xorigin: float = 0.0
    yorigin: float = 0.0
    xyscale: float = 1.0

    @property
    def null_bytes(self) -> int:
        return (sum(f.nullable for f in self.fields) + 7) // 8


def _utf16(b: bytes, p: int, n_chars: int) -> tuple[str, int]:
    return b[p : p + 2 * n_chars].decode("utf-16-le", "replace"), p + 2 * n_chars


def _varuint(b: bytes, p: int) -> tuple[int, int]:
    val = shift = 0
    while True:
        byte = b[p]
        p += 1
        val |= (byte & 0x7F) << shift
        shift += 7
        if byte < 0x80:
            return val, p


def parse_header(head: bytes, member: str, tablx: str) -> Table:
    """The 40-byte header plus the field section (bytes from the start of the file)."""
    version = struct.unpack("<i", head[:4])[0]
    if version == 3:
        n_rows = struct.unpack("<i", head[4:8])[0]
    elif version == 4:
        n_rows = struct.unpack("<q", head[16:24])[0]
    else:
        raise ValueError(f"{member}: unknown .gdbtable version {version}")
    start = struct.unpack("<q", head[32:40])[0]
    size = struct.unpack("<i", head[start : start + 4])[0]
    b = head[start + 4 : start + 4 + size]
    _, flags, n_fields = struct.unpack("<iIh", b[:10])
    has_z, has_m = bool(flags & 0x80000000), bool(flags & 0x40000000)
    p, fields, geo = 10, [], {}
    for _ in range(n_fields):
        name, p = _utf16(b, p + 1, b[p])
        _, p = _utf16(b, p + 1, b[p])  # alias
        kind = b[p]
        p += 1
        if kind == 4:
            fl = b[p + 4]
            p += 5
            if fl & 4:
                n, p = _varuint(b, p)
                p += n
        elif kind == 6:
            fl = b[p + 1]
            p += 2
        elif kind == 7:
            fl = b[p + 1]
            wkt_len = struct.unpack("<h", b[p + 2 : p + 4])[0]
            p += 4
            wkt = b[p : p + wkt_len].decode("utf-16-le", "replace").rstrip("\x00")
            p += wkt_len
            gflags = b[p]
            p += 1
            gz, gm = bool(gflags & 2), bool(gflags & 4)
            xorigin, yorigin, xyscale = struct.unpack("<3d", b[p : p + 24])
            n_doubles = 3 + 2 * gm + 2 * gz + 1 + gm + gz + 4 + 2 * has_z + 2 * has_m
            p += 8 * n_doubles + 1  # then a 0 byte and the spatial-index grid sizes
            n_grids = struct.unpack("<I", b[p : p + 4])[0]
            p += 4 + 8 * n_grids
            geo = {"wkt": None if wkt.startswith("{") else wkt, "xorigin": xorigin, "yorigin": yorigin,
                   "xyscale": xyscale}  # fmt: skip
        elif kind in (8, 10, 11, 12):
            fl = b[p + 1]
            p += 2
        elif kind == 9:
            raise ValueError(f"{member}: raster fields are not supported")
        elif kind in FIXED_WIDTH:
            fl, n = b[p + 1], b[p + 2]
            p += 3 + n
        else:
            raise ValueError(f"{member}: unknown field type {kind} ({name})")
        if kind != 6:
            fields.append(Field(name, kind, bool(fl & 1)))
    if p != size and b[p:size] != b"\xde\xad\xbe\xef":  # some writers count the DEADBEEF marker in the size
        raise ValueError(f"{member}: field section parsed to byte {p}, but its stated size is {size}")
    return Table(member, tablx, n_rows, bool(flags & 0x100), flags & 0xFF, tuple(fields), **geo)


def tables(zf: zipfile.ZipFile) -> list[Table]:
    """Every table in the zip that has a `.gdbtablx`, in name order."""
    names = {n.lower(): n for n in zf.namelist()}
    out = []
    for low, name in sorted(names.items()):
        if not low.endswith(".gdbtable") or low[:-1] + "x" not in names:
            continue
        with zf.open(name) as fh:
            head = fh.read(40)
            start = struct.unpack("<q", head[32:40])[0]
            head += fh.read(start + 4 - 40)
            head += fh.read(struct.unpack("<i", head[start : start + 4])[0])
        out.append(parse_header(head, name, names[low[:-1] + "x"]))
    return out


def catalog_names(zf: zipfile.ZipFile) -> dict[str, str]:
    """Table file stem (`a0000000b`) → table name, from the catalog `a00000001` (row N ↔ file N in hex).

    The catalog is small and has no missing 1024-row blocks, so row N is the Nth offset in its `.gdbtablx`.
    """
    found = {t.member.lower().rsplit("/", 1)[-1][:-9]: t for t in tables(zf)}
    cat = found.get("a00000001")
    if cat is None:
        return {}
    raw = zf.read(cat.tablx)
    offsets = _offsets(raw)
    fids = np.flatnonzero(offsets) + 1
    with zf.open(cat.member) as fh:
        buf = np.frombuffer(fh.read(), dtype=np.uint8)
    names = read_chunk(buf, offsets[offsets > 0], cat, {"name": "Name"}, geometry=False)["name"]
    return {f"a{fid:08x}": name for fid, name in zip(fids, names, strict=True)}


def polygon_tables(zf: zipfile.ZipFile) -> list[Table]:
    """Polygon feature tables, leaving out the geodatabase's own system tables (`GDB_*`)."""
    names = catalog_names(zf)
    out = []
    for t in tables(zf):
        stem = t.member.lower().rsplit("/", 1)[-1][:-9]
        if t.geometry_type == LAYER_POLYGON and not names.get(stem, "").upper().startswith("GDB_"):
            out.append(t)
    return out


def _offsets(raw: bytes) -> np.ndarray:
    """`.gdbtablx` bytes → one byte offset per row slot (0 = deleted), in slot order."""
    _, n_blocks, _, width = struct.unpack("<iiii", raw[:16])
    n = n_blocks * 1024
    cells = np.frombuffer(raw, dtype=np.uint8, count=n * width, offset=16).reshape(n, width).astype(np.int64)
    off = np.zeros(n, dtype=np.int64)
    for i in range(width):
        off |= cells[:, i] << (8 * i)
    return off


def row_offsets(raw: bytes) -> np.ndarray:
    """`.gdbtablx` bytes → the byte offsets of live rows, ascending."""
    off = _offsets(raw)
    return np.sort(off[off > 0])


def _skip(fh, n: int) -> None:
    while n > 0:
        got = len(fh.read(min(n, 1 << 24)))
        if got == 0:
            raise ValueError("table ended before a row offset")
        n -= got


def _varuint_at(buf: np.ndarray, pos: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Varuints starting at each position → (values, positions just after)."""
    val = np.zeros(pos.size, dtype=np.int64)
    end = pos.copy()
    todo = np.arange(pos.size)
    shift = 0
    while todo.size:
        byte = buf[end[todo]].astype(np.int64)
        val[todo] |= (byte & 0x7F) << shift
        end[todo] += 1
        todo = todo[byte >= 0x80]
        shift += 7
    return val, end


def _gather(buf: np.ndarray, start: np.ndarray, length: np.ndarray) -> np.ndarray:
    """Bytes [start, start + length) of each row as one (rows, max length) array, zero-padded."""
    width = int(length.max()) if length.size else 0
    if width == 0:
        return np.zeros((start.size, 0), dtype=np.uint8)
    k = np.arange(width)
    idx = np.minimum(start[:, None] + k, buf.size - 1)
    return np.where(k < length[:, None], buf[idx], 0).astype(np.uint8)


def _strings(buf, start, length, present, encoding) -> pd.Series:
    out = pd.Series("", index=np.arange(start.size), dtype=object)
    rows = np.flatnonzero(present & (length > 0))
    if rows.size:
        mat = _gather(buf, start[rows], length[rows])
        text = pd.Series(np.ascontiguousarray(mat).view(f"S{mat.shape[1]}").ravel())
        out.iloc[rows] = text.str.decode(encoding, errors="replace").str.strip().to_numpy()
    return out


def _fixed(buf, start, present, kind) -> pd.Series:
    width = FIXED_WIDTH[kind]
    rows = np.flatnonzero(present)
    if kind in NUMERIC_DTYPE:
        out = np.full(start.size, np.nan)
        if rows.size:
            mat = _gather(buf, start[rows], np.full(rows.size, width))
            out[rows] = np.ascontiguousarray(mat[:, : np.dtype(NUMERIC_DTYPE[kind]).itemsize]).view(
                NUMERIC_DTYPE[kind]
            )[:, 0]
        return pd.Series(out)
    if kind in DATE_TYPES:
        days = np.full(start.size, np.nan)
        if rows.size:
            mat = _gather(buf, start[rows], np.full(rows.size, 8))
            days[rows] = np.ascontiguousarray(mat).view("<f8")[:, 0]
        return pd.Series(DATE_ORIGIN + pd.to_timedelta(days, unit="D"))
    raise ValueError(f"field type {kind} cannot be requested")


def polygon_stats(blob: np.ndarray, glen: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Concatenated geometry blobs (lengths `glen`) → integer-grid centroid x, y and area for each.

    Works in the integer grid; the caller applies origin and scale.
    """
    n = glen.size
    cx, cy, area = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    if not blob.size:
        return cx, cy, area
    ends = np.flatnonzero(blob < 0x80)
    vstart = np.r_[0, ends[:-1] + 1]
    k = np.arange(blob.size) - np.repeat(vstart, ends - vstart + 1)
    u = np.add.reduceat((blob & 0x7F).astype(np.int64) << (7 * k), vstart)
    mag = (u & 0x3F) | ((u >> 7) << 6)
    s = np.where(u & 0x40, -mag, mag)
    goff = np.r_[0, np.cumsum(glen)[:-1]]
    live = np.flatnonzero(glen > 0)
    v0 = np.searchsorted(vstart, goff[live])
    n_values = np.searchsorted(vstart, goff[live] + glen[live]) - v0
    shape = u[v0]
    ok = np.isin(shape & 0xFF, [0, *POLYGON_SHAPES])  # 0: a null shape
    if not ok.all():
        bad = sorted(set((shape[~ok] & 0xFF).tolist()))
        raise ValueError(f"geometry shape types {bad} are not polygons")
    # an empty shape is its type and a zero count: too short to hold both counts and a bounding box
    full = (n_values >= 7) & (shape & 0xFF > 0)
    live, v0, shape = live[full], v0[full], shape[full]
    npts, nparts = u[v0 + 1], u[v0 + 2]
    curve = ((shape & CURVES_FLAG) != 0).astype(np.int64)
    keep = (npts > 0) & (nparts > 0)
    live, v0, npts, nparts, curve = live[keep], v0[keep], npts[keep], nparts[keep], curve[keep]
    g = live.size
    if not g:
        return cx, cy, area
    # ring sizes: listed for all parts but the last, which takes the remainder
    first_count = v0 + 7 + curve
    ring_geom = np.repeat(np.arange(g), nparts)
    rstart = np.r_[0, np.cumsum(nparts)[:-1]]
    j = np.arange(ring_geom.size) - rstart[ring_geom]
    listed = j < nparts[ring_geom] - 1
    size = np.zeros(ring_geom.size, dtype=np.int64)
    size[listed] = u[first_count[ring_geom[listed]] + j[listed]]
    last = rstart + nparts - 1
    size[last] = npts - np.bincount(ring_geom, weights=size, minlength=g).astype(np.int64)
    if (size < 0).any():
        raise ValueError("geometry part counts exceed the point count")
    # points: x, y deltas from the previous point; the first point is relative to the grid origin
    c0 = first_count + (nparts - 1)
    pstart = np.r_[0, np.cumsum(npts)[:-1]]
    pgeom = np.repeat(np.arange(g), npts)
    pidx = c0[pgeom] + 2 * (np.arange(pgeom.size) - pstart[pgeom])
    dx, dy = s[pidx].copy(), s[pidx + 1].copy()
    x0, y0 = dx[pstart].copy(), dy[pstart].copy()
    dx[pstart] = 0
    dy[pstart] = 0
    x = np.cumsum(dx)
    y = np.cumsum(dy)
    x = (x - x[pstart][pgeom]).astype(np.float64)
    y = (y - y[pstart][pgeom]).astype(np.float64)
    # each point's successor in its ring (the last point closes to the first)
    ring_first = np.r_[0, np.cumsum(size)[:-1]]
    nxt = np.arange(pgeom.size) + 1
    ring_last = ring_first + size - 1
    has = size > 0
    nxt[ring_last[has]] = ring_first[has]
    cross = x * y[nxt] - x[nxt] * y
    a = np.bincount(pgeom, weights=cross, minlength=g) / 2
    sx = np.bincount(pgeom, weights=(x + x[nxt]) * cross, minlength=g) / 6
    sy = np.bincount(pgeom, weights=(y + y[nxt]) * cross, minlength=g) / 6
    flat = a == 0
    with np.errstate(divide="ignore", invalid="ignore"):
        lx = np.where(flat, np.bincount(pgeom, weights=x, minlength=g) / npts, sx / a)
        ly = np.where(flat, np.bincount(pgeom, weights=y, minlength=g) / npts, sy / a)
    cx[live], cy[live], area[live] = x0 + lx, y0 + ly, np.abs(a)
    return cx, cy, area


def read_chunk(
    buf: np.ndarray, rel: np.ndarray, table: Table, wanted: dict[str, str], *, geometry: bool = True
) -> pd.DataFrame:
    """Row blobs at offsets `rel` in `buf` → requested fields plus x, y, area (projected units)."""
    pos = rel + 4
    flags = _gather(buf, pos, np.full(rel.size, table.null_bytes)) if table.null_bytes else None
    pos = pos + table.null_bytes
    encoding = "utf-8" if table.utf8 else "utf-16-le"
    out, bit, geom = {}, 0, None
    for f in table.fields:
        if f.nullable:
            present = ((flags[:, bit // 8] >> (bit % 8)) & 1) == 0
            bit += 1
        else:
            present = np.ones(rel.size, dtype=bool)
        rows = np.flatnonzero(present)
        if f.kind in VARIABLE:
            length = np.zeros(rel.size, dtype=np.int64)
            start = pos.copy()
            length[rows], start[rows] = _varuint_at(buf, pos[rows])
            if f.kind == 7:
                geom = (start, np.where(present, length, 0))
            elif f.name in wanted.values():
                out[f.name] = _strings(buf, start, length, present, encoding)
            pos = np.where(present, start + length, pos)
        else:
            if f.name in wanted.values():
                out[f.name] = _fixed(buf, pos, present, f.kind)
            pos = np.where(present, pos + FIXED_WIDTH[f.kind], pos)
    df = pd.DataFrame({w: out[f] for w, f in wanted.items() if f in out})
    if not geometry:
        return df
    if geom is None:
        raise ValueError(f"{table.member}: no geometry field")
    start, glen = geom
    keep = np.flatnonzero(glen > 0)
    blob = buf[np.repeat(start[keep], glen[keep]) + (np.arange(glen.sum()) - np.repeat(np.r_[0, np.cumsum(
        glen[keep])[:-1]], glen[keep]))]  # fmt: skip
    gx, gy, ga = np.full(rel.size, np.nan), np.full(rel.size, np.nan), np.full(rel.size, np.nan)
    gx[keep], gy[keep], ga[keep] = polygon_stats(blob, glen[keep])
    df["x"] = gx / table.xyscale + table.xorigin
    df["y"] = gy / table.xyscale + table.yorigin
    df["area"] = ga / table.xyscale**2
    return df


def match_fields(table: Table, wanted: list[str]) -> dict[str, str]:
    """Requested name → the table's field name: exact or its 10-character (shapefile-era) truncation,
    case-insensitive (StratMap 2019 has `stat_land_` for `stat_land_use`)."""
    low = {f.name.lower(): f.name for f in table.fields}
    out = {}
    for w in wanted:
        hit = low.get(w.lower()) or low.get(w.lower()[:10])
        if hit:
            out[w] = hit
    return out


def read_rows(
    zf: zipfile.ZipFile, table: Table, wanted: list[str], rows_per_chunk: int = ROWS_PER_CHUNK
) -> Iterator[pd.DataFrame]:
    """Chunks of the requested fields and each polygon's centroid (x, y) and area, in file order."""
    names = match_fields(table, wanted)
    offsets = row_offsets(zf.read(table.tablx))
    at = 0
    with zf.open(table.member) as fh:
        for i in range(0, offsets.size, rows_per_chunk):
            off = offsets[i : i + rows_per_chunk]
            _skip(fh, int(off[0]) - at)
            if i + rows_per_chunk < offsets.size:
                stop = int(offsets[i + rows_per_chunk])
                raw = fh.read(stop - int(off[0]))
            else:
                raw = fh.read()
                stop = int(off[0]) + len(raw)
            at = stop
            buf = np.frombuffer(raw, dtype=np.uint8)
            yield read_chunk(buf, off - off[0], table, names)
