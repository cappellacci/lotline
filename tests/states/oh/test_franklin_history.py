"""scripts/dev/oh_franklin_history.py: parcel-ID matching, district fallback and the comparison (S6a).

Synthetic rows only; each expected value is worked by hand in the comment beside it.
"""

import importlib.util
from pathlib import Path

import pandas as pd

_spec = importlib.util.spec_from_file_location(
    "oh_franklin_history",
    Path(__file__).resolve().parents[3] / "scripts" / "dev" / "oh_franklin_history.py",
)
fh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fh)


def test_roll_id_drops_the_card_suffix():
    ids = pd.Series(["010-023573-00", " 070-000123-00 ", "not a parcel"])
    assert fh.roll_id(ids).tolist()[:2] == ["39049010-023573", "39049070-000123"]
    assert pd.isna(fh.roll_id(ids).iloc[2])


def test_place_uses_roll_then_a_dominant_district():
    # district 010: 20 parcels, all in A → share 1.0, used for unmatched 010 parcels
    # district 020: 19 in B and 1 in C → share 0.95, just at DISTRICT_SHARE, used
    # district 030: 1 in B and 1 in C → share 0.5, not used
    roll = pd.DataFrame(
        {
            "parcel_id": [f"39049010-{i:06d}" for i in range(20)]
            + [f"39049020-{i:06d}" for i in range(20)]
            + ["39049030-000000", "39049030-000001"],
            "jurisdiction_geoid": ["A"] * 20 + ["B"] * 19 + ["C"] + ["B", "C"],
        }
    )
    archive = pd.DataFrame(
        {"parcel_id": ["39049020-000019", "39049010-999999", "39049020-999999", "39049030-999999"]}
    )
    # matched parcel keeps its roll jurisdiction (C), even inside a B-dominated district
    assert fh.place(archive, roll).tolist()[:3] == ["C", "A", "B"]
    assert pd.isna(fh.place(archive, roll).iloc[3])


def test_compare_gap_and_size_filter():
    real = pd.DataFrame(
        {
            "jurisdiction_geoid": ["J"] * 2 + ["S"] * 2,
            "year": [2019, 2023] * 2,
            "theme": "adu",
            "real": [1000, 1100, 50, 55],
        }
    )
    eligible = pd.DataFrame(
        {
            "jurisdiction_geoid": ["J"] * 2 + ["S"] * 2,
            "year": [2019, 2023] * 2,
            "theme": "adu",
            "eligible_parcels": [1050, 1100, 50, 55],
            "denominator_source": ["parcels_scaled_acs", "parcels"] * 2,
        }
    )
    t = fh.compare(real, eligible, pd.Series({"J": "Jville", "S": "Small"}), pd.Series({"J": 0.8, "S": 1.0}))
    # S has 55 < MIN_ELIGIBLE (1000) eligible lots in 2023 → dropped
    assert set(t["name"]) == {"Jville"}
    # 2019: scaled 1050 vs real 1000 → +5%; 2023 roll year: 1100 vs 1100 → 0
    assert t.set_index("year")["gap_pct"].round(6).to_dict() == {2019: 5.0, 2023: 0.0}
    # J has 80% of its houses in the county: 2019 whole ≈ 1000 / 0.8 = 1250, scaled 1050 → -16%
    assert round(t.set_index("year").loc[2019, "gap_adj_pct"], 6) == -16.0
    g = fh.growth(t, 2019, 2023).loc["adu"].loc["Jville"]
    # real 1000 → 1100 = +10%; scaled 1050 → 1100 = +4.8%
    assert (g["real_growth_pct"], g["scaled_growth_pct"]) == (10.0, 4.8)


def test_county_share_counts_only_houses_of_places_reaching_the_county():
    parcels = pd.DataFrame(
        {
            "jurisdiction_geoid": ["D", "D", "D", "D", "D", "O"],
            "county_geoid": ["39049", "39049", "39049", "39041", "39049", "39041"],
            "land_use_std": ["SF_DETACHED"] * 4 + ["COMMERCIAL", "SF_DETACHED"],
        }
    )
    # D: 3 of its 4 houses in Franklin (the commercial parcel is ignored) → 0.75; O never reaches it
    assert fh.county_share(parcels).to_dict() == {"D": 0.75}
