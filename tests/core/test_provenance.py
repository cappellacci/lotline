import pandas as pd
import pytest

from lotline import provenance
from lotline.adapters.national import bps, fred
from lotline.io.store import DataStore, ManifestEntry


def _entry(source, path, url, **kw):
    base = dict(
        url=url,
        path=path,
        accessed_at="2026-10-06T14:00:00+00:00",
        sha256="0" * 64,
        bytes=1000,
        source=source,
        license="Public domain",
        adapter="national.x",
        adapter_version="1.0",
    )
    return ManifestEntry(**(base | kw))


def _store(tmp_path, entries):
    store = DataStore(tmp_path)
    for e in entries:
        store.record(e)
    return store


def test_render_has_every_required_column_and_adapter_notes(tmp_path):
    store = _store(
        tmp_path,
        [
            _entry(
                bps.SOURCE,
                f"raw/{bps.SOURCE}/{y}/mw{y}a.txt",
                f"https://x/mw{y}a.txt",
                last_modified="Thu, 14 May 2026 12:15:24 GMT",
            )
            for y in (2023, 2024, 2025)
        ]
        + [_entry(fred.SOURCE, f"raw/{fred.SOURCE}/2026-10/CPIAUCSL.csv", "https://x/cpi")],
    )
    doc = provenance.render(store.manifest())
    for col in (
        "Source (URL)",
        "Version",
        "Access date",
        "License / terms",
        "Cleaning steps",
        "Known limitations",
    ):
        assert col in doc
    assert "2023–2025 (3 vintages)" in doc and "last modified up to 2026-05-14" in doc
    assert bps.PROVENANCE["limitations"][0] in doc
    assert "Required attribution:** Mortgage rates: Freddie Mac" in doc  # FRED's attribution surfaces


def test_only_latest_entry_per_url_counts(tmp_path):
    store = _store(
        tmp_path,
        [
            _entry(
                bps.SOURCE,
                f"raw/{bps.SOURCE}/2024/a.txt",
                "https://x/a",
                accessed_at="2026-01-01T00:00:00+00:00",
            ),
            _entry(
                bps.SOURCE,
                f"raw/{bps.SOURCE}/2024/a.txt",
                "https://x/a",
                accessed_at="2026-10-06T00:00:00+00:00",
            ),
        ],
    )
    doc = provenance.render(store.manifest())
    assert "2026-10-06" in doc and "2026-01-01" not in doc


def test_unknown_source_is_an_error(tmp_path):
    store = _store(tmp_path, [_entry("mystery", "raw/mystery/1/a", "https://x/m")])
    with pytest.raises(provenance.ProvenanceError, match="mystery"):
        provenance.render(store.manifest())


def test_check_flags_stale_doc_and_undocumented_processed_tables(tmp_path):
    store = _store(tmp_path, [_entry(fred.SOURCE, f"raw/{fred.SOURCE}/2026-10/a.csv", "https://x/a")])
    doc = tmp_path / "data_provenance.md"
    assert any("out of date" in p for p in provenance.check(store, doc))
    provenance.write(store, doc)
    assert provenance.check(store, doc) == []
    out = store.processed("MN", "bps_place_year", "bps")  # a table from a source never downloaded
    out.parent.mkdir(parents=True)
    pd.DataFrame({"x": [1]}).to_parquet(out)
    assert any(bps.SOURCE in p for p in provenance.check(store, doc))
