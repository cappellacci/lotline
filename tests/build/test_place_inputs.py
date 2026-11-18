"""WS-SCALE task 4: `place_inputs` reproduces the per-place inputs the models compute today.

Synthetic state "ZZ" (fixture `zz` in tests/conftest.py). For origin 2025, each shared column equals what
`adu.places_from_store` and `mm.places_from_store` compute themselves, place for place.
"""

import numpy as np
import pandas as pd

from lotline.build import place_inputs
from lotline.model.scenarios import adu, mm


def _at(table, year):
    return table[table["year"] == year].set_index("geoid")


def test_one_row_per_jurisdiction_and_year(zz):
    t = place_inputs.build("ZZ", zz, years=[2020, 2025])
    assert not t.duplicated(place_inputs.KEY).any()
    assert len(t) == 4 * 2 and set(t["state"]) == {"ZZ"}
    assert list(t.columns[:3]) == place_inputs.KEY


def test_default_years_are_the_bps_years(zz):
    assert sorted(place_inputs.build("ZZ", zz)["year"].unique()) == list(range(2010, 2026))


def test_matches_the_adu_model_inputs(zz):
    t = _at(place_inputs.build("ZZ", zz, years=[2025]), 2025)
    a = adu.places_from_store("ZZ", zz, 2025).set_index("geoid")
    pairs = {
        "eligible_parcels_adu": "eligible_parcels",
        "eligible_parcels_reported_adu": "eligible_parcels_reported",
        "overlap_removed_adu": "overlap_removed",
        "parcels_year_adu": "parcels_year",
        "denominator_source_adu": "denominator_source",
        "acs_geo": "acs_geo",
        "rent": "rent",
        "home_value": "home_value",
        "acs_end_year": "acs_end_year",
    }
    for mine, theirs in pairs.items():
        pd.testing.assert_series_equal(
            t.loc[a.index, mine], a[theirs], check_names=False, check_dtype=False, obj=mine
        )
    obs = t.loc[a.index, "observed_adu_per_year"]
    assert np.allclose(obs.fillna(-1), a["observed_adu_per_year"].fillna(-1))


def test_matches_the_mm_model_inputs(zz):
    t = _at(place_inputs.build("ZZ", zz, years=[2025]), 2025)
    m = mm.places_from_store("ZZ", zz, 2025).set_index("geoid")
    for mine, theirs in {
        "eligible_parcels_mm": "eligible_parcels",
        "parcels_year_mm": "parcels_year",
        "size_band": "band",
        "rent": "rent",
    }.items():
        pd.testing.assert_series_equal(
            t.loc[m.index, mine], m[theirs], check_names=False, check_dtype=False, obj=mine
        )


def test_models_flag_says_who_reads_each_row(zz):
    t = _at(place_inputs.build("ZZ", zz, years=[2025]), 2025)
    assert set(t["models"]) == {"adu;missing_middle;fees;baseline"}
    assert t["models_note"].isna().all()
    df = pd.DataFrame(
        {"eligible_parcels_adu": [5.0, np.nan], "rent": [np.nan, 900.0], "home_value": [1.0, 1.0],
         "eligible_parcels_mm": [3.0, np.nan], "in_bps": [True, False]}
    )  # fmt: skip
    f = place_inputs._flag_models(df)
    assert f["models"].tolist() == ["missing_middle;fees;baseline", ""]
    assert "no ACS rent" in f.loc[0, "models_note"] and "not a BPS place" in f.loc[1, "models_note"]
