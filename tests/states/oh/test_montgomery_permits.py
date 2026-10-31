"""Montgomery CAMA permit adapter on synthetic records (no network, no real data).

Checks the methodology in the module docstring: the fixed-width fields read (no address fields), each named
ADU rule on a hand-written note, one ADU per parcel in two years, placement through the roll with the
taxing-district fallback, and that load() runs the holdout filter.
"""

import zipfile

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.oh import montgomery_permits as mp
from lotline.schemas import assert_conforms
from lotline.validation import holdout

DAYTON, TROTWOOD = "3921000", "3977504"


def _record(parid, num, date, why, note, amount="0") -> bytes:
    buf = bytearray(b" " * 423)
    for (start, _), value in zip(
        mp.FIELDS.values(),
        [parid, num, date, why, amount, note[:80], note[80:160], note[160:240]],
        strict=True,
    ):
        buf[start - 1 : start - 1 + len(value)] = value.encode()
    buf[73:84] = b"123 MAIN ST"  # an address field (Adrno/Adrstr): must never be read
    return bytes(buf) + b"\r\n"


def _zip(path, records, folder=""):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(folder + "PERMIT.DAT", b"".join(records) + b"\r\n")
    return path


@pytest.mark.parametrize(
    ("note", "why", "num", "expected"),
    [
        ("CONSTRUCT DETACHED GARAGE WITH AN ACCESSORY DWELLING UNIT", "DET GAR", "BLD2024R00381", True),
        ("NEW ACCESSORY GARAGE W/ADU ABOVE", "ADDN", "BLD2022R00321", True),
        # CREATING_WHY: an addition permit needs no creation word
        ("IN LAW SUITE ADDITION", "ADDN", "Z20250257", True),
        ("IN LAW SUITE ADDITION", "REMODEL", "Z1", False),
        # TRADE_WHY: trade permits are never ADUs
        ("ROOM ADDITION MOTHER-IN-LAW SUITE; SEE: BLD20-01367", "ELECTRIC", "ELE20-02067", False),
        ("REPLACE GAS FURNACE AND A/C IN CARRIAGE HOUSE", "AC", "MEC21-00553", False),
        # ADDITION_TO_EXISTING, GARAGE_WORDS, MULTIFAMILY
        ("CONSTRUCT 410 SF 1 STORY ADDITION TO 2 STORY CARRIAGE HOUSE", "ADDN", "BLD2025R00075", False),
        (
            "A NEW 3,656 SQUARE FOOT TWO-STORY CARRIAGE HOUSE COMPRISED OF A FOUR-CAR GARAGE",
            "DET GAR",
            "B1",
            False,
        ),
        (
            "PARKVIEW APARTMENTS; BLD 40; CARRIAGE HOUSE; 2 UNITS; NEW MULTI-FAMILY HOUSING",
            "GAR ADDN",
            "B2",
            False,
        ),
        # Franklin's rules: existing work
        ("REMODEL 2 STORY DET CARRIAGE HOUSE", "REMODEL", "BLD2022R00169", False),
        ("", "DWLG", "B3", False),
    ],
)
def test_named_adu_rules(note, why, num, expected):
    assert mp.describes_new_adu(mp.fp.clean_text(note), why, num) is expected


RECORDS = [
    _record(
        "R72 00001 0001",
        "BLD2021R00204",
        "02-AUG-21",
        "DEMO",
        "GARAGE AND MOTHER IN LAW SUITE. DEMOLISH EXISTING DETACHED GARAGE AND REBUILD NEW GARAGE AND "
        "NEW 2ND FL MOTHER IN LAW SUITE",
    ),
    # the same parcel 400 days later: a re-issued permit, not a new ADU
    _record(
        "R72 00001 0001",
        "BLD2022R00999",
        "06-SEP-22",
        "DET GAR",
        "CONSTRUCT DETACHED GARAGE WITH ACCESSORY DWELLING UNIT",
    ),
    # not in the roll: placed by its district (R72 → Dayton)
    _record(
        "R72 99999 0099",
        "BLD2024R00381",
        "12-DEC-24",
        "DET GAR",
        "CONSTRUCT DETACHED GARAGE WITH AN ACCESSORY DWELLING UNIT",
        "85000",
    ),
    _record("K40 00001 0001", "BLDR24-0492", "19-JUN-24", "ADDN", "MOTHER IN LAW SUITE ROOM ADDITION"),
    _record("R72 00001 0002", "ELE20-00001", "01-JAN-20", "ELECTRIC", "WIRE NEW CARRIAGE HOUSE"),
]
PARCELS = pd.DataFrame(
    {
        "parcel_id": ["39113R72 00001 0001", "39113R72 00001 0002", "39113K40 00001 0001"],
        "county_geoid": "39113",
        "jurisdiction_geoid": [DAYTON, DAYTON, TROTWOOD],
    }
)


def test_read_permits_reads_named_fields_only(tmp_path):
    raw = mp.read_permits(_zip(tmp_path / "c.zip", RECORDS + RECORDS[:1], folder="Cama_Files_20260930\\"))
    assert list(raw.columns) == list(mp.FIELDS) and len(raw) == len(RECORDS)  # the exact repeat is dropped
    assert not raw.apply(lambda c: c.astype(str).str.contains("MAIN ST")).any().any()


def test_build_places_and_dedupes(tmp_path):
    out = mp.build(mp.read_permits(_zip(tmp_path / "c.zip", RECORDS)), PARCELS).set_index("permit_id")
    assert_conforms(out.reset_index(), "permits")
    assert list(out.index) == ["MONT-BLD2021R00204", "MONT-BLDR24-0492", "MONT-BLD2024R00381"]
    assert out.loc["MONT-BLD2024R00381", "jurisdiction_geoid"] == DAYTON  # district fallback
    assert out.loc["MONT-BLD2024R00381", "valuation_usd"] == 85000
    assert out.loc["MONT-BLDR24-0492", "jurisdiction_geoid"] == TROTWOOD
    assert out.loc["MONT-BLD2021R00204", "adu_type"] == "detached"
    assert (out["building_type_std"] == "ADU").all() and (out["units_new"] == 1).all()


def test_load_applies_holdout_filter(tmp_path, monkeypatch):
    path = _zip(tmp_path / "c.zip", RECORDS)

    class Store:
        def read(self, state, table):
            return PARCELS

    monkeypatch.setattr(mp, "registered_file", lambda store: path)
    calls = []
    real_apply = holdout.apply

    def spy(df, state, **kw):
        calls.append(kw)
        return real_apply(df, state, **kw)

    monkeypatch.setattr(mp.holdout, "apply", spy)
    out = mp.load("OH", Store())
    assert calls and calls[0]["geoid_col"] == "jurisdiction_geoid"
    assert_conforms(out, "permits")


def test_registered_as_oh_source():
    assert "montgomery_permits" in registry.sources_for("OH")
