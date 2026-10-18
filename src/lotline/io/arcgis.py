"""ArcGIS REST pager: download every feature of a layer through `fetch()`, so each page is cached and logged.

Most state permit and parcel sources are ArcGIS FeatureServer or MapServer layers that return at most
`maxRecordCount` features per query. Two strategies:

- **offset paging** (`resultOffset` + `resultRecordCount`, ordered by the object-ID field) when the layer
  advertises `supportsPagination`;
- **object-ID chunks** otherwise (e.g. Durham's MapServer): fetch the full ID list with `returnIdsOnly`,
  then query the IDs in chunks.

A short page with `exceededTransferLimit` means the server capped the page below what we asked for; paging
continues from the number of features actually returned.

Raw files land under `raw/<source>/<vintage>/<name>/`: the layer description as `layer.json`, and each query's
pages in their own folder, `q-<hash>/page_NNNN.json` (plus `object_ids.json` for ID chunks). The hash covers
what defines the query (filter, fields, geometry, page size, paging strategy), so rerunning the same query
reuses its cached pages, while a different query the same day (another field list, say) becomes a new
snapshot instead of overwriting the first. With the default vintage (today's date) every fetch of a rolling
window is a dated snapshot.
"""

from __future__ import annotations

import datetime as dt
import json
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

import httpx
import pandas as pd

from lotline.io.http import client, fetch
from lotline.io.store import DataStore, query_folder

GEOMETRY_MODES = {"none", "point", "centroid", "polygon"}
ID_CHUNK = 500  # object IDs per query: keeps GET URLs well under common length limits


class ArcGISError(RuntimeError):
    pass


@dataclass(frozen=True)
class LayerInfo:
    max_records: int
    object_id_field: str
    supports_pagination: bool
    supports_order_by: bool
    geometry_type: str | None = None  # e.g. esriGeometryPoint, esriGeometryPolygon
    supports_centroid: bool = False  # the server can compute polygon label points (returnCentroid)


def query_url(layer_url: str, **params) -> str:
    """Deterministic query URL (sorted parameters), so the same request always hits the same cache entry."""
    return f"{layer_url.rstrip('/')}/query?{urlencode(sorted(params.items()))}"


def _json(path: Path) -> dict:
    data = json.loads(path.read_text())
    if "error" in data:  # ArcGIS reports errors as HTTP 200 with an error body
        path.unlink()  # never cache an error page as data
        raise ArcGISError(f"{data['error'].get('code')}: {data['error'].get('message')}")
    return data


@dataclass
class _Ctx:
    store: DataStore
    source: str
    license: str
    adapter: str
    adapter_version: str
    raw_dir: Path
    http: httpx.Client
    pause: float
    refresh: bool
    retries: int = 3
    backoff: float = 2.0

    def get(self, url: str, name: str) -> dict:
        """Fetch one page; an ArcGIS error body (HTTP 200) is retried with backoff, then raised."""
        for attempt in range(self.retries + 1):
            path = fetch(
                url,
                self.raw_dir / name,
                store=self.store,
                source=self.source,
                license=self.license,
                adapter=self.adapter,
                adapter_version=self.adapter_version,
                http=self.http,
                refresh=self.refresh,
            )
            if self.pause:
                time.sleep(self.pause)  # be polite to small municipal servers
            try:
                return _json(path)  # an error page is deleted, so the next attempt downloads again
            except ArcGISError:
                if attempt == self.retries:
                    raise
                time.sleep(self.backoff * 2**attempt)  # some servers fail deep pages intermittently
        raise AssertionError("unreachable")


def layer_info(meta: dict) -> LayerInfo:
    adv = meta.get("advancedQueryCapabilities") or {}
    oid = meta.get("objectIdField") or next(
        (f["name"] for f in meta.get("fields", []) if f.get("type") == "esriFieldTypeOID"), None
    )
    if not oid:
        raise ArcGISError("layer has no object-ID field")
    return LayerInfo(
        max_records=int(meta.get("maxRecordCount") or 1000),
        object_id_field=oid,
        supports_pagination=bool(adv.get("supportsPagination", False)),
        supports_order_by=bool(adv.get("supportsOrderBy", True)),
        geometry_type=meta.get("geometryType"),
        supports_centroid=bool(adv.get("supportsReturningGeometryCentroid", False)),
    )


def download_layer(
    layer_url: str,
    *,
    store: DataStore,
    source: str,
    license: str,
    adapter: str,
    adapter_version: str,
    name: str = "layer",
    where: str = "1=1",
    out_fields: str = "*",
    geometry: bool | str = False,
    vintage: str | None = None,
    page_size: int | None = None,
    pause: float = 0.5,
    refresh: bool = False,
    http: httpx.Client | None = None,
    retries: int = 3,
    retry_backoff: float = 2.0,
) -> pd.DataFrame:
    """Download all features matching `where` and return their attributes, plus geometry if asked.

    `geometry` (all in WGS84):

    - `False`: attributes only;
    - `True` or `"point"`: `lon`/`lat` of the feature's point, or of a polygon's label point when the server
      can compute it (`returnCentroid`), so parcel layers yield centroids;
    - `"centroid"`: polygon label points only, without downloading the polygons (about a quarter of the
      bytes on a parcel layer); polygon layers only;
    - `"polygon"`: a `rings` column (a list of rings, each a list of [lon, lat] pairs); polygon layers only.

    An ArcGIS error body is retried `retries` times with exponential backoff before it is raised.
    """
    mode = {False: "none", True: "point"}.get(geometry, geometry)  # type: ignore[arg-type]
    if mode not in GEOMETRY_MODES:
        raise ValueError(f"geometry must be one of False, True, {sorted(GEOMETRY_MODES - {'none'})}")
    vintage = vintage or dt.date.today().isoformat()
    own = http is None
    ctx = _Ctx(
        store,
        source,
        license,
        adapter,
        adapter_version,
        store.raw(source, vintage) / name,
        http or client(timeout=120),
        pause,
        refresh,
        retries,
        retry_backoff,
    )
    try:
        info = layer_info(ctx.get(f"{layer_url.rstrip('/')}?f=json", "layer.json"))
        size = min(page_size or info.max_records, info.max_records)
        polygon_layer = info.geometry_type == "esriGeometryPolygon"
        if mode in ("centroid", "polygon") and not polygon_layer:
            raise ArcGISError(f"geometry={mode!r} needs a polygon layer, not {info.geometry_type}")
        if mode == "centroid" and not info.supports_centroid:  # such servers ignore returnCentroid silently
            raise ArcGISError("this server can't compute centroids (returnCentroid); use geometry='polygon'")
        fields = [f.strip() for f in out_fields.split(",")]
        if (
            "*" not in fields and info.object_id_field not in fields
        ):  # needed for paging and the overlap check
            out_fields = ",".join([info.object_id_field, *fields])
        downloads = mode in ("point", "polygon")
        base = {
            "where": where,
            "outFields": out_fields,
            "f": "json",
            "returnGeometry": str(downloads).lower(),
        }
        if mode != "none":
            base |= {"outSR": "4326"}
        if (mode == "point" and polygon_layer) or mode == "centroid":  # point layers reject returnCentroid
            base |= {"returnCentroid": "true"}
        by_offset = info.supports_pagination and info.supports_order_by
        strategy = "offset" if by_offset else "object_ids"
        ctx.raw_dir = ctx.raw_dir / query_folder(base, size, strategy)
        if by_offset:
            features = _by_offset(ctx, layer_url, base, info, size)
        else:
            features = _by_object_ids(ctx, layer_url, base, info, size)
    finally:
        if own:
            ctx.http.close()
    return _to_frame(features, info.object_id_field, mode)


def _by_offset(ctx: _Ctx, url: str, base: dict, info: LayerInfo, size: int) -> list[dict]:
    features, offset, page = [], 0, 1
    while True:
        params = base | {
            "orderByFields": info.object_id_field,
            "resultOffset": offset,
            "resultRecordCount": size,
        }
        data = ctx.get(query_url(url, **params), f"page_{page:04d}.json")
        got = data.get("features", [])
        features += got
        if not got or (len(got) < size and not data.get("exceededTransferLimit")):
            return features
        offset += len(got)
        page += 1


def _by_object_ids(ctx: _Ctx, url: str, base: dict, info: LayerInfo, size: int) -> list[dict]:
    ids_params = {"where": base["where"], "returnIdsOnly": "true", "f": "json"}
    ids = sorted(ctx.get(query_url(url, **ids_params), "object_ids.json").get("objectIds") or [])
    chunk = min(size, ID_CHUNK)
    features = []
    for page, start in enumerate(range(0, len(ids), chunk), start=1):
        part = ids[start : start + chunk]
        params = {k: v for k, v in base.items() if k != "where"} | {"objectIds": ",".join(map(str, part))}
        data = ctx.get(query_url(url, **params), f"page_{page:04d}.json")
        got = data.get("features", [])
        if len(got) < len(part):
            raise ArcGISError(f"asked for {len(part)} object IDs, server returned {len(got)}")
        features += got
    return features


def _to_frame(features: list[dict], oid: str, mode: str) -> pd.DataFrame:
    rows = []
    for f in features:
        row = dict(f.get("attributes") or {})
        if mode == "polygon":
            row["rings"] = (f.get("geometry") or {}).get("rings")
        elif mode != "none":
            g = f.get("centroid") or f.get("geometry") or {}
            row["lon"], row["lat"] = g.get("x"), g.get("y")
        rows.append(row)
    df = pd.DataFrame(rows)
    if len(df) and df[oid].duplicated().any():
        raise ArcGISError(
            f"duplicate {oid} values: paging overlapped (is the layer changing during download?)"
        )
    return df


def epoch_ms_to_timestamp(values: pd.Series) -> pd.Series:
    """ArcGIS date fields arrive as milliseconds since 1970 (UTC); return naive UTC timestamps."""
    return pd.to_datetime(pd.to_numeric(values, errors="coerce"), unit="ms", utc=True).dt.tz_localize(None)
