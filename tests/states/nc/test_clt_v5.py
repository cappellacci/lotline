"""Charlotte V5 helper on synthetic rows: N1 translation (UDO Table 3-1) and the town prior (option b)."""

import pandas as pd
import pytest

from lotline.adapters.states.nc import clt_v5
from lotline.config import load_params


def test_translation_matches_udo_table_3_1():
    t = clt_v5.n1_translation()
    assert t == {"R-3": "N1-A", "R-4": "N1-B", "R-5": "N1-C", "R-6": "N1-D", "R-8": "N1-D", "UR-1": "N1-E"}


def test_conditional_and_other_districts_are_not_n1():
    z = pd.Series(["R-3", " r-5 ", "R-5(CD)", "R-8MF", "UR-2(CD)", None, "UR-1"])
    assert clt_v5.n1_district(z).tolist() == ["N1-A", "N1-C", pd.NA, pd.NA, pd.NA, pd.NA, "N1-E"]


def test_n1_lots_counts_charlotte_only():
    p = pd.DataFrame(
        {
            "parcel_id": ["a", "b", "c", "d", "e"],
            "jurisdiction_geoid": ["3712000", "3712000", "3712000", "37119", "3712000"],
            "zoning_raw": ["R-3", "R-3", "R-6", "R-3", "B-1"],
            "lot_sqft": [10000.0, 12000.0, 6000.0, 9000.0, 5000.0],
        }
    )
    out = clt_v5.n1_lots(p).set_index("n1")
    assert out.loc["N1-A", "lots"] == 2 and out.loc["N1-A", "median_lot_sqft"] == 11000.0
    assert out.loc["N1-D", "lots"] == 1 and len(out) == 2


def test_town_prior_hand_worked():
    # Town A: 4 kept parcels (house, house, vacant, house built 2024 → vacant); a shop is left out.
    # Town B: 2 kept parcels (house, church). Pooled: 3 houses / 6, 2 vacant / 6.
    p = pd.DataFrame(
        {
            "jurisdiction_geoid": ["A"] * 5 + ["B"] * 2,
            "land_use_std": ["SF_DETACHED", "SF_DETACHED", "VACANT_RESIDENTIAL", "SF_DETACHED", "COMMERCIAL",
                             "SF_DETACHED", "INSTITUTIONAL"],
            "year_built": pd.array([1990, 2001, None, 2024, 1980, 1975, 1950], dtype="Int64"),
        }
    )  # fmt: skip
    out = clt_v5.town_prior(p, towns={"A": "A", "B": "B"}).set_index("town")
    assert out.loc["A", "parcels"] == 4
    assert out.loc["A", "sf_share"] == pytest.approx(0.5)
    assert out.loc["A", "vacant_share"] == pytest.approx(0.5)
    assert out.loc["B", "sf_share"] == pytest.approx(0.5) and out.loc["B", "vacant_share"] == 0
    assert out.loc["pooled", "sf_share"] == pytest.approx(3 / 6)
    assert out.loc["pooled", "vacant_share"] == pytest.approx(2 / 6)


def test_params_are_ranges_from_the_towns():
    p = load_params("v5_charlotte")
    assert set(p) == {"n1_sf_share", "n1_vacant_share"}
    for v in p.values():
        assert 0 < v.low < v.value < v.high < 1
