"""Standard-library File Geodatabase reader on hand-built tables (no real data).

Checks the module docstring: tables found through the system catalog, nulls from the null bitmap, deleted
rows skipped, strings / int32 / float64 / dates decoded, `columns=` limits what is returned, and unsupported
inputs raise instead of guessing.
"""

import struct
from datetime import datetime

import pandas as pd
import pytest

from lotline.adapters.states.nc import filegdb

from .gdb_writer import DATETIME, FLOAT64, INT32, OBJECTID, STRING, write_gdb, write_table

FIELDS = [("OBJECTID", OBJECTID), ("Num", INT32), ("Descr", STRING), ("Cost", FLOAT64), ("When", DATETIME)]
ROWS = [
    {"Num": 201510001, "Descr": "New ADU (750 sf)", "Cost": 125000.5, "When": datetime(2015, 6, 1, 12)},
    None,  # deleted row id 2
    {"Num": 201510003, "Descr": None, "Cost": None, "When": None},
    {"Num": -7, "Descr": "é" * 200, "Cost": 0.0, "When": datetime(1899, 12, 30)},  # 2-byte varuint length
]


@pytest.fixture
def gdb(tmp_path):
    path = tmp_path / "t.gdb"
    write_gdb(path, {"Permits": (FIELDS, ROWS)})
    return path


def test_catalog_names_tables_by_row_id(gdb):
    assert filegdb.list_tables(gdb) == {"GDB_SystemCatalog": 1, "Permits": 3}


def test_values_nulls_and_deleted_rows(gdb):
    df = filegdb.read_table(gdb, "Permits")
    assert list(df.columns) == ["OBJECTID", "Num", "Descr", "Cost", "When"]
    assert df["OBJECTID"].tolist() == [1, 3, 4]  # row 2 deleted; ids keep their position
    assert df.loc[0, "Num"] == 201510001 and df.loc[2, "Num"] == -7
    assert df.loc[0, "Descr"] == "New ADU (750 sf)" and df.loc[2, "Descr"] == "é" * 200
    assert df.loc[0, "Cost"] == 125000.5
    assert abs(df.loc[0, "When"] - pd.Timestamp("2015-06-01 12:00")) < pd.Timedelta(seconds=1)
    assert df.loc[2, "When"] == pd.Timestamp("1899-12-30")
    assert df.loc[1, ["Descr", "Cost", "When"]].isna().all()


def test_columns_limits_output(gdb):
    df = filegdb.read_table(gdb, "Permits", ["Num", "Cost"])
    assert list(df.columns) == ["Num", "Cost"] and len(df) == 3
    with pytest.raises(KeyError):
        filegdb.read_table(gdb, "Permits", ["Address"])
    with pytest.raises(KeyError):
        filegdb.read_table(gdb, "Nope")


def test_varuint():
    assert filegdb._varuint(bytes([0x05]), 0) == (5, 1)
    assert filegdb._varuint(bytes([0x90, 0x03]), 0) == (400, 2)  # 0x10 + 3 * 128


def test_unsupported_inputs_raise(tmp_path):
    gdb = tmp_path / "g.gdb"
    write_table(gdb, 5, [("OBJECTID", OBJECTID), ("Shape", 7)], [])  # a geometry field
    with pytest.raises(filegdb.FileGDBError, match="geometry"):
        filegdb._read(gdb, 5, None)
    table = gdb / "a00000005.gdbtable"
    table.write_bytes(struct.pack("<i", 2) + table.read_bytes()[4:])  # ArcGIS 9 magic
    with pytest.raises(filegdb.FileGDBError, match="version"):
        filegdb._read(gdb, 5, None)
    write_table(gdb, 6, [("OBJECTID", OBJECTID)], [{}])
    tablx = gdb / "a00000006.gdbtablx"
    tablx.write_bytes(struct.pack("<4i", 3, 0, 2000, 5) + tablx.read_bytes()[16:])  # sparse index
    with pytest.raises(filegdb.FileGDBError, match="sparse"):
        filegdb._read(gdb, 6, None)
