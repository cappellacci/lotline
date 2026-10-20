"""Charlotte UDO Zoning Translation adapter on synthetic data (no network, no real data).

Checks the module docstring: the window guard runs before any download, parcels from taxpid, areas,
pre-UDO zoning, jurisdictions, and the snapshot holdout keeping a pre-window Charlotte roll.
"""

import datetime as dt

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.nc import clt_udo_translation as clt
from lotline.io import DataStore
from lotline.schemas import assert_conforms
from lotline.validation import holdout


def meta(when: dt.datetime) -> dict:
    return {"editingInfo": {"dataLastEditDate": int(when.replace(tzinfo=dt.UTC).timestamp() * 1000)}}


MAY_31 = dt.datetime(2023, 5, 31, 18, 29, 59)

RAW = pd.DataFrame(
    {
        "taxpid": ["01101101", "01101102", "01101102", "02202201", " "],
        "OldZoneDes": ["R-3", "R-5(CD)", "R-5(CD)", "UR-2(CD)", "R-4"],
        "ZoneDes": ["N1-A", "N1-C", "N1-C", "N2-B", "N1-B"],
        "Shape__Area": [10_000.0, 6_000.0, 500.0, 0.0, 9_000.0],
        "lon": [-80.84, -80.85, -80.85, -80.70, -80.80],
        "lat": [35.22, 35.23, 35.23, 35.40, 35.20],
    }
)


def test_window_opens_from_config():
    assert clt.window_opens() == pd.Timestamp("2023-06-01")


def test_window_guard():
    opens = pd.Timestamp("2023-06-01")
    assert clt.check_window(meta(MAY_31), opens) == pd.Timestamp(MAY_31)
    with pytest.raises(ValueError, match="must not be fetched"):
        clt.check_window(meta(dt.datetime(2023, 6, 1, 0, 0, 1)), opens)
    with pytest.raises(ValueError, match="dataLastEditDate"):
        clt.check_window({}, opens)


def test_build_parcels():
    out = clt.build(RAW, pd.Timestamp(MAY_31)).set_index("parcel_id")
    assert len(out) == 3  # blank taxpid dropped, split polygon merged
    assert out.loc["3711901101102", "lot_sqft"] == 6_500.0
    assert out.loc["3711901101102", "zoning_raw"] == "R-5(CD)"
    assert pd.isna(out.loc["3711902202201", "lot_sqft"])  # zero area is unknown
    assert (out.land_use_std == "UNKNOWN").all()
    assert (out.vintage_date == pd.Timestamp("2023-05-31")).all() and (out.vintage == 2023).all()


def test_load_guard_runs_before_download(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(clt, "layer_description", lambda: meta(dt.datetime(2024, 1, 5)))
    monkeypatch.setattr(clt, "download", lambda store, refresh=False: calls.append("download"))
    with pytest.raises(ValueError, match="must not be fetched"):
        clt.load("NC", DataStore(tmp_path))
    assert calls == []


def test_load_keeps_pre_window_charlotte_roll(tmp_path, monkeypatch):
    monkeypatch.setattr(clt, "layer_description", lambda: meta(MAY_31))
    monkeypatch.setattr(clt, "download", lambda store, refresh=False: RAW.copy())
    places = {-80.84: "3712000", -80.85: "3712000", -80.70: None}
    monkeypatch.setattr(
        clt,
        "assign_jurisdictions",
        lambda df, state, store: df.assign(
            jurisdiction_geoid=df["lon"].map(places).fillna(clt.COUNTY).astype("string")
        ),
    )
    out = clt.load("NC", DataStore(tmp_path))
    assert (out.jurisdiction_geoid == "3712000").sum() == 2  # before the window: not held out
    assert set(out.jurisdiction_geoid) == {"3712000", "37119"}
    assert_conforms(out, "parcels")
    holdout.assert_no_leak(out, "parcels", "NC")


def test_no_personal_fields_requested():
    assert not set(clt.OUT_FIELDS) & clt.PERSONAL


def test_registered():
    assert registry.sources_for("NC")["clt_udo_translation"].module.TABLE == "parcels"
