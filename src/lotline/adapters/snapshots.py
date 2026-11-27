"""Read every dated snapshot of a rolling-window ArcGIS layer, so permits that roll out are kept.

Some city permit layers keep only a recent window (St. Paul: 10 years; Minneapolis from Dec 2016). Each fetch
is saved as a dated raw snapshot (`raw/<source>/<YYYY-MM-DD>/<name>/`, the default vintage of
`download_layer`), but reading only the newest one drops whatever has rolled out since an earlier fetch,
with no error (ingestion review, 2026-11-25, item 3).

`all_snapshots` downloads (or, offline, reads) today's copy as usual, then reads every complete cached
snapshot of the same query from disk, and tags each row with its snapshot date. `newest_rows` then keeps, for
each permit, only its rows from the newest snapshot that lists it, so a permit's latest status wins and a
permit seen only in an older snapshot is kept. Older snapshots are read from the cache only: nothing extra
is downloaded.

Limitation: a permit the city deleted outright (not just cancelled) stays in from the older snapshot.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from lotline.io import DataStore, offline

SNAPSHOT = "_snapshot"  # the vintage (YYYY-MM-DD folder name) each row was read from


def cached_vintages(store: DataStore, source: str, name: str) -> list[str]:
    """Vintage folders holding a saved layer description for `name`, oldest first."""
    base = store.root / "raw" / source
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if (p / name / "layer.json").is_file())


def all_snapshots(
    read: Callable[[str | None], pd.DataFrame], store: DataStore, source: str, name: str
) -> pd.DataFrame:
    """Every complete snapshot of a layer, stacked, with a `SNAPSHOT` column.

    `read(vintage)` is the adapter's own `download_layer` call with that vintage (None: today's, as usual).
    It is called once with None, which downloads today's copy (or, offline, reads the newest complete one),
    then once per cached vintage inside an offline build, so those reads come from disk only."""
    current = read(None)
    vintages = cached_vintages(store, source, name)
    frames, skipped = [], []

    def from_cache(v: str) -> None:
        try:
            frames.append(read(v).assign(**{SNAPSHOT: v}))
        except offline.OfflineError as exc:  # an incomplete or foreign snapshot is skipped, never mixed in
            skipped.append(f"{v}: {exc}")

    if offline.is_offline():
        for v in vintages:
            from_cache(v)
    else:
        with offline.offline_build(store):
            for v in vintages:
                from_cache(v)
    for note in skipped:
        print(f"note: {source}/{name}: skipped snapshot {note}")
    if not frames:  # nothing on disk to stack (e.g. a client that saves nothing): today's copy alone
        return current.assign(**{SNAPSHOT: "current"})
    return pd.concat(frames, ignore_index=True)


def newest_rows(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """For each `key` (a permit number), only its rows from the newest snapshot that lists it."""
    if SNAPSHOT not in df:
        return df
    newest = df.groupby(key)[SNAPSHOT].transform("max")
    return df[df[SNAPSHOT] == newest].drop(columns=SNAPSHOT)
