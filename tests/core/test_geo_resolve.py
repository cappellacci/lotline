"""WS-SCALE task 3: the one jurisdiction resolver (`geo.resolve`) every adapter uses. Synthetic polygons.

Layout: place 3700001 is the square x 0-10, township 3700000002 (a county subdivision) the square x 10-20,
both y 0-10, in county 37001. Known jurisdictions: the place, the township and the county remainder.
"""

import numpy as np
import pandas as pd
import pytest

from lotline import geo

PLACE = pd.DataFrame({"geoid": ["3700001"], "rings": [[[[0, 0], [10, 0], [10, 10], [0, 10]]]]})
TOWNSHIP = pd.DataFrame({"geoid": ["3700000002"], "rings": [[[[10, 0], [20, 0], [20, 10], [10, 10]]]]})
KNOWN = {"3700001", "3700000002", "37001"}
ALIASES = {"ALPHA CITY": "3700001"}


def _resolve(lon, lat, names):
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    index = pd.RangeIndex(len(lon))
    place = pd.Series(geo.assign(lon, lat, PLACE), index=index)
    township = pd.Series(geo.assign(lon, lat, TOWNSHIP), index=index)
    alias = pd.Series(names, index=index, dtype="string").map(ALIASES)
    county = pd.Series("37001", index=index)
    steps = [("place", place), ("township", township), ("alias", alias), ("county", county, False)]
    return geo.resolve(steps, KNOWN)


def test_point_in_a_place_a_township_and_outside_both():
    geoid, how = _resolve([5, 15, 30], [5, 5, 5], [None] * 3)
    assert list(geoid) == ["3700001", "3700000002", "37001"]
    assert list(how) == ["place", "township", "county"]


def test_point_on_the_shared_border_goes_east_by_the_half_open_rule():
    """x = 10 is the place's east edge and the township's west edge: a ray towards +x crosses only the
    township's east edge (x = 20 > 10), so the point is in the township and never in both."""
    geoid, how = _resolve([10], [5], [None])
    assert (geoid[0], how[0]) == ("3700000002", "township")


def test_alias_hit_when_there_is_no_point():
    geoid, how = _resolve([np.nan, np.nan], [np.nan, np.nan], ["ALPHA CITY", "NOWHERE"])
    assert list(geoid) == ["3700001", "37001"] and list(how) == ["alias", "county"]


def test_an_unknown_geoid_falls_through_unless_the_step_keeps_it():
    found = pd.Series(["3799999", "3799999"])
    county = pd.Series(["37001", None])
    geoid, how = geo.resolve([("place", found), ("county", county)], KNOWN, otherwise="none")
    assert geoid.tolist() == ["37001", pd.NA] and how.tolist() == ["county", "none"]
    geoid, how = geo.resolve([("place", found), ("kept", found, False)], KNOWN)
    assert geoid.tolist() == ["3799999"] * 2 and how.tolist() == ["kept"] * 2


def test_first_step_wins_and_index_is_kept():
    a = pd.Series(["37001", None], index=[7, 9])
    b = pd.Series(["3700001", "3700001"], index=[7, 9])
    geoid, how = geo.resolve([("a", a), ("b", b)], KNOWN)
    assert (
        list(geoid.index) == [7, 9] and geoid.tolist() == ["37001", "3700001"] and how.tolist() == ["a", "b"]
    )


def test_no_steps_is_an_error():
    with pytest.raises(ValueError):
        geo.resolve([], KNOWN)


@pytest.mark.parametrize("state", ["nc", "or", "tx"])
def test_aliases_files_are_well_formed(state):
    """WS-SCALE: one aliases file per state; each (source, field, raw) maps to one GEOID of that state."""
    from lotline.config import CONFIG_DIR, load_state

    df = pd.read_csv(CONFIG_DIR / "crosswalks" / f"{state}_aliases.csv", dtype=str, keep_default_na=False)
    assert list(df.columns) == ["source", "field", "raw", "geoid", "notes", "source_url"]
    assert not df.duplicated(["source", "field", "raw"]).any()
    fips = load_state(state.upper()).fips
    assert df["geoid"].str.fullmatch(fips + r"(\d{3}|\d{5}|\d{8})").all()
    assert df["source_url"].str.startswith("https://").all()


def test_aliases_lookup_by_source_and_field():
    assert geo.aliases("NC", "cary_permits", "jurisdiction") == {"TC": "3710740", "CC": "3710740"}
    assert geo.aliases("OR", "mwvcog_permits", "JURISD") == {
        "SALEM": "4164900",
        "KEIZER": "4138500",
        "TURNER": "4175150",
    }
    with pytest.raises(KeyError):
        geo.aliases("NC", "no_such_source")
