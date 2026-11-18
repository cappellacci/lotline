"""The two crosswalk formats (WS-SCALE task 7): every file in `config/crosswalks/` follows one of them or is a
listed exception, and the reader rejects what the formats forbid."""

from __future__ import annotations

import csv

import pytest

from lotline.adapters import crosswalks
from lotline.config import CONFIG_DIR

FOLDER = CONFIG_DIR / "crosswalks"
# Not crosswalks: per-state registries (one row per county or place, own columns) and one-off inputs.
NOT_CROSSWALKS = {
    "nc_land_use_counties.csv",  # registry: which crosswalk and fields each NC county uses
    "mn_mngeo_counties.csv",  # registry: MnGeo county acquisition status
    "nc_land_use_wake_jurisdictions.csv",  # registry: Wake towns and their roll shares
    "nc_clt_udo_n1.csv",  # V5 Charlotte: pre-UDO district -> UDO district
    "or_hb2001_metro.csv",  # Oregon Metro list for the MM route
    "or_metro_cities.csv",  # read by scripts/dev/or_state_reform_rows.py
}


def _header(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return tuple(next(csv.reader(fh)))


def _kind(path):
    head = _header(path)
    if head[: len(crosswalks.LAND_USE)] == crosswalks.LAND_USE:
        return "land_use"
    if head[: len(crosswalks.BUILDING_TYPE)] == crosswalks.BUILDING_TYPE:
        return "building_type"
    if path.name.endswith("_aliases.csv"):
        return "aliases"
    return None


FILES = sorted(FOLDER.glob("*.csv"))


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_every_file_follows_a_format_or_is_listed(path):
    kind = _kind(path)
    if kind is None:
        assert path.name in NOT_CROSSWALKS, f"{path.name}: header {_header(path)} is in neither format"
        return
    assert path.name not in NOT_CROSSWALKS, f"{path.name} follows a format; drop it from NOT_CROSSWALKS"
    if kind != "aliases":
        assert crosswalks.read(path, kind)


def test_listed_exceptions_exist():
    assert {p.name for p in FILES} >= NOT_CROSSWALKS


def test_two_formats_are_counted():
    kinds = [_kind(p) for p in FILES]
    assert kinds.count("land_use") >= 59 and kinds.count("building_type") >= 5


def _write(tmp_path, text):
    p = tmp_path / "x.csv"
    p.write_text(text)
    return p


LU_HEAD = "field,code,description,land_use_std,notes,source_url"


def test_reader_accepts_codes_and_patterns(tmp_path):
    p = _write(tmp_path, LU_HEAD + ",pattern\nUSE,510,Res,SF_DETACHED,,,\nUSE,,,DUPLEX,,,^2 units$\n")
    rows = crosswalks.read(p, "land_use")
    assert [r["land_use_std"] for r in rows] == ["SF_DETACHED", "DUPLEX"]
    assert crosswalks.by_code(rows)["510"]["description"] == "Res"


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("code,field,description,land_use_std,notes,source_url\nUSE,1,,SF_DETACHED,,\n", "header must start"),
        (LU_HEAD + ",zoning\nUSE,1,,SF_DETACHED,,,R1\n", "unknown columns"),
        (LU_HEAD + "\nUSE,1,,single family,,\n", "not in the schema vocabulary"),
    ],
)
def test_reader_rejects(tmp_path, text, match):
    with pytest.raises(crosswalks.CrosswalkError, match=match):
        crosswalks.read(_write(tmp_path, text), "land_use")


def test_building_type_rejects_unknown_type(tmp_path):
    head = ",".join(crosswalks.BUILDING_TYPE)
    p = _write(tmp_path, head + "\nOcc,One Family,,DUPLEX,dwelling,1,,\n")
    with pytest.raises(crosswalks.CrosswalkError, match="building_type_std"):
        crosswalks.read(p, "building_type")
