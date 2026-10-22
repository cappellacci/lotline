"""NC State Plane (NAD83, US survey feet, EPSG:2264) → longitude/latitude (helper, no data).

Some county files give points only in North Carolina State Plane coordinates. `to_lonlat` inverts the
Lambert conformal conic projection that defines EPSG:2264, with Snyder's ellipsoidal formulas (*Map
Projections: A Working Manual*, USGS Professional Paper 1395, 1987, eqs. 15-1 to 15-11, 7-9 and 7-13), so the
points can go through `lotline.geo.place_or_township` like any WGS84 point. NAD83 and WGS84 differ by about
a metre here, which is far below what placing a permit in a town needs. numpy only.

EPSG:2264 definition (NAD83 / North Carolina (ftUS)): GRS 1980 ellipsoid; standard parallels 34°20' N and
36°10' N; latitude of origin 33°45' N; central meridian 79° W; false easting 609,601.22 m (2,000,000 ftUS);
false northing 0.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

A = 6_378_137.0  # GRS 1980 semi-major axis (m)
INV_F = 298.257222101  # GRS 1980 inverse flattening
US_FT = 1200 / 3937  # metres per US survey foot
LAT1, LAT2, LAT0, LON0 = np.radians([34 + 20 / 60, 36 + 10 / 60, 33.75, -79.0])
FALSE_EASTING_M = 609_601.22

_F = 1 / INV_F
E = np.sqrt(2 * _F - _F**2)


def _m(phi):
    return np.cos(phi) / np.sqrt(1 - (E * np.sin(phi)) ** 2)


def _t(phi):
    s = E * np.sin(phi)
    return np.tan(np.pi / 4 - phi / 2) / ((1 - s) / (1 + s)) ** (E / 2)


N = (np.log(_m(LAT1)) - np.log(_m(LAT2))) / (np.log(_t(LAT1)) - np.log(_t(LAT2)))
F_CONST = _m(LAT1) / (N * _t(LAT1) ** N)
RHO0 = A * F_CONST * _t(LAT0) ** N


def to_lonlat(x_ft: pd.Series, y_ft: pd.Series, iterations: int = 8) -> tuple[pd.Series, pd.Series]:
    """(lon, lat) in degrees for EPSG:2264 easting/northing in US survey feet; missing stays missing."""
    x = pd.to_numeric(x_ft, errors="coerce").to_numpy(dtype=float) * US_FT - FALSE_EASTING_M
    y = RHO0 - pd.to_numeric(y_ft, errors="coerce").to_numpy(dtype=float) * US_FT
    rho = np.sign(N) * np.hypot(x, y)
    t = (rho / (A * F_CONST)) ** (1 / N)
    theta = np.arctan2(x, y)
    lon = theta / N + LON0
    lat = np.pi / 2 - 2 * np.arctan(t)
    for _ in range(iterations):  # converges to well under 1e-12 rad in 3-4 steps
        s = E * np.sin(lat)
        lat = np.pi / 2 - 2 * np.arctan(t * ((1 - s) / (1 + s)) ** (E / 2))
    idx = pd.Series(x_ft).index
    return pd.Series(np.degrees(lon), index=idx), pd.Series(np.degrees(lat), index=idx)


def to_stateplane(lon: pd.Series, lat: pd.Series) -> tuple[pd.Series, pd.Series]:
    """The forward projection (degrees → EPSG:2264 US feet), for round-trip checks."""
    phi = np.radians(pd.to_numeric(lat, errors="coerce").to_numpy(dtype=float))
    lam = np.radians(pd.to_numeric(lon, errors="coerce").to_numpy(dtype=float))
    rho = A * F_CONST * _t(phi) ** N
    theta = N * (lam - LON0)
    x = (FALSE_EASTING_M + rho * np.sin(theta)) / US_FT
    y = (RHO0 - rho * np.cos(theta)) / US_FT
    idx = pd.Series(lon).index
    return pd.Series(x, index=idx), pd.Series(y, index=idx)
