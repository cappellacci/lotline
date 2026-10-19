"""TCAD parcels adapter on a tiny synthetic fixed-width export (no network, no real data).

Checks the module docstring's rules: fields read by position, owner fields never read, City of Austin
placement by taxing-unit name, state code → state category → land_use_std, lot size from land segments
(else legal acreage), earliest year built, appraisal values, one row per property and roll (highest
supplement), real property only, the register-first error, and that load() runs the snapshot holdout filter.
"""

import zipfile

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.tx import tcad_parcels as tp
from lotline.io import DataStore
from lotline.schemas import assert_conforms
from lotline.validation import holdout

OWNER = "JANE Q PUBLIC"
OWNER_SPAN = (609, 70)  # py_owner_name in the layout: must never reach the output
MAIL_SPAN = (694, 60)  # py_addr_line1


def record(fields: dict, values: dict, extra: dict | None = None, width: int = 9000) -> str:
    line = [" "] * width
    for name, value in values.items():
        start, n = fields[name]
        text = str(value)[:n].ljust(n)
        line[start - 1 : start - 1 + n] = text
    for (start, n), value in (extra or {}).items():
        line[start - 1 : start - 1 + n] = str(value)[:n].ljust(n)
    return "".join(line).rstrip()


def prop(pid, geo, *, yr=2026, sup=0, ptype="R", acreage="", land=(0, 100000), imp=(250000, 0), hs="T",
         imp_cd="A1", land_cd="A1"):  # fmt: skip
    values = {
        "prop_id": pid, "prop_type_cd": ptype, "prop_val_yr": yr, "sup_num": sup, "geo_id": geo,
        "legal_acreage": acreage, "land_hstd_val": land[0], "land_non_hstd_val": land[1],
        "imprv_hstd_val": imp[0], "imprv_non_hstd_val": imp[1], "hs_exempt": hs,
        "imprv_state_cd": imp_cd, "land_state_cd": land_cd,
    }  # fmt: skip
    return record(tp.PROP_FIELDS, values, {OWNER_SPAN: OWNER, MAIL_SPAN: "123 PRIVATE LN"})


def build_zip(path, *, entity="CITY OF AUSTIN"):
    props = [
        prop(1, "0101010101"),  # SFD, Austin
        prop(2, "0202020202", imp_cd="", land_cd="C1", imp=(0, 0), acreage="00000000002500"),  # vacant
        prop(3, "0303030303", imp_cd="B2", hs="F"),  # duplex code → category B
        prop(4, "0404040404"),  # not in Austin (no city entity)
        prop(5, "0505050505", ptype="P"),  # business personal property
        prop(6, "0606060606", sup=0, imp=(100, 0)),
        prop(6, "0606060606", sup=3, imp=(300000, 0)),  # later supplement wins
        prop(7, "0707070707", imp_cd="ZZ9"),  # unknown code
    ]
    ent = [record(tp.PROP_ENT_FIELDS, {"prop_id": p, "entity_name": e})
           for p, e in [(1, entity), (1, "AUSTIN ISD"), (2, entity), (3, entity), (5, entity), (6, entity),
                        (7, entity), (4, "TRAVIS COUNTY")]]  # fmt: skip
    codes = [record(tp.STATE_CD_FIELDS, {"state_cd": c, "ptd_state_cd": p}, width=125)
             for c, p in [("A1", "A"), ("B2", "B"), ("C1", "C1")]]  # fmt: skip
    land = [record(tp.LAND_DET_FIELDS, v, width=200) for v in [
        {"prop_id": 1, "size_square_feet": "6000"}, {"prop_id": 1, "size_square_feet": "1500.00"},
        {"prop_id": 3, "size_acres": "00000000002000"},  # 0.2 acres, implied 4 decimals
    ]]  # fmt: skip
    imp = [record(tp.IMP_DET_FIELDS, {"prop_id": p, "yr_built": y}, width=622)
           for p, y in [(1, 1952), (1, 1998), (1, 0), (3, 2019), (6, 1700)]]  # fmt: skip
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("PROP.TXT", "\r\n".join(props) + "\r\n")
        zf.writestr("PROP_ENT.TXT", "\n".join(ent))
        zf.writestr("STATE_CD.TXT", "\n".join(codes))
        zf.writestr("LAND_DET.TXT", "\n".join(land))
        zf.writestr("IMP_DET.TXT", "\n".join(imp))
    return path


@pytest.fixture
def roll(tmp_path) -> pd.DataFrame:
    path = build_zip(tmp_path / "tcad.zip")
    return tp.read_roll(path, vintage_date=pd.Timestamp("2026-07-18")).set_index("parcel_id")


def test_conforms_and_places_only_austin_real_property(roll):
    assert_conforms(roll.reset_index(), "parcels")
    geo_ids = ["0101010101", "0202020202", "0303030303", "0606060606", "0707070707"]
    assert set(roll.index) == {"48453" + g for g in geo_ids}
    assert (roll.jurisdiction_geoid == "4805000").all()
    assert (roll.vintage == 2026).all() and (roll.vintage_date == pd.Timestamp("2026-07-18")).all()
    assert (roll.value_basis == "appraisal").all() and "last_sale_price" not in roll.columns


def test_owner_fields_never_read(roll):
    text = roll.astype(str).to_string()
    assert OWNER not in text and "PRIVATE" not in text
    spans = [tp.PROP_FIELDS[k] for k in tp.PROP_FIELDS]
    for start, n in spans:  # no listed field overlaps the owner name or mailing address
        for o_start, o_n in (OWNER_SPAN, MAIL_SPAN):
            assert start + n <= o_start or o_start + o_n <= start


def test_land_use_via_state_category(roll):
    assert roll.loc["484530101010101", "land_use_std"] == "SF_DETACHED"
    assert roll.loc["484530101010101", "land_use_raw"] == "A1"
    assert (
        roll.loc["484530202020202", "land_use_std"] == "VACANT_RESIDENTIAL"
    )  # land code when no improvement
    assert roll.loc["484530303030303", "land_use_std"] == "OTHER"  # category B: 2+ units, count unknown
    assert roll.loc["484530707070707", "land_use_std"] == "UNKNOWN"


@pytest.mark.parametrize(
    "code, expected",
    [("A1", "SF_DETACHED"), ("M1", "MOBILE_HOME"), ("F1", "COMMERCIAL"), ("D1", "AGRICULTURAL"),
     ("X", "UNKNOWN"), (None, "UNKNOWN")],
)  # fmt: skip
def test_land_use_falls_back_to_code_prefix(code, expected):
    assert tp.land_use(code, {}, tp.load_land_use_crosswalk()) == expected


def test_lot_size_year_built_values(roll):
    sfd = roll.loc["484530101010101"]
    assert sfd.lot_sqft == 7500.0  # 6,000 + 1,500 sq ft segments
    assert sfd.year_built == 1952  # earliest detail year; 0 ignored
    assert (sfd.land_value, sfd.bldg_value, sfd.homestead) == (100000.0, 250000.0, True)
    vacant = roll.loc["484530202020202"]
    assert vacant.lot_sqft == pytest.approx(0.25 * 43560)  # legal acreage, 4 implied decimals
    assert pd.isna(vacant.year_built)
    duplex = roll.loc["484530303030303"]
    assert duplex.lot_sqft == pytest.approx(0.2 * 43560) and duplex.year_built == 2019
    assert duplex.homestead == False  # noqa: E712
    assert pd.isna(roll.loc["484530606060606", "year_built"])  # 1700 is outside the plausible range
    assert roll.units.isna().all()


def test_latest_supplement_wins(roll):
    assert roll.loc["484530606060606", "bldg_value"] == 300000.0


@pytest.mark.parametrize(
    "text, field, expected",
    [
        ("00000000002500", "legal_acreage", 0.25),
        ("0.2500", "legal_acreage", 0.25),
        ("000000250000", "land_hstd_val", 250000.0),
        ("", "x", None),
        ("abc", "x", None),
    ],
)
def test_number(text, field, expected):
    assert tp.number(text, field) == expected


def test_unknown_entity_name_fails_loudly(tmp_path):
    path = build_zip(tmp_path / "tcad.zip", entity="CITY OF AUSTIN TX")
    with pytest.raises(ValueError, match="CITY OF AUSTIN TX"):
        tp.read_roll(path)


def test_load_without_registered_file_explains_register(tmp_path):
    with pytest.raises(FileNotFoundError, match="lotline manifest register"):
        tp.load("TX", DataStore(tmp_path))


def test_load_reads_registered_zip_and_applies_snapshot_holdout(tmp_path, monkeypatch):
    store = DataStore(tmp_path / "data")
    src = build_zip(tmp_path / "2026 Certified Export.zip")
    store.register(src, source="tcad", url=tp.LANDING_URL, license=tp.LICENSE, vintage="2026-07-18")
    calls = []
    real_apply = holdout.apply

    def spy(df, state, **kw):
        calls.append(kw)
        return real_apply(df, state, **kw)

    monkeypatch.setattr(tp.holdout, "apply", spy)
    out = tp.load("TX", store)
    assert calls and calls[0]["snapshot"] is True and calls[0]["year_col"] == "vintage"
    assert len(out) == 5 and (out.vintage_date == pd.Timestamp("2026-07-18")).all()
    assert_conforms(out, "parcels")
    holdout.assert_no_leak(out, "parcels", "TX")


def test_crosswalks_are_sourced():
    lu = pd.read_csv(tp.LAND_USE_CROSSWALK, dtype=str)
    assert lu.source_url.str.startswith("https://").all() and lu.ptad_code.is_unique
    from lotline.schemas import LAND_USES

    assert lu.land_use_std.isin(LAND_USES).all()
    ent = pd.read_csv(tp.ENTITY_CROSSWALK, dtype=str)
    assert ent.jurisdiction_geoid.str.fullmatch(r"48\d{5}").all()


def test_registered_as_tx_source():
    assert "tcad_parcels" in registry.sources_for("TX")
