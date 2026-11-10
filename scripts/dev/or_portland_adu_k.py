"""Counts behind §2.3 of `reports/or/adu-coverage-and-undercount.md`: Portland's flag undercount k.

    uv run python scripts/dev/or_portland_adu_k.py

Descriptive counts only (data thread): no engine, scenario or calibration run. Downloads the RLIS Housing
inventory's ADU rows through the IO layer (non-personal fields only; logged in manifest.jsonl) and reads
Portland's processed permits through `holdout.apply`. The rule is the report's §2.2 (committed before this
script was run) and `lotline.adapters.checks.rlis_housing`. Writes aggregates only to
`reports/or/portland-adu-k.json`; no tax-lot-level table is written.
"""

from __future__ import annotations

import json
from pathlib import Path

from lotline.adapters.checks import rlis_housing as rh
from lotline.io import DataStore
from lotline.validation import holdout

PORTLAND = "4159000"
OUT = Path(__file__).resolve().parents[2] / "reports" / "or" / "portland-adu-k.json"


def main() -> None:
    store = DataStore()
    housing = rh.download(store)
    permits = store.read("OR", "permits")
    permits = holdout.apply(permits, "OR", geoid_col="jurisdiction_geoid", date_col="issue_date")
    permits = permits[permits["jurisdiction_geoid"] == PORTLAND]
    portland = housing[housing["JURIS_CITY"].str.upper() == "PORTLAND"]
    keys = rh.taxlot_key(portland["TLID"])
    out = {
        "inventory_adu_rows": int(len(housing)),
        "portland_adu_rows": int(len(portland)),
        "portland_rows_by_source": portland["DATASOURCE"].value_counts().to_dict(),
        "portland_tlid_unkeyed": int(keys.isna().sum()),
        "permit_rows_unkeyed": int(rh.taxlot_key(permits["parcel_id"]).isna().sum()),
        "central": rh.compare(rh.independent_lots(housing), permits),
        "sens_no_adu_study": rh.compare(rh.independent_lots(housing, drop_study=True), permits),
        "sens_high_confidence": rh.compare(rh.independent_lots(housing, high_only=True), permits),
        "sens_2016_on": rh.compare(rh.independent_lots(housing, built_from=2016), permits, first_year=2016),
    }
    # where the flagged lots that are not in R sit: in the inventory through permit-based rows, or absent
    all_keys = set(keys.dropna())
    permit_keys = set(
        rh.taxlot_key(portland.loc[portland["DATASOURCE"].isin(rh.PERMIT_SOURCES), "TLID"]).dropna()
    )
    w = permits[permits["issue_year"].between(1995, 2025) & permits["adu_type"].notna()]
    p_only = set(rh.taxlot_key(w["parcel_id"]).dropna()) - set(rh.independent_lots(housing))
    out["permits_only_split"] = {
        "in_inventory_permit_rows": len(p_only & permit_keys),
        "in_inventory_other_rows": len((p_only & all_keys) - permit_keys),
        "not_in_inventory": len(p_only - all_keys),
    }
    out["portland_tlid_blank"] = int(
        portland["TLID"].astype("string").str.strip().replace("", None).isna().sum()
    )
    OUT.write_text(json.dumps(out, indent=2, default=float) + "\n")
    print(json.dumps(out, indent=2, default=float))


if __name__ == "__main__":
    main()
