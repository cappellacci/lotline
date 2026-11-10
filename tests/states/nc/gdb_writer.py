"""Write tiny File Geodatabase attribute tables byte by byte, for the reader tests (synthetic data only).

The layout follows the same public format description the reader cites
(https://github.com/rouault/dump_gdbtable/wiki/FGDB-Spec): a 40-byte header, the field descriptions, then
the rows (4-byte length, null bitmap, values); the `.gdbtablx` index holds a 5-byte offset per row id
(0 = deleted).
Supported field types: OBJECTID, STRING, INT32, FLOAT64, DATETIME.
"""

from __future__ import annotations

import struct
from datetime import datetime
from pathlib import Path

INT32, FLOAT64, STRING, DATETIME, OBJECTID = 1, 3, 4, 5, 6
EPOCH = datetime(1899, 12, 30)


def _utf16(s: str) -> bytes:
    return bytes([len(s)]) + s.encode("utf-16-le")


def _varuint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _field(name: str, ftype: int) -> bytes:
    head = _utf16(name) + _utf16("") + bytes([ftype])
    if ftype == OBJECTID:
        return head + bytes([4, 2])
    if ftype == STRING:
        return head + struct.pack("<i", 255) + bytes([1])  # nullable, no default
    if ftype not in (INT32, FLOAT64, DATETIME):
        return head + bytes([0, 0])  # only the type code matters to the reader's rejection tests
    width = {INT32: 4, FLOAT64: 8, DATETIME: 8}[ftype]
    return head + bytes([width, 1])


def _value(ftype: int, v: object) -> bytes:
    if ftype == INT32:
        return struct.pack("<i", v)
    if ftype == FLOAT64:
        return struct.pack("<d", v)
    if ftype == DATETIME:
        return struct.pack("<d", (v - EPOCH).total_seconds() / 86400)
    raw = str(v).encode("utf-8")
    return _varuint(len(raw)) + raw


def write_table(gdb: Path, number: int, fields: list[tuple[str, int]], rows: list[dict | None]) -> None:
    """`rows[i]` is row id i+1 (None = a deleted row); missing or None values are nulls."""
    gdb.mkdir(parents=True, exist_ok=True)
    body = b"".join(_field(n, t) for n, t in fields)
    fdesc = struct.pack("<iih", 4, 0, len(fields)) + body
    fdesc = struct.pack("<i", len(fdesc)) + fdesc
    nullable = [n for n, t in fields if t != OBJECTID]
    blobs, offsets = [], []
    pos = 40 + len(fdesc)
    for row in rows:
        if row is None:
            offsets.append(0)
            continue
        bits = bytearray((len(nullable) + 7) // 8)
        vals = b""
        for i, (name, ftype) in enumerate(f for f in fields if f[1] != OBJECTID):
            v = row.get(name)
            if v is None:
                bits[i // 8] |= 1 << (i % 8)
            else:
                vals += _value(ftype, v)
        blob = bytes(bits) + vals
        offsets.append(pos)
        blobs.append(struct.pack("<i", len(blob)) + blob)
        pos += 4 + len(blob)
    data = b"".join(blobs)
    size = 40 + len(fdesc) + len(data)
    header = struct.pack("<4i", 3, sum(r is not None for r in rows), 0, 5) + struct.pack(
        "<iiqq", 0, 0, size, 40
    )
    (gdb / f"a{number:08x}.gdbtable").write_bytes(header + fdesc + data)
    blocks = max(1, -(-len(rows) // 1024))
    tablx = struct.pack("<4i", 3, blocks, len(rows), 5) + b"".join(o.to_bytes(5, "little") for o in offsets)
    (gdb / f"a{number:08x}.gdbtablx").write_bytes(tablx)


def write_gdb(gdb: Path, tables: dict[str, tuple[list[tuple[str, int]], list[dict | None]]]) -> None:
    """A geodatabase with a system catalog (table 1) and `tables` stored from table 3 on (2 is deleted)."""
    catalog: list[dict | None] = [{"Name": "GDB_SystemCatalog"}, None]
    for number, (name, (fields, rows)) in enumerate(tables.items(), start=3):
        catalog.append({"Name": name})
        write_table(gdb, number, fields, rows)
    write_table(gdb, 1, [("ID", OBJECTID), ("Name", STRING)], catalog)
