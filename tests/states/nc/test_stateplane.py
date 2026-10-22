"""NC State Plane (EPSG:2264) inverse projection, checked on its defining points and by round trip."""

import pandas as pd
import pytest

from lotline.adapters.states.nc import stateplane as sp

# EPSG rounds the false easting to 609,601.22 m; 2,000,000 ftUS is 609,601.2192 m, so the origin is off by
# about 1 mm (1e-8 degrees). 1e-7 degrees is about 1 cm.
TOL = 1e-7


def test_origin_is_the_false_easting_on_the_latitude_of_origin():
    lon, lat = sp.to_lonlat(pd.Series([2_000_000.0]), pd.Series([0.0]))
    assert lon.iloc[0] == pytest.approx(-79.0, abs=TOL)
    assert lat.iloc[0] == pytest.approx(33.75, abs=TOL)


def test_central_meridian_keeps_longitude():
    lon, _ = sp.to_lonlat(pd.Series([2_000_000.0] * 3), pd.Series([100_000.0, 500_000.0, 900_000.0]))
    assert lon.tolist() == pytest.approx([-79.0] * 3, abs=TOL)


def test_round_trip_across_north_carolina():
    lon = pd.Series([-84.3, -80.84, -78.64, -75.5, None])  # Murphy, Charlotte, Raleigh, Outer Banks, missing
    lat = pd.Series([35.09, 35.23, 35.78, 35.9, None])
    x, y = sp.to_stateplane(lon, lat)
    lon2, lat2 = sp.to_lonlat(x, y)
    assert lon2.iloc[:4].tolist() == pytest.approx(lon.iloc[:4].tolist(), abs=1e-9)
    assert lat2.iloc[:4].tolist() == pytest.approx(lat.iloc[:4].tolist(), abs=1e-9)
    assert pd.isna(lon2.iloc[4]) and pd.isna(lat2.iloc[4])


def test_one_degree_east_of_the_meridian_is_about_300_000_feet():
    # On the latitude of origin, 1° of longitude is about 92.4 km = 303,000 ftUS (cos 33.75° × 111.32 km).
    x, _ = sp.to_stateplane(pd.Series([-78.0]), pd.Series([33.75]))
    assert x.iloc[0] - 2_000_000 == pytest.approx(303_000, rel=0.01)
