"""TIGERweb layer IDs are checked against the layer's name and vintage group (review item 7, synthetic)."""

import json

import pandas as pd
import pytest

from lotline.adapters.national import tiger_boundaries as tb
from lotline.io.store import DataStore


def test_the_expected_layers_pass():
    tb.check_layer({"name": "Incorporated Places", "parentLayer": {"id": 13, "name": "ACS 2025"}}, "place")
    tb.check_layer({"name": "County Subdivisions", "parentLayer": {"id": 13, "name": "ACS 2025"}}, "cousub")


@pytest.mark.parametrize(
    "meta",
    [
        {"name": "Incorporated Places", "parentLayer": {"id": 13, "name": "ACS 2026"}},  # next vintage
        {"name": "Census Designated Places", "parentLayer": {"id": 13, "name": "ACS 2025"}},  # shifted ID
        {"name": "Incorporated Places"},  # no group at all
    ],
)
def test_a_renumbered_service_is_refused(meta):
    with pytest.raises(ValueError, match="renumbered"):
        tb.check_layer(meta, "place")


def test_load_polygons_checks_the_saved_layer_description(tmp_path, monkeypatch):
    store = DataStore(tmp_path)
    monkeypatch.setattr(tb, "load_state", lambda st: type("S", (), {"fips": "39"})())
    monkeypatch.setattr(tb, "download_layer", lambda *a, **k: pd.DataFrame())
    folder = store.raw(tb.SOURCE, tb.VINTAGE) / "place_39"
    folder.mkdir(parents=True)
    meta = {"name": "Incorporated Places", "parentLayer": {"name": "ACS 2026"}}
    (folder / "layer.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="renumbered"):
        tb.load_polygons("OH", store, "place")
