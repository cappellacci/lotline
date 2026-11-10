#!/usr/bin/env python3
"""Austin residential addition permits (class 434/435), 2018-07 to 2025, for the group-(b) check (report §2).

    uv run python scripts/dev/tx_austin_additions_fetch.py

The `austin_permits` adapter downloads only classes that add or remove dwellings (101-106, 436, 645-649).
An attached ADU or a guest suite can be filed as an addition (R-434 "Addition & Alterations", R-435
"Addns of residential garages/carports"), so this downloads those permits for the k window through the IO
layer (`lotline.io.socrata.download_dataset`, manifest entry under source `austin_permits`, name
`additions_434_435`). Same non-personal fields as the adapter: no names, addresses or legal description.
Nothing is written to the processed tables; `tx_austin_adu_k.py --additions` reads the raw pages.
"""

from __future__ import annotations

from lotline.adapters.states.tx import austin_permits as ap
from lotline.io import DataStore
from lotline.io.socrata import download_dataset

WHERE = (
    "permittype = 'BP' AND (permit_class LIKE 'R- 434 %' OR permit_class LIKE 'R- 435 %') "
    "AND issue_date >= '2018-07-01T00:00:00' AND issue_date < '2026-01-01T00:00:00'"
)


def fetch(store: DataStore | None = None):
    return download_dataset(
        ap.DOMAIN, ap.DATASET_ID, select=ap.SELECT, where=WHERE, store=store or DataStore(),
        source=ap.SOURCE, license=ap.LICENSE, adapter="dev.tx_austin_additions_fetch", adapter_version="1.0",
        name="additions_434_435",
    )  # fmt: skip


if __name__ == "__main__":
    df = fetch()
    print(len(df), df["permit_class"].value_counts().head().to_dict())
