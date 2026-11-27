"""Rolling-window permit layers: every cached snapshot read, each permit's newest copy kept (synthetic)."""

import pandas as pd

from lotline.adapters import snapshots
from lotline.io import offline
from lotline.io.store import DataStore


def _store_with(tmp_path, vintages):
    store = DataStore(tmp_path)
    for v in vintages:
        folder = store.raw("src", v) / "layer"
        folder.mkdir(parents=True)
        (folder / "layer.json").write_text("{}")
    return store


def test_newest_rows_keeps_each_permits_newest_copy_and_rolled_out_permits():
    df = pd.DataFrame(
        {
            "permit": ["A", "A", "B", "C", "C"],  # A in both; B rolled out; C on two parcels today
            "status": ["Issued", "Closed", "Closed", "Issued", "Issued"],
            snapshots.SNAPSHOT: ["2026-10-14", "2026-11-11", "2026-10-14", "2026-11-11", "2026-11-11"],
        }
    )
    got = snapshots.newest_rows(df, "permit")
    assert got["permit"].tolist() == ["A", "B", "C", "C"]
    assert got.set_index("permit").loc["A", "status"] == "Closed"  # the newer status wins
    assert snapshots.SNAPSHOT not in got


def test_all_snapshots_reads_every_cached_vintage_from_disk_only(tmp_path):
    store = _store_with(tmp_path, ["2026-10-14", "2026-11-11"])
    (store.raw("src", "2026-12-01") / "layer").mkdir(parents=True)  # no layer.json: not a snapshot
    calls = []

    def read(vintage):
        calls.append((vintage, offline.is_offline()))
        return pd.DataFrame({"permit": [f"p{vintage}"]})

    got = snapshots.all_snapshots(read, store, "src", "layer")
    assert calls == [(None, False), ("2026-10-14", True), ("2026-11-11", True)]  # cached ones never online
    assert got[snapshots.SNAPSHOT].tolist() == ["2026-10-14", "2026-11-11"]


def test_an_incomplete_snapshot_is_skipped_not_mixed_in(tmp_path, capsys):
    store = _store_with(tmp_path, ["2026-10-14", "2026-11-11"])

    def read(vintage):
        if vintage == "2026-10-14":
            raise offline.SnapshotIncomplete("page 3 missing")
        return pd.DataFrame({"permit": ["x"]})

    got = snapshots.all_snapshots(read, store, "src", "layer")
    assert got[snapshots.SNAPSHOT].tolist() == ["2026-11-11"]
    assert "skipped snapshot 2026-10-14" in capsys.readouterr().out


def test_nothing_cached_falls_back_to_todays_copy(tmp_path):
    got = snapshots.all_snapshots(
        lambda v: pd.DataFrame({"permit": ["x"]}), DataStore(tmp_path), "src", "layer"
    )
    assert got["permit"].tolist() == ["x"]
