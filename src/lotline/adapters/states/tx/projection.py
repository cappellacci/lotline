"""Projected coordinates → longitude/latitude, from a shapefile's `.prj` text (helper, no data). numpy only.

StratMap parcel shapefiles carry their coordinate system in a `.prj` file (ESRI WKT). `from_wkt` reads it and
returns a function that maps arrays of x, y to longitude, latitude (degrees), so parcel centroids can go
through `lotline.geo.place_or_township` like any WGS84 point. Supported, because they are what Texas GIS
publishers use:

- **geographic** (`GEOGCS` only: NAD83 / WGS84 degrees): returned as is;
- **Albers equal-area conic** (`Albers`, `Albers_Conic_Equal_Area`; e.g. EPSG:3083, NAD83 / Texas Centric
  Albers Equal Area): inverted with Snyder's ellipsoidal formulas (*Map Projections: A Working Manual*,
  USGS Professional Paper 1395, 1987, eqs. 14-1 to 14-21 and 3-16), φ found by the iteration of eq. 3-16;
- **Web Mercator** (`Mercator_Auxiliary_Sphere`, EPSG:3857): spherical inverse on the semi-major axis.

Anything else raises `ValueError` naming the projection, so a new one is added on purpose, never guessed.
NAD83 and WGS84 differ by about a metre in Texas, far below what placing a parcel in a city needs.

`albers_forward` is the forward projection, used by the tests to check the inverse.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import numpy as np

GRS80 = (6_378_137.0, 298.257222101)  # semi-major axis (m), inverse flattening

ToLonLat = Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]


def _param(wkt: str, name: str) -> float:
    m = re.search(rf'PARAMETER\["{name}",\s*([-0-9.eE+]+)\]', wkt, flags=re.IGNORECASE)
    if not m:
        raise ValueError(f"projection parameter {name} not found in the .prj text")
    return float(m.group(1))


def _spheroid(wkt: str) -> tuple[float, float]:
    m = re.search(r'SPHEROID\["[^"]*",\s*([-0-9.eE+]+),\s*([-0-9.eE+]+)', wkt, flags=re.IGNORECASE)
    return (float(m.group(1)), float(m.group(2))) if m else GRS80


def _linear_unit(wkt: str) -> float:
    """Metres per projected unit: the last UNIT in a PROJCS is the linear one."""
    units = re.findall(r'UNIT\["[^"]*",\s*([-0-9.eE+]+)\]', wkt, flags=re.IGNORECASE)
    return float(units[-1]) if units else 1.0


class _Albers:
    """Ellipsoidal Albers equal-area conic (Snyder 1987, ch. 14)."""

    def __init__(self, lat1, lat2, lat0, lon0, a=GRS80[0], inv_f=GRS80[1], fe=0.0, fn=0.0):
        f = 1 / inv_f
        self.a, self.e = a, np.sqrt(2 * f - f * f)
        self.lon0, self.fe, self.fn = np.radians(lon0), fe, fn
        p1, p2, p0 = np.radians([lat1, lat2, lat0])
        m1, m2 = self._m(p1), self._m(p2)
        q1, q2, q0 = self._q(p1), self._q(p2), self._q(p0)
        self.n = (m1 * m1 - m2 * m2) / (q2 - q1) if not np.isclose(p1, p2) else np.sin(p1)
        self.c = m1 * m1 + self.n * q1
        self.rho0 = a * np.sqrt(self.c - self.n * q0) / self.n

    def _m(self, phi):
        return np.cos(phi) / np.sqrt(1 - (self.e * np.sin(phi)) ** 2)

    def _q(self, phi):
        e, s = self.e, np.sin(phi)
        return (1 - e * e) * (s / (1 - (e * s) ** 2) - np.log((1 - e * s) / (1 + e * s)) / (2 * e))

    def forward(self, lon, lat):
        phi, lam = np.radians(lat), np.radians(lon)
        rho = self.a * np.sqrt(self.c - self.n * self._q(phi)) / self.n
        theta = self.n * (lam - self.lon0)
        return self.fe + rho * np.sin(theta), self.fn + self.rho0 - rho * np.cos(theta)

    def inverse(self, x, y, iterations: int = 8):
        x = np.asarray(x, dtype="float64") - self.fe
        y = np.asarray(y, dtype="float64") - self.fn
        sign = np.sign(self.n)
        rho = sign * np.hypot(x, self.rho0 - y)
        theta = np.arctan2(sign * x, sign * (self.rho0 - y))
        q = (self.c - (rho * self.n / self.a) ** 2) / self.n
        e = self.e
        phi = np.arcsin(np.clip(q / 2, -1, 1))
        for _ in range(iterations):  # Snyder eq. 3-16
            s = np.sin(phi)
            w = 1 - (e * s) ** 2
            phi = phi + w * w / (2 * np.cos(phi)) * (
                q / (1 - e * e) - s / w + np.log((1 - e * s) / (1 + e * s)) / (2 * e)
            )
        return np.degrees(self.lon0 + theta / self.n), np.degrees(phi)


def albers_forward(lon, lat, **params) -> tuple[np.ndarray, np.ndarray]:
    return _Albers(**params).forward(np.asarray(lon, dtype="float64"), np.asarray(lat, dtype="float64"))


def equal_area_sqm_per_unit2(wkt: str) -> float | None:
    """Square metres per squared projected unit when the projection is equal-area (Albers), else None.

    Only then is a polygon's planar area its true area, so lot size can be measured from the shape.
    """
    m = re.search(r'PROJECTION\["([^"]+)"\]', wkt, flags=re.IGNORECASE)
    if m and m.group(1).lower() in ("albers", "albers_conic_equal_area"):
        return _linear_unit(wkt) ** 2
    return None


def from_wkt(wkt: str) -> ToLonLat:
    """A function mapping (x, y) arrays in the `.prj`'s coordinate system to (lon, lat) degrees."""
    text = wkt.strip()
    if text.upper().startswith("GEOGCS"):
        return lambda x, y: (np.asarray(x, dtype="float64"), np.asarray(y, dtype="float64"))
    m = re.search(r'PROJECTION\["([^"]+)"\]', text, flags=re.IGNORECASE)
    if not m:
        raise ValueError("the .prj text has neither GEOGCS nor a PROJECTION")
    name = m.group(1).lower()
    unit = _linear_unit(text)
    fe, fn = _param(text, "False_Easting") * unit, _param(text, "False_Northing") * unit
    if name in ("albers", "albers_conic_equal_area"):
        a, inv_f = _spheroid(text)
        proj = _Albers(
            _param(text, "Standard_Parallel_1"),
            _param(text, "Standard_Parallel_2"),
            _param(text, "Latitude_Of_Origin"),
            _param(text, "Central_Meridian"),
            a=a,
            inv_f=inv_f,
            fe=fe,
            fn=fn,
        )
        return lambda x, y: proj.inverse(
            np.asarray(x, dtype="float64") * unit, np.asarray(y, dtype="float64") * unit
        )
    if name == "mercator_auxiliary_sphere":
        a, _ = _spheroid(text)
        lon0 = _param(text, "Central_Meridian")

        def merc(x, y):
            xm = np.asarray(x, dtype="float64") * unit - fe
            ym = np.asarray(y, dtype="float64") * unit - fn
            return lon0 + np.degrees(xm / a), np.degrees(2 * np.arctan(np.exp(ym / a)) - np.pi / 2)

        return merc
    raise ValueError(f"unsupported projection {m.group(1)!r} in the .prj text: add it to {__name__}")
