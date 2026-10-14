"""2020 Census splits of places across counties and townships, with the Census responses faked."""

import pandas as pd
import pytest

from lotline.adapters.national import geoparts
from lotline.io.store import DataStore

PBC = pd.DataFrame(
    {  # place-by-county code file rows (OH)
        "STATEFP": ["39"] * 4,
        "PLACEFP": ["00100", "00100", "00200", "00300"],
        "COUNTYFP": ["001", "003", "001", "001"],
    }
)
SUBS = pd.DataFrame(
    {  # county-subdivision code file rows: 00100 is its own subdivision (C5), 00200 isn't
        "STATEFP": ["39"] * 3,
        "COUNTYFP": ["001"] * 3,
        "COUSUBFP": ["00100", "10000", "20000"],
        "CLASSFP": ["C5", "T1", "T1"],
    }
)


@pytest.fixture
def fake_census(monkeypatch):
    def codes(name, store, refresh):
        return PBC if "place_by_county" in name else SUBS

    def parts(url, name, store, refresh, key):
        if "county%20(or%20part)" in url:  # place 3900100 spans counties 001 and 003
            return [
                ["H1_001N", "state", "place", "county (or part)"],
                ["600", "39", "00100", "001"],
                ["300", "39", "00100", "003"],
            ]
        if "subdivision:10000" in url:  # dependent village 00200 lies in township 10000 (40 HU) ...
            return [
                ["H1_001N", "state", "county", "county subdivision", "place/remainder (or part)"],
                ["40", "39", "001", "10000", "00200"],
                ["500", "39", "001", "10000", "99999"],
            ]
        return [
            [
                "H1_001N",
                "state",
                "county",
                "county subdivision",
                "place/remainder (or part)",
            ],  # ... and 20000
            ["10", "39", "001", "20000", "00200"],
            ["700", "39", "001", "20000", "99999"],
        ]

    monkeypatch.setattr(geoparts, "_codes", codes)
    monkeypatch.setattr(geoparts, "_parts", parts)
    monkeypatch.setattr(geoparts, "api_key", lambda: "K")


def test_county_shares_split_multi_county_places_by_2020_housing(fake_census, tmp_path):
    out = geoparts.county_shares("39", ["3900100", "3900200", "3900300"], DataStore(tmp_path))
    by = out.set_index(["place_geoid", "county_geoid"])["share"]
    assert by[("3900100", "39001")] == pytest.approx(2 / 3) and by[("3900100", "39003")] == pytest.approx(
        1 / 3
    )
    assert by[("3900200", "39001")] == 1.0  # single-county place: no API call needed
    assert out.groupby("place_geoid")["share"].sum().tolist() == pytest.approx([1.0, 1.0, 1.0])


def test_township_shares_only_for_places_that_are_not_their_own_subdivision(fake_census, tmp_path):
    out = geoparts.township_shares(
        "39", ["3900100", "3900200"], ["3900110000", "3900120000"], DataStore(tmp_path)
    )
    by = out.set_index(["place_geoid", "township_geoid"])["share"]
    assert set(out["place_geoid"]) == {"3900200"}  # 3900100 is its own subdivision: never inside a township
    assert by[("3900200", "3900110000")] == pytest.approx(0.8) and by[
        ("3900200", "3900120000")
    ] == pytest.approx(0.2)


def test_no_dependent_places_means_no_requests(fake_census, tmp_path, monkeypatch):
    monkeypatch.setattr(geoparts, "_parts", lambda *a, **k: pytest.fail("no request expected"))
    out = geoparts.township_shares("39", ["3900100"], ["3900110000"], DataStore(tmp_path))
    assert out.empty
