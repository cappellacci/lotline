"""Minneapolis CCS permits adapter on a synthetic fixture (no network, no real data)."""

import json
from pathlib import Path

import httpx
import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.mn import mpls_permits as mp
from lotline.io.store import DataStore
from lotline.schemas import assert_conforms
from lotline.validation import holdout

FIX = Path(__file__).parent / "fixtures" / "mpls_permits_synthetic.csv"


def _raw() -> pd.DataFrame:
    df = pd.read_csv(FIX, dtype=str, keep_default_na=False).drop(columns="note")
    for col in ("OBJECTID", "permit_Value", "totalFees", "issueDate", "completeDate"):
        df[col] = pd.to_numeric(df[col].replace("", None))
    return df.replace({"": None})


@pytest.fixture
def permits() -> pd.DataFrame:
    return mp.to_permits(_raw()).set_index("permit_id")


def test_conforms_and_is_registered(permits):
    assert_conforms(permits.reset_index(), "permits")
    assert "mpls_permits" in registry.sources_for("MN")
    holdout.assert_no_leak(permits.reset_index(), "permits", "MN")
    assert (permits.jurisdiction_geoid == "2743000").all()


def test_personal_fields_never_requested_nor_kept(permits):
    assert not mp.PERSONAL & set(mp.FIELDS)
    assert "comments" not in permits.columns
    text = permits.to_csv()
    assert not any(s in text for s in ("Testperson", "Fake Street", "Faketown"))


def test_one_row_per_permit_units_counted_once(permits):
    assert "mpls-PLUM9022" not in permits.index  # plumbing permits are not building permits
    # 26 rows - 1 plumbing - 1 repeat of a multi-parcel permit + 1 ADU row for a new house built with an ADU
    assert len(permits) == 25
    multi = permits.loc["mpls-BLDG9019"]
    assert multi.units_new == 6 and multi.building_type_std == "U5_6"
    assert multi.parcel_id == "270533333333333333"  # lowest APN of the two parcels


def test_empty_units_are_null_not_zero(permits):
    row = permits.loc["mpls-BLDG9015"]
    assert pd.isna(row.units_new) and pd.isna(row.units_removed)
    assert row.units_confidence == "unknown"
    assert row.building_type_std == "MF5"


def test_dates_are_local_days(permits):
    assert (permits.date_precision == "day").all()
    assert permits.loc["mpls-BLDG9001", "issue_date"] == pd.Timestamp("2019-05-01")
    late = permits.loc["mpls-BLDG9021"]  # 03:00 UTC on Jan 1 is 9 p.m. Dec 31 in Minneapolis
    assert late.issue_date == pd.Timestamp("2019-12-31") and late.issue_year == 2019


def test_final_date_only_for_passed_final_inspection(permits):
    done = permits.loc["mpls-BLDG9001"]
    assert done.final_date == pd.Timestamp("2020-01-10") and done.final_date_type == "final_inspection"
    cancelled = permits.loc["mpls-BLDG9020"]
    assert pd.isna(cancelled.final_date) and pd.isna(cancelled.final_date_type)
    assert cancelled.permit_class_raw == "Res:SFD:New:Cancelled"


def test_building_types(permits):
    def t(pid):
        return permits.loc[pid, ["building_type_std", "type_confidence"]].tolist()

    assert t("mpls-BLDG9001") == ["SFD", "high"]
    assert t("mpls-BLDG9011") == ["U7P", "high"]  # 48 new units
    assert t("mpls-BLDG9012") == ["U3_4", "high"]
    assert t("mpls-BLDG9013") == ["U3_4", "high"]  # TFD (two- or three-family) with 3 units
    assert t("mpls-BLDG9014") == ["DTQ", "high"]  # TFD, no count
    assert t("mpls-BLDG9017") == ["OTHER", "high"]


def test_adu_inferred_only_with_evidence(permits):
    adus = permits[permits.building_type_std == "ADU"]
    assert sorted(adus.index) == [
        "mpls-BLDG9002",  # garage with ADU above, on a house
        "mpls-BLDG9005",  # accessory structure, "accessory to a SFD"
        "mpls-BLDG9006",  # accessory structure, the APN has a house permit
        "mpls-BLDG9008",  # basement ADU conversion
        "mpls-BLDG9010",  # legalized existing ADU
        "mpls-BLDG9023-ADU",  # new house built with a basement ADU: its own ADU row
    ]
    assert (adus.type_confidence == "inferred").all()
    assert adus.adu_type.to_dict() == {
        "mpls-BLDG9002": "detached",
        "mpls-BLDG9005": "detached",
        "mpls-BLDG9006": "detached",
        "mpls-BLDG9008": "internal_conversion",
        "mpls-BLDG9010": "detached",
        "mpls-BLDG9023-ADU": "internal_conversion",
    }
    # An ADU permit adds a home: the city's 0 becomes 1, inferred (Ben, 2026-10-14); a reported 1 stays.
    assert permits.loc["mpls-BLDG9002", ["units_new", "units_confidence"]].tolist() == [1, "inferred"]
    assert permits.loc["mpls-BLDG9005", ["units_new", "units_confidence"]].tolist() == [1, "reported"]
    # New house with an ADU: house row keeps its reported 1 unit; the ADU row adds 1, inferred, no money.
    assert permits.loc["mpls-BLDG9023", ["building_type_std", "units_new"]].tolist() == ["SFD", 1]
    adu_row = permits.loc["mpls-BLDG9023-ADU"]
    assert (adu_row.units_new, adu_row.units_confidence, adu_row.type_confidence) == (
        1,
        "inferred",
        "inferred",
    )
    assert pd.isna(adu_row.valuation_usd) and adu_row.parcel_id == permits.loc["mpls-BLDG9023", "parcel_id"]
    # Not ADUs themselves: negated, future, the new house (its ADU has its own row), work on an existing ADU.
    for pid in ("mpls-BLDG9003", "mpls-BLDG9004", "mpls-BLDG9023", "mpls-BLDG9009", "mpls-BLDG9024"):
        assert permits.loc[pid, "building_type_std"] == "SFD", pid
    assert permits.loc["mpls-BLDG9025", "building_type_std"] == "DTQ"
    assert permits.adu_type.notna().sum() == 6


def test_demolitions_and_conversions(permits):
    sfd = permits.loc["mpls-BLDG9016"]
    assert sfd.is_demolition and sfd.units_removed == 1 and sfd.units_new == 0
    assert sfd.units_confidence == "derived"
    comm = permits.loc["mpls-BLDG9017"]
    assert comm.is_demolition and pd.isna(comm.units_removed) and comm.units_confidence == "unknown"
    duplex = permits.loc["mpls-BLDG9018"]
    assert duplex.is_conversion and (duplex.units_new, duplex.units_removed) == (2, 1)
    assert permits.loc["mpls-BLDG9008", "is_conversion"]
    assert not permits.loc["mpls-BLDG9001", "is_demolition"]
    assert not permits.loc["mpls-BLDG9001", "is_conversion"]


def test_value_and_fees(permits):
    row = permits.loc["mpls-BLDG9001"]
    assert row.valuation_usd == 350_000 and row.fees_paid_usd == 7500.5


def test_load_through_pager(tmp_path):
    """load() pages the layer through the IO layer, asking only for FIELDS on building permits."""
    store = DataStore(tmp_path)
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
    assert len(out) == 25
    assert all(r.source == mp.SOURCE for r in store.manifest())
    query = seen[1].params
    assert query["outFields"].split(",") == mp.FIELDS
    assert query["where"] == "permitType IN ('Res','Commercial','Wrecking')"
    assert not set(query["outFields"].split(",")) & mp.PERSONAL
    json.dumps(mp.PROVENANCE)  # provenance is plain data


def test_house_that_counted_its_adu_gives_one_unit_to_the_adu_row():
    """New SFD reporting 2 units for "house + ADU": house 1 (derived), ADU row 1 (inferred). Total 2."""
    raw = _raw()
    row = raw[raw.permitNumber == "BLDG9023"].copy()
    row["permitNumber"], row["OBJECTID"], row["dwellingUnitsNew"] = "BLDG9099", 9099, "2"
    out = mp.to_permits(pd.concat([raw, row], ignore_index=True)).set_index("permit_id")
    assert out.loc["mpls-BLDG9099", ["units_new", "units_confidence"]].tolist() == [1, "derived"]
    assert out.loc["mpls-BLDG9099-ADU", "units_new"] == 1
    assert out.loc[["mpls-BLDG9099", "mpls-BLDG9099-ADU"], "units_new"].sum() == 2
