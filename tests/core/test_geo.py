"""Point assignment: even-odd point-in-polygon, first-match assignment, the place-or-township rule, and the
TIGERweb boundary loader against a fake server. Synthetic polygons only; no network."""

from urllib.parse import parse_qs, urlparse

import httpx
import numpy as np
import pandas as pd
import pytest

from lotline import geo
from lotline.adapters.national import tiger_boundaries
from lotline.io import arcgis
from lotline.io.store import DataStore

SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
HOLE = [[3, 3], [3, 7], [7, 7], [7, 3], [3, 3]]
ISLAND = [[20, 0], [24, 0], [24, 4], [20, 4]]  # left open on purpose: rings are closed if needed


def _reference(px, py, rings):
    """Plain even-odd ray cast, one point and one edge at a time (same half-open rule)."""
    inside = False
    for ring in rings:
        pts = ring if ring[0] == ring[-1] else [*ring, ring[0]]
        for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:], strict=True):
            if (y1 > py) != (y2 > py):
                if x1 + (py - y1) * (x2 - x1) / (y2 - y1) > px:
                    inside = not inside
    return inside


def test_square_inside_and_outside():
    got = geo.points_in_rings([5, 15, -1, 5, 9.99], [5, 5, 5, 11, 0.01], [SQUARE])
    assert got.tolist() == [True, False, False, False, True]


def test_hole_is_outside_and_enclave_inside_hole_is_inside():
    x, y = [1, 5, 4], [1, 5, 4]
    assert geo.points_in_rings(x, y, [SQUARE, HOLE]).tolist() == [True, False, False]
    enclave = [[4.5, 4.5], [5.5, 4.5], [5.5, 5.5], [4.5, 5.5], [4.5, 4.5]]  # an island inside the hole
    assert geo.points_in_rings(x, y, [SQUARE, HOLE, enclave]).tolist() == [True, True, False]


def test_multipolygon_of_two_disjoint_rings():
    got = geo.points_in_rings([5, 22, 15, 22], [5, 2, 2, 5], [SQUARE, ISLAND])
    assert got.tolist() == [True, True, False, False]


def test_boundary_points_follow_the_half_open_rule():
    # Bottom and left edges count as inside, top and right as outside; a shared vertex is counted once.
    x = [5, 5, 0, 10, 0, 10]
    y = [0, 10, 5, 5, 0, 10]
    assert geo.points_in_rings(x, y, [SQUARE]).tolist() == [True, False, True, False, True, False]
    # A ray through a vertex shared by two edges (the diamond's left tip) crosses once, not twice.
    diamond = [[0, 5], [5, 0], [10, 5], [5, 10], [0, 5]]
    assert geo.points_in_rings([-1, 5, 2], [5, 5, 5], [diamond]).tolist() == [False, True, True]


def test_nan_and_empty_inputs():
    assert geo.points_in_rings([np.nan, 5], [5, np.nan], [SQUARE]).tolist() == [False, False]
    assert geo.points_in_rings([], [], [SQUARE]).tolist() == []
    assert geo.points_in_rings([5], [5], []).tolist() == [False]


def test_matches_reference_on_random_points_and_a_concave_polygon(monkeypatch):
    rng = np.random.default_rng(7)
    # A 40-point star (concave) with a square hole and a separate triangle; vertices on shared y values too.
    t = np.linspace(0, 2 * np.pi, 41)[:-1]
    r = np.where(np.arange(40) % 2 == 0, 10.0, 4.0)
    star = np.round(np.c_[r * np.cos(t), r * np.sin(t)], 1).tolist()
    rings = [star, [[-1, -1], [-1, 1], [1, 1], [1, -1], [-1, -1]], [[12, -2], [16, -2], [14, 3]]]
    x = np.round(rng.uniform(-12, 18, 2000), 1)  # rounded so many points sit on vertex y values
    y = np.round(rng.uniform(-12, 12, 2000), 1)
    expected = [_reference(a, b, rings) for a, b in zip(x, y, strict=True)]
    monkeypatch.setattr(geo, "PAIR_CHUNK", 97)  # force many small chunks: same answer
    assert geo.points_in_rings(x, y, rings).tolist() == expected
    assert 0 < sum(expected) < 2000


def test_assign_first_match_and_missing_coordinates():
    polys = pd.DataFrame(
        {
            "geoid": ["A", "B", "C"],
            "rings": [[SQUARE, HOLE], [ISLAND], [[[0, 0], [30, 0], [30, 30], [0, 30]]]],
        }
    )
    lon = [5, 22, 1, 5, 25, np.nan, 50]
    lat = [5, 2, 1, 15, 25, 1, 50]
    assert geo.assign(lon, lat, polys).tolist() == ["C", "B", "A", "C", "C", None, None]
    assert geo.assign(lon, lat, polys.iloc[:2]).tolist() == [None, "B", "A", None, None, None, None]
    assert geo.assign([1.0], [1.0], polys.iloc[:0]).tolist() == [None]


@pytest.fixture
def fake_boundaries(monkeypatch):
    place = pd.DataFrame({"geoid": ["3900001"], "rings": [[SQUARE]]})
    cousub = pd.DataFrame({"geoid": ["3904900001", "3904900002"], "rings": [[ISLAND], [SQUARE]]})
    calls = []

    def fake(state, store, level, *, refresh=False):
        calls.append((state, level))
        return {"place": place, "cousub": cousub}[level]

    monkeypatch.setattr(tiger_boundaries, "load_polygons", fake)
    return calls


def test_place_or_township_in_a_township_state(fake_boundaries):
    lon = pd.Series([5, 22, 50, None], index=[10, 11, 12, 13])
    lat = pd.Series([5, 2, 50, 1], index=[10, 11, 12, 13])
    got = geo.place_or_township(lon, lat, "OH", store=None)
    assert got.index.tolist() == [10, 11, 12, 13]
    # The place wins over the township holding it; outside both: None (the caller uses the county).
    assert got.tolist() == ["3900001", "3904900001", None, None]
    assert fake_boundaries == [("OH", "place"), ("OH", "cousub")]


def test_place_or_township_in_a_county_permit_state(fake_boundaries):
    got = geo.place_or_township([5, 22], [5, 2], "NC", store=None)
    assert got.tolist() == ["3900001", None]  # NC townships don't permit: never a county subdivision
    assert fake_boundaries == [("NC", "place")]


def test_load_polygons_from_a_fake_tigerweb(tmp_path, monkeypatch):
    feats = [
        {"attributes": {"OBJECTID": 2, "GEOID": "3918000", "NAME": "Columbus city", "FUNCSTAT": "A"},
         "geometry": {"rings": [SQUARE, HOLE]}},
        {"attributes": {"OBJECTID": 1, "GEOID": "3901000", "NAME": "Ada village", "FUNCSTAT": "A"},
         "geometry": {"rings": [ISLAND]}},
    ]  # fmt: skip
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        q = {k: v[0] for k, v in parse_qs(urlparse(str(request.url)).query).items()}
        if not request.url.path.endswith("/query"):
            return httpx.Response(
                200,
                json={
                    "maxRecordCount": 100000,
                    "geometryType": "esriGeometryPolygon",
                    "objectIdField": "OBJECTID",
                    "advancedQueryCapabilities": {"supportsPagination": True, "supportsOrderBy": True},
                },
            )
        off, size = int(q["resultOffset"]), int(q["resultRecordCount"])
        assert q["where"] == "STATE='39'" and q["outSR"] == "4326" and size == tiger_boundaries.PAGE_SIZE
        return httpx.Response(200, json={"features": feats[off : off + size]})

    monkeypatch.setattr(arcgis, "client", lambda **kw: httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(arcgis.time, "sleep", lambda s: None)
    store = DataStore(tmp_path)
    df = tiger_boundaries.load_polygons("OH", store, "place")
    assert df["geoid"].tolist() == ["3901000", "3918000"]
    assert df.columns.tolist() == ["geoid", "name", "funcstat", "rings"]
    assert df["rings"].iloc[1] == [SQUARE, HOLE]
    assert seen[0].startswith(f"{tiger_boundaries.SERVICE}/18")
    assert (tmp_path / "raw/census_tigerweb_acs2025/acs2025/place_39").is_dir()
    with pytest.raises(ValueError, match="level"):
        tiger_boundaries.load_polygons("OH", store, "cdp")
