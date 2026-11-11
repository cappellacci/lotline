"""Socrata (SODA) pager: download every row of a dataset through `fetch()`, so each page is cached and logged.

City open-data portals on Socrata (Austin, Cincinnati, ...) serve rows from
`https://<domain>/resource/<dataset id>.json` with SoQL parameters. Pages are requested with `$limit` /
`$offset`, ordered by the system row id `:id` so the order is stable between pages; the row id is also used
to check that no row came back twice (which would mean the dataset changed during the download).

`select` is required: permit datasets often carry contractor and applicant names, phone numbers and
addresses, so an adapter names the fields it needs and nothing else is downloaded.

Raw files land under `raw/<source>/<vintage>/<name>/`: the dataset description as `dataset.json`, and each
query's pages in their own folder, `q-<hash>/page_NNNN.json` (see `query_folder`). With the default vintage
(today's date) every fetch of a live dataset is a dated snapshot.

An optional app token (`SOCRATA_APP_TOKEN` in the environment or `.env`) raises Socrata's rate limits; it is
sent with each request but never written to the manifest, cache key or error messages.

During an offline build (`lotline fetch --offline`, see `lotline.io.offline`) nothing is requested: the newest
complete cached snapshot of the same query is read instead, and incomplete ones are skipped with a note.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import time
from pathlib import Path

import httpx
import pandas as pd

from lotline.io import offline
from lotline.io.http import client, fetch
from lotline.io.store import DataStore, _dotenv_value, query_folder

PAGE_SIZE = 50_000  # SODA's largest page; smaller pages only mean more requests


class SocrataError(RuntimeError):
    pass


def resource_url(domain: str, dataset_id: str, **params: str | int) -> str:
    """Deterministic SODA query URL (sorted parameters): the same request always hits the same cache entry."""
    query = str(httpx.QueryParams(sorted(params.items())))
    base = f"https://{domain}/resource/{dataset_id}.json"
    return f"{base}?{query}" if query else base


def _token() -> dict[str, str]:
    token = os.environ.get("SOCRATA_APP_TOKEN") or _dotenv_value("SOCRATA_APP_TOKEN")
    return {"$$app_token": token} if token else {}


def download_dataset(
    domain: str,
    dataset_id: str,
    *,
    select: list[str],
    store: DataStore,
    source: str,
    license: str,
    adapter: str,
    adapter_version: str,
    name: str = "dataset",
    where: str | None = None,
    vintage: str | None = None,
    page_size: int = PAGE_SIZE,
    pause: float = 0.5,
    refresh: bool = False,
    http: httpx.Client | None = None,
) -> pd.DataFrame:
    """Download the `select` columns of every row matching `where` (SoQL) and return them as strings.

    SODA returns every value as text (numbers included) and leaves out keys whose value is null, so the
    adapter converts types and missing columns come back as all-null.
    """
    if not select:
        raise SocrataError("select is required: name the (non-personal) fields to download")
    params = {"$select": ",".join([":id", *select]), "$order": ":id"}
    if where:
        params["$where"] = where
    folder = query_folder(params, page_size, "soda_offset")
    if offline.is_offline():
        return _from_cache(
            domain, dataset_id, store, source, name, vintage, params, folder, page_size, select
        )
    vintage = vintage or dt.date.today().isoformat()
    raw_dir = store.raw(source, vintage) / name
    own = http is None
    http = http or client(timeout=120)
    secret = _token()

    def get(url: str, dest: Path) -> object:
        try:
            path = fetch(
                url,
                dest,
                store=store,
                source=source,
                license=license,
                adapter=adapter,
                adapter_version=adapter_version,
                http=http,
                refresh=refresh,
                secret_params=secret,
            )
        except httpx.HTTPStatusError as exc:  # SODA explains a bad query in the error body
            raise SocrataError(f"{exc}: {_message(exc.response)}") from None
        if pause:
            time.sleep(pause)  # be polite to city portals
        return json.loads(path.read_text())

    try:
        get(f"https://{domain}/api/views/{dataset_id}.json", raw_dir / "dataset.json")
        rows = _pages(get, domain, dataset_id, params, raw_dir / folder, page_size)
    finally:
        if own:
            http.close()
    return _to_frame(rows, select)


def _pages(get, domain: str, dataset_id: str, params: dict, pages: Path, page_size: int) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    page = 1
    while True:
        url = resource_url(domain, dataset_id, **params, **{"$limit": page_size, "$offset": len(rows)})
        got = get(url, pages / f"page_{page:04d}.json")
        if not isinstance(got, list):
            raise SocrataError(f"expected a list of rows from {url}")
        ids = [r.get(":id") for r in got]
        if None in ids or seen.intersection(ids) or len(set(ids)) < len(ids):
            # checked page by page: a server repeating full pages would otherwise never end the loop
            raise SocrataError(
                "duplicate or missing row ids: paging overlapped (did the dataset change mid-download?)"
            )
        seen.update(ids)
        rows += got
        if len(got) < page_size:
            return rows
        page += 1


def _from_cache(
    domain: str,
    dataset_id: str,
    store: DataStore,
    source: str,
    name: str,
    vintage: str | None,
    params: dict,
    folder: str,
    page_size: int,
    select: list[str],
) -> pd.DataFrame:
    """Offline: the newest complete cached snapshot of this query (see `lotline.io.offline`)."""
    sess = offline.session()
    meta_url = f"https://{domain}/api/views/{dataset_id}.json"
    skipped = []
    for raw_dir in offline.candidate_dirs(store, source, name, vintage, "dataset.json", meta_url):
        pages = raw_dir / folder
        try:
            if not pages.is_dir():
                raise offline.SnapshotIncomplete(f"no pages for this query ({folder})")
            rows = _pages(
                lambda _url, dest: offline.read_cached(dest), domain, dataset_id, params, pages, page_size
            )
        except offline.SnapshotIncomplete as exc:
            skipped.append(f"{pages.relative_to(store.root)}: incomplete ({exc})")
            if sess:
                sess.note(skipped[-1])
            continue
        if sess:
            sess.used_path(pages)
        return _to_frame(rows, select)
    detail = "; ".join(skipped) or "no cached snapshot of this dataset"
    raise offline.OfflineError(
        f"offline build: no complete cached snapshot of {source}/{name} for {domain}/{dataset_id} "
        f"({detail}); run `lotline fetch` online to download it"
    )


def _message(resp: httpx.Response | None) -> str:
    try:
        return str(resp.json().get("message", "")) if resp is not None else ""
    except ValueError:
        return ""


def _to_frame(rows: list[dict], select: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=[":id", *select]).astype("string")
    return df.drop(columns=":id").reset_index(drop=True)
