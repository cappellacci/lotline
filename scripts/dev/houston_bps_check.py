"""Check Census BPS for Houston against the city's own permit counts (causal diagram v0.2, §6.5).

Run: `uv run python scripts/dev/houston_bps_check.py` → reports/mm-d038/houston_check.csv. Reads BPS and the
city's monthly summary only; fits nothing. Houston is a fit place, not a holdout.
"""

from pathlib import Path

from lotline.adapters.checks import houston_permits
from lotline.io import DataStore

HOUSTON = "4835000"
OUT = Path("reports/mm-d038/houston_check.csv")


def main() -> None:
    store = DataStore()
    city = houston_permits.load(store)
    bps = store.read("TX", "bps_place_year")
    b = bps[bps["geoid"] == HOUSTON].set_index("year")
    t = city.join(b[["bldgs_2", "units_1", "units_2", "bldgs_3_4", "units_3_4", "units_5p"]], how="inner")
    t["bps_3p_units"] = t["units_3_4"] + t["units_5p"]
    t["sf_city_over_bps"] = t["single_family"] / t["units_1"]
    t["mf_city_minus_bps_3p"] = t["multi_family"] - t["bps_3p_units"]  # compare with units_2
    t = t.loc[2010:]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.round(3).to_csv(OUT)
    print(t.round(2).to_string())


if __name__ == "__main__":
    main()
