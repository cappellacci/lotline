"""Met Council permits adapter on a synthetic 20-row fixture (no network, no real data)."""

import json
from pathlib import Path

import httpx
import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.mn import metc_permits as mp
from lotline.io.store import DataStore
from lotline.schemas import assert_conforms
from lotline.validation import holdout

FIX = Path(__file__).parent / "fixtures" / "metc_permits_synthetic.csv"
PLACES = ["2743000", "2758000", "2705554", "2717288", "2710918", "2759998", "2771032"]


def _raw() -> pd.DataFrame:
    return pd.read_csv(FIX, dtype=str).drop(columns="note")


def _jurisdictions() -> pd.DataFrame:
    rows = [{"geoid": g, "kind": "place"} for g in PLACES] + [{"geoid": "2700340166", "kind": "township"}]
    return pd.DataFrame(rows)


@pytest.fixture
def permits() -> pd.DataFrame:
    return mp.to_permits(_raw(), _jurisdictions(), "MN").set_index("permit_id")


def test_conforms_and_is_registered(permits):
    assert_conforms(permits.reset_index(), "permits")
    assert "metc_permits" in registry.sources_for("MN")


def test_held_out_st_paul_rows_disappear(permits):
    stpaul = permits[permits.jurisdiction_geoid == "2758000"]
    assert sorted(stpaul.issue_year) == [2022, 2023]  # 2024 and 2025 rows removed
    assert not {"metc-1012", "metc-1013"} & set(permits.index)
    assert len(permits) == 18
    holdout.assert_no_leak(permits.reset_index(), "permits", "MN")


def test_year_only_dates(permits):
    assert permits.issue_date.isna().all()
    assert (permits.date_precision == "year").all()
    assert permits.loc["metc-1001", "issue_year"] == 2018


def test_types_never_split_and_unknowns_marked(permits):
    assert permits.loc["metc-1003", "building_type_std"] == "DTQ"
    assert permits.loc["metc-1003", "units_new"] == 3
    assert permits.loc["metc-1004", "building_type_std"] == "MF5"
    assert permits.loc["metc-1002", "building_type_std"] == "ADU"
    assert permits.loc["metc-1002", "adu_type"] == "unknown"
    assert permits.loc["metc-1019", ["building_type_std", "type_confidence"]].tolist() == [
        "UNKNOWN",
        "unknown",
    ]
    assert (permits.drop("metc-1019").type_confidence == "high").all()
    assert permits.loc["metc-1003", "permit_class_raw"] == "DTQ:NU"


def test_ledger_units(permits):
    def units(pid):
        r = permits.loc[pid]
        return r.units_new, r.units_removed, r.units_confidence

    assert units("metc-1001") == (1, 0, "reported")  # new
    assert units("metc-1005") == (0, 1, "reported")  # removed from stock
    assert units("metc-1006") == (2, 0, "reported")  # converted from SFD into DTQ
    assert units("metc-1007") == (0, 1, "reported")  # the matching SFD loss
    assert units("metc-1008") == (0, 0, "derived")  # remodel: no unit change
    assert units("metc-1018") == (0, 1, "reported")  # moved out


def test_unknown_units_are_null_not_zero(permits):
    th = permits.loc["metc-1009"]
    assert pd.isna(th.units_new) and pd.isna(th.units_removed) and th.units_confidence == "unknown"
    odd = permits.loc["metc-1020"]  # unrecognised permit code
    assert pd.isna(odd.units_new) and pd.isna(odd.is_demolition) and pd.isna(odd.is_conversion)


def test_demolition_and_conversion_flags(permits):
    assert permits.loc["metc-1005", ["is_demolition", "is_conversion"]].tolist() == [True, False]
    assert permits.loc["metc-1006", ["is_demolition", "is_conversion"]].tolist() == [False, True]
    assert permits.loc["metc-1001", ["is_demolition", "is_conversion"]].tolist() == [False, False]


def test_jurisdiction_geoids_place_or_township(permits):
    assert permits.loc["metc-1001", "jurisdiction_geoid"] == "2743000"
    assert permits.loc["metc-1014", "jurisdiction_geoid"] == "2705554"
    assert permits.loc["metc-1015", "jurisdiction_geoid"] == "2700340166"  # not a place → county subdivision


def test_pins_are_county_fips_plus_local(permits):
    assert permits.loc["metc-1001", "parcel_id"] == "270532102724410003"  # '053' prefix stripped
    assert permits.loc["metc-1002", "parcel_id"] == "270531502724430043"
    assert permits.loc["metc-1016", "parcel_id"] == "27037015450001100"  # punctuation removed
    assert permits.loc["metc-1017", "parcel_id"] == "27019010110110"  # Carver: 9-digit local after prefix
    assert permits.loc["metc-1018", "parcel_id"] == "27139200670550"
    assert pd.isna(permits.loc["metc-1015", "parcel_id"])  # '0' placeholder
    assert pd.isna(permits.loc["metc-1003", "parcel_id"])


def test_tenure_and_value(permits):
    assert permits.loc["metc-1017", "tenure"] == "cooperative"
    assert pd.isna(permits.loc["metc-1018", "tenure"])
    assert permits.loc["metc-1004", "valuation_usd"] == 25_000_000


def test_no_personal_fields_requested():
    assert not {"ADDRESS", "NAME", "ZIP_CODE", "ZIP_PLUS_4", "NOTES"} & set(mp.FIELDS)


def test_load_through_pager(tmp_path):
    """load() pages the layer through the IO layer (manifest entries) and needs the jurisdictions table."""
    store = DataStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        mp.load("MN", store)
    jur = store.processed("MN", "jurisdictions")
    jur.mkdir(parents=True)
    _jurisdictions().to_parquet(jur / "jurisdictions.parquet")

    raw = _raw()
    feats = [
        {"attributes": {k: (None if pd.isna(v) else v) for k, v in r.items()}} for r in raw.to_dict("records")
    ]
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        if not request.url.path.endswith("/query"):
            meta = {"maxRecordCount": 2000, "objectIdField": "OBJECTID"}
            meta["advancedQueryCapabilities"] = {"supportsPagination": True, "supportsOrderBy": True}
            return httpx.Response(200, json=meta)
        off = int(request.url.params["resultOffset"])
        return httpx.Response(200, json={"features": feats[off:]})

    out = mp.load("MN", store, http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert len(out) == 18
    assert all(r.source == mp.SOURCE for r in store.manifest())
    asked = seen[1].params["outFields"].split(",")
    assert asked == mp.FIELDS
    json.dumps(mp.PROVENANCE)  # provenance is plain data
