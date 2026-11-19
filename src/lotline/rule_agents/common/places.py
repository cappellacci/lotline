"""The places a rule run works on, for any category: the state's jurisdictions table, or a CSV the user gives.

A state the app has never seen has no jurisdictions table yet, so every swarm accepts `--jurisdictions <csv>`
with at least `geoid`, `name` and `pop_2020` (`county_geoid` and `kind` if known; `kind` defaults to `place`).
Found in the Burlington VT proof of concept, 2026-11-19: MM took a CSV, ADU only the table, fees only GEOIDs.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED = ("geoid", "name", "pop_2020")


def read_jurisdictions(state: str, csv: str | Path | None = None) -> pd.DataFrame | None:
    """The CSV when given (checked for the required columns), else the state's table; None if neither."""
    if csv:
        j = pd.read_csv(csv, dtype={"geoid": str, "county_geoid": str})
        missing = [c for c in REQUIRED if c not in j.columns]
        if missing:
            raise ValueError(f"{csv} lacks column(s) {missing}; it needs {list(REQUIRED)}")
        if "kind" not in j.columns:
            j["kind"] = "place"
        if "state" not in j.columns:
            j["state"] = state.upper()
        return j
    from lotline.io.store import DataStore

    return DataStore().read(state.lower(), "jurisdictions")
