"""ArcGIS REST pager: download every feature of a layer through `fetch()`, so each page is cached and logged.

Most state permit and parcel sources are ArcGIS FeatureServer or MapServer layers that return at most
`maxRecordCount` features per query. Two strategies:

- **offset paging** (`resultOffset` + `resultRecordCount`, ordered by the object-ID field) when the layer
  advertises `supportsPagination`;
- **object-ID chunks** otherwise (e.g. Durham's MapServer): fetch the full ID list with `returnIdsOnly`,
  then query the IDs in chunks.

A short page with `exceededTransferLimit` means the server capped the page below what we asked for; paging
continues from the number of features actually returned. Raw pages land under
`raw/<source>/<vintage>/<name>/page_NNNN.json`; with the default vintage (today's date) every fetch of a
rolling window is a dated snapshot.
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
from lotline.io.store import DataStore

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

    def get(self, url: str, name: str) -> dict:
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
        return _json(path)


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
    geometry: bool = False,
    vintage: str | None = None,
    page_size: int | None = None,
    pause: float = 0.5,
    refresh: bool = False,
    http: httpx.Client | None = None,
) -> pd.DataFrame:
    """Download all features matching `where` and return their attributes (plus `lon`/`lat` if `geometry`).

    Geometry, when requested, is returned as a WGS84 point: the feature's point, or the label point of a
    polygon when the server can compute it (`returnCentroid`), so parcel layers yield centroids.
    """
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
    )
    try:
        info = layer_info(ctx.get(f"{layer_url.rstrip('/')}?f=json", "layer.json"))
        size = min(page_size or info.max_records, info.max_records)
        base = {"where": where, "outFields": out_fields, "f": "json", "returnGeometry": str(geometry).lower()}
        if geometry:
            base |= {"outSR": "4326"}
            if info.geometry_type == "esriGeometryPolygon":  # point layers reject returnCentroid
                base |= {"returnCentroid": "true"}
        if info.supports_pagination and info.supports_order_by:
            features = _by_offset(ctx, layer_url, base, info, size)
        else:
            features = _by_object_ids(ctx, layer_url, base, info, size)
    finally:
        if own:
            ctx.http.close()
    return _to_frame(features, info.object_id_field, geometry)


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


def _to_frame(features: list[dict], oid: str, geometry: bool) -> pd.DataFrame:
    rows = []
    for f in features:
        row = dict(f.get("attributes") or {})
        if geometry:
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
