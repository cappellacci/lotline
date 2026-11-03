"""Do Austin's post-HOME 2-unit counts hold ADUs? (causal diagram v0.2, §6.6)

Run: `uv run python scripts/dev/austin_permit_class_check.py` → reports/mm-d038/austin_check.csv. Counts the
city's new-building permits by Census class (101 house, 102 secondary apartment = ADU, 103 two-family,
104 three-four) per year next to BPS 2-unit buildings. Reads stored tables only; fits nothing.
"""

from pathlib import Path

from lotline.io import DataStore

AUSTIN = "4805000"
CLASSES = {"101": "house", "102": "adu", "103": "two_family", "104": "three_four"}
OUT = Path("reports/mm-d038/austin_check.csv")


def main() -> None:
    store = DataStore()
    p = store.read("TX", "permits")
    p = p[(p["source"] == "austin_permits") & (p["jurisdiction_geoid"] == AUSTIN) & ~p["is_demolition"]]
    p = p.assign(code=p["permit_class_raw"].str.extract(r"(\d{3})", expand=False))
    p = p[p["code"].isin(CLASSES) & p["issue_year"].between(2015, 2025)]
    t = p.groupby(["issue_year", "code"]).size().unstack("code").rename(columns=CLASSES).fillna(0).astype(int)
    t["adu_plus_two_family"] = t["adu"] + t["two_family"]
    flags = p[p["reform_flag_raw"].notna()].groupby("issue_year").size()
    t["two_or_three_unit_res_flag"] = flags.reindex(t.index).fillna(0).astype(int)
    bps = store.read("TX", "bps_place_year")
    t["bps_bldgs_2"] = bps[bps["geoid"] == AUSTIN].set_index("year")["bldgs_2"].reindex(t.index)
    t.index.name = "year"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT)
    print(t.to_string())


if __name__ == "__main__":
    main()
