"""Read attribute tables from an Esri File Geodatabase (`.gdb` folder) with the standard library only.

Chapel Hill publishes its legacy permits only as a zipped File Geodatabase, and Lotline has no GDAL-based
reader (adding one is a new dependency). This module reads the **non-spatial tables** of a File Geodatabase,
which is all the Chapel Hill adapter needs. It follows the public description of the format written by Even
Rouault for GDAL's OpenFileGDB driver (https://github.com/rouault/dump_gdbtable/wiki/FGDB-Spec); no code was
copied from GDAL.

How the format is read:

- `a00000001.gdbtable` is the system catalog: row *n* names the table stored in `a{n:08x}.gdbtable`.
- A `.gdbtable` file starts with a 40-byte header (magic 3 for ArcGIS 10+ files, the offset of the field
  descriptions at byte 32), then the field descriptions (name, alias, type and per-type extras).
- The `.gdbtablx` index file holds one offset per row id (0 = deleted row); each row is a 4-byte length,
  a null bitmap over the nullable fields (bit set = null), then the values in field order. The OBJECTID is
  the row's position in the index and is not stored in the row.
- Value encodings: int16/int32/int64 little-endian, float32/float64, dates as float64 days since
  1899-12-30, strings and XML as a variable-length unsigned integer byte count then UTF-8, GUIDs 16 bytes.

**Limits (it raises instead of guessing):** tables with a geometry or raster field, sparse `.gdbtablx`
indexes (tables with large gaps in their row ids) and pre-10 (ArcGIS 9) files are not supported.
`read_table(..., columns=[...])` decodes only the named columns, so fields that hold personal data are skipped
without being kept.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

__all__ = ["FileGDBError", "list_tables", "read_table"]

# Field type codes (FGDB spec).
INT16, INT32, FLOAT32, FLOAT64, STRING, DATETIME, OBJECTID, GEOMETRY, BINARY, RASTER, GUID, GLOBALID, XML = (
    range(13)
)
INT64, DATE_ONLY, TIME_ONLY, DATETIME_OFFSET = 13, 14, 15, 16
FIXED = {INT16: 2, INT32: 4, FLOAT32: 4, FLOAT64: 8, DATETIME: 8, GUID: 16, GLOBALID: 16, INT64: 8,
         DATE_ONLY: 8, TIME_ONLY: 8, DATETIME_OFFSET: 10}  # fmt: skip
EPOCH = pd.Timestamp("1899-12-30")


class FileGDBError(ValueError):
    """The file is not a File Geodatabase table this reader supports."""


@dataclass(frozen=True)
class Field:
    name: str
    type: int
    nullable: bool


def _varuint(buf: bytes, pos: int) -> tuple[int, int]:
    """Variable-length unsigned integer: 7 bits per byte, low bits first, high bit = more bytes follow."""
    value = shift = 0
    while True:
        b = buf[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not b & 0x80:
            return value, pos
        shift += 7


def _utf16(buf: bytes, pos: int) -> tuple[str, int]:
    n = buf[pos]
    pos += 1
    return buf[pos : pos + 2 * n].decode("utf-16-le"), pos + 2 * n


def _fields(buf: bytes) -> tuple[list[Field], int]:
    """Field descriptions → (fields, offset of the first byte after them)."""
    magic, _rows, _maxlen, _five = struct.unpack_from("<4i", buf, 0)
    if magic != 3:
        raise FileGDBError(f"unsupported .gdbtable version (magic {magic}); only ArcGIS 10+ files are read")
    (start,) = struct.unpack_from("<q", buf, 32)
    header_size, version, _flags = struct.unpack_from("<3i", buf, start)
    if version not in (3, 4, 6):
        raise FileGDBError(f"unsupported field-description version {version}")
    (count,) = struct.unpack_from("<h", buf, start + 12)
    pos = start + 14
    fields = []
    for _ in range(count):
        name, pos = _utf16(buf, pos)
        _alias, pos = _utf16(buf, pos)
        ftype = buf[pos]
        pos += 1
        if ftype in (GEOMETRY, RASTER):
            raise FileGDBError(f"field {name!r} is a geometry/raster field; only attribute tables are read")
        if ftype == STRING:
            pos += 4  # max length
            flag = buf[pos]
            pos += 1
            if flag & 4:
                n, pos = _varuint(buf, pos)
                pos += n
        elif ftype == OBJECTID:
            pos += 1
            flag = buf[pos]
            pos += 1
        elif ftype in (BINARY, XML):
            pos += 1
            flag = buf[pos]
            pos += 1
        elif ftype in FIXED:
            pos += 1  # width
            flag = buf[pos]
            pos += 1
            if flag & 4:
                n = buf[pos]
                pos += 1 + n
        else:
            raise FileGDBError(f"field {name!r} has unknown type code {ftype}")
        fields.append(Field(name, ftype, bool(flag & 1) and ftype != OBJECTID))
    end = start + 4 + header_size
    return fields, end


def _offsets(tablx: bytes) -> list[int]:
    """Row offsets from the `.gdbtablx` index (0 for a deleted row id)."""
    _three, blocks, rows, size = struct.unpack_from("<4i", tablx, 0)
    if blocks * 1024 < rows:
        raise FileGDBError("sparse .gdbtablx index (row-id gaps) is not supported")
    out = []
    for i in range(rows):
        p = 16 + i * size
        out.append(int.from_bytes(tablx[p : p + size], "little"))
    return out


def _decode(buf: bytes, pos: int, ftype: int) -> tuple[object, int]:
    if ftype == INT16:
        return struct.unpack_from("<h", buf, pos)[0], pos + 2
    if ftype == INT32:
        return struct.unpack_from("<i", buf, pos)[0], pos + 4
    if ftype == INT64:
        return struct.unpack_from("<q", buf, pos)[0], pos + 8
    if ftype == FLOAT32:
        return struct.unpack_from("<f", buf, pos)[0], pos + 4
    if ftype in (FLOAT64, DATETIME, DATE_ONLY, TIME_ONLY):
        days = struct.unpack_from("<d", buf, pos)[0]
        value = days if ftype == FLOAT64 else EPOCH + pd.to_timedelta(days, unit="D")
        return value, pos + 8
    if ftype == DATETIME_OFFSET:
        days = struct.unpack_from("<d", buf, pos)[0]
        return EPOCH + pd.to_timedelta(days, unit="D"), pos + 10
    if ftype in (STRING, XML):
        n, pos = _varuint(buf, pos)
        return buf[pos : pos + n].decode("utf-8", errors="replace"), pos + n
    if ftype == BINARY:
        n, pos = _varuint(buf, pos)
        return bytes(buf[pos : pos + n]), pos + n
    if ftype in (GUID, GLOBALID):
        return bytes(buf[pos : pos + 16]).hex(), pos + 16
    raise FileGDBError(f"unknown type code {ftype}")


def _read(gdb: Path, number: int, columns: list[str] | None, *, oid: bool = False) -> pd.DataFrame:
    """Rows of table `number` (deleted rows skipped); `oid` adds the row id as column `_oid`."""
    stem = gdb / f"a{number:08x}"
    buf = (stem.with_suffix(".gdbtable")).read_bytes()
    fields, _ = _fields(buf)
    names = [f.name for f in fields]
    if columns is not None:
        missing = sorted(set(columns) - set(names))
        if missing:
            raise KeyError(f"columns not in table: {missing}")
    keep = set(names if columns is None else columns)
    nullable = [f for f in fields if f.nullable]
    nbytes = (len(nullable) + 7) // 8
    rows: list[dict] = []
    for rid, off in enumerate(_offsets(stem.with_suffix(".gdbtablx").read_bytes()), start=1):
        if off == 0:
            continue
        pos = off + 4  # row length
        bitmap = buf[pos : pos + nbytes]
        pos += nbytes
        bit = 0
        row: dict = {"_oid": rid} if oid else {}
        for f in fields:
            if f.type == OBJECTID:
                if f.name in keep:
                    row[f.name] = rid
                continue
            if f.nullable:
                is_null = bool(bitmap[bit // 8] >> (bit % 8) & 1)
                bit += 1
                if is_null:
                    if f.name in keep:
                        row[f.name] = None
                    continue
            value, pos = _decode(buf, pos, f.type)
            if f.name in keep:
                row[f.name] = value
        rows.append(row)
    return pd.DataFrame(rows, columns=(["_oid"] if oid else []) + [n for n in names if n in keep])


def list_tables(gdb: Path) -> dict[str, int]:
    """Table name → table number, from the system catalog (`a00000001`)."""
    catalog = _read(Path(gdb), 1, ["Name"], oid=True)
    return {
        name: int(i)
        for i, name in zip(catalog["_oid"], catalog["Name"], strict=True)
        if isinstance(name, str)
    }


def read_table(gdb: Path, table: str, columns: list[str] | None = None) -> pd.DataFrame:
    """One attribute table as a DataFrame (all columns, or only `columns`, in the table's field order)."""
    gdb = Path(gdb)
    tables = list_tables(gdb)
    if table not in tables:
        raise KeyError(f"{table!r} not in {gdb.name}; tables: {sorted(tables)}")
    return _read(gdb, tables[table], columns)
