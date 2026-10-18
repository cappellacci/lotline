"""Assign points (parcel centroids, permit locations) to the government that permits them. Numpy only.

**Rule** (`place_or_township`): a point inside an incorporated place belongs to that place (7-digit GEOID).
Otherwise, in states whose townships issue building permits (`township_permits: true`: MN and OH, where the
Census Building Permits Survey has a row per township), it belongs to its county subdivision (10-digit
GEOID). Otherwise it gets None and the caller falls back to the county, which permits unincorporated land
in NC and TX. Points with a missing coordinate get None. Callers should still check the result against the
jurisdictions table: an unorganized territory, say, is a county subdivision but not a permit issuer.

**Point in polygon** (`points_in_rings`): the even-odd rule over every ring of a (multi)polygon, so holes,
islands and enclaves need no special handling. A point is inside when a ray from it towards +x crosses the
rings an odd number of times. An edge counts for a point when the point's y is in the half-open interval
[min(y1, y2), max(y1, y2)), so a ray through a vertex shared by two edges is counted once (or for a peak,
zero or two times), and horizontal edges never count. Points exactly on an edge go to one side by this fixed
rule; there is no tolerance.

For speed with millions of points it is a vectorized scanline: candidate points (inside the polygon's
bounding box) are sorted by y, each edge finds the run of points whose y it spans with `np.searchsorted`,
and all (edge, point) pairs are expanded at once, in chunks of at most `PAIR_CHUNK` pairs to bound memory.
The work is the number of points times the number of edges crossing a point's horizontal line, not points
times all edges.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PAIR_CHUNK = 4_000_000  # (edge, point) pairs per batch: about 100 MB of temporaries; mechanics only


def _edges(rings) -> np.ndarray:
    """(n, 4) array of x1, y1, x2, y2 for every non-horizontal edge of every ring (rings closed if open)."""
    parts = []
    for ring in rings:
        r = np.asarray(ring, dtype="float64").reshape(-1, 2)
        if len(r) < 3:
            continue
        if not np.array_equal(r[0], r[-1]):
            r = np.vstack([r, r[:1]])
        parts.append(np.hstack([r[:-1], r[1:]]))
    if not parts:
        return np.empty((0, 4))
    e = np.vstack(parts)
    return e[e[:, 1] != e[:, 3]]


def points_in_rings(x, y, rings) -> np.ndarray:
    """Boolean mask: is each point (x, y) inside the polygon formed by `rings` under the even-odd rule?"""
    x = np.asarray(x, dtype="float64")
    y = np.asarray(y, dtype="float64")
    inside = np.zeros(x.shape, dtype=bool)
    e = _edges(rings)
    if not len(e) or not x.size:
        return inside
    xmin, xmax = min(e[:, 0].min(), e[:, 2].min()), max(e[:, 0].max(), e[:, 2].max())
    ymin, ymax = min(e[:, 1].min(), e[:, 3].min()), max(e[:, 1].max(), e[:, 3].max())
    with np.errstate(invalid="ignore"):  # NaN coordinates compare False: never candidates
        cand = np.flatnonzero((x >= xmin) & (x <= xmax) & (y >= ymin) & (y < ymax))
    if not cand.size:
        return inside
    order = np.argsort(y[cand], kind="stable")
    cand = cand[order]
    py, px = y[cand], x[cand]

    x1, y1, x2, y2 = e.T
    ylo, yhi = np.minimum(y1, y2), np.maximum(y1, y2)
    start = np.searchsorted(py, ylo, side="left")  # first point with y >= ylo
    stop = np.searchsorted(py, yhi, side="left")  # first point with y >= yhi (half-open)
    count = stop - start
    keep = count > 0
    x1, y1, x2, y2, start, count = x1[keep], y1[keep], x2[keep], y2[keep], start[keep], count[keep]
    slope = (x2 - x1) / (y2 - y1)

    crossings = np.zeros(cand.size, dtype=np.int64)
    total = np.cumsum(count)
    begin = 0
    while begin < len(count):
        # Edges [begin, end) whose pairs fit the chunk (at least one edge, however many points it spans).
        base = total[begin - 1] if begin else 0
        end = max(int(np.searchsorted(total, base + PAIR_CHUNK, side="right")), begin + 1)
        c = count[begin:end]
        edge = np.repeat(np.arange(begin, end), c)
        offset = np.arange(c.sum()) - np.repeat(np.cumsum(c) - c, c)  # 0..c-1 within each edge's run
        pt = start[edge] + offset
        x_at = x1[edge] + (py[pt] - y1[edge]) * slope[edge]
        crossings += np.bincount(pt[x_at > px[pt]], minlength=cand.size)
        begin = end
    inside[cand] = (crossings % 2).astype(bool)
    return inside


def assign(lon, lat, polygons: pd.DataFrame) -> np.ndarray:
    """GEOID of the polygon (`geoid`, `rings` columns) holding each point, else None. First match wins.

    Polygons of one level (places, or county subdivisions) don't overlap, so their order doesn't matter.
    Points are sorted by longitude once, so each polygon only scans the strip under its bounding box.
    """
    x = np.asarray(lon, dtype="float64")
    y = np.asarray(lat, dtype="float64")
    out = np.full(x.shape, None, dtype=object)
    ok = np.flatnonzero(np.isfinite(x) & np.isfinite(y))
    ok = ok[np.argsort(x[ok], kind="stable")]
    xs = x[ok]
    done = np.zeros(ok.size, dtype=bool)
    for geoid, rings in zip(polygons["geoid"], polygons["rings"], strict=True):
        if not rings:
            continue
        pts = np.vstack([np.asarray(r, dtype="float64").reshape(-1, 2) for r in rings])
        lo, hi = np.searchsorted(xs, pts[:, 0].min(), "left"), np.searchsorted(xs, pts[:, 0].max(), "right")
        if lo == hi:
            continue
        strip = np.arange(lo, hi)
        sy = y[ok[strip]]
        strip = strip[~done[strip] & (sy >= pts[:, 1].min()) & (sy <= pts[:, 1].max())]
        if not strip.size:
            continue
        hit = strip[points_in_rings(xs[strip], y[ok[strip]], rings)]
        out[ok[hit]] = geoid
        done[hit] = True
    return out


def place_or_township(lon, lat, state: str, store, *, refresh: bool = False) -> pd.Series:
    """Incorporated place GEOID; else, where townships issue permits, the county subdivision GEOID; else None.

    See the module docstring for the rule. The result keeps `lon`'s index when it is a Series.
    """
    from lotline.adapters.national.tiger_boundaries import load_polygons
    from lotline.config import load_state

    index = lon.index if isinstance(lon, pd.Series) else None
    x = np.asarray(lon, dtype="float64")
    y = np.asarray(lat, dtype="float64")
    out = assign(x, y, load_polygons(state, store, "place", refresh=refresh))
    if load_state(state).township_permits:
        rest = np.flatnonzero(pd.isna(out))
        if rest.size:
            out[rest] = assign(x[rest], y[rest], load_polygons(state, store, "cousub", refresh=refresh))
    return pd.Series(out, index=index, dtype=object, name="geoid")
