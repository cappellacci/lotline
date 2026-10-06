"""IO layer: download cache under LOTLINE_DATA_DIR, manifest.jsonl, HTTP helpers.

Every download goes through `fetch()` so it is cached and recorded in the manifest (BUILD_PLAN §4).
"""

from lotline.io.http import fetch
from lotline.io.store import DataStore, data_dir

__all__ = ["DataStore", "data_dir", "fetch"]
