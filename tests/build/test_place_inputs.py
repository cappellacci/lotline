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


def test_place_tags_match_the_adu_model_and_mark_sources(zz):
    t = _at(place_inputs.build("ZZ", zz, years=[2025]), 2025)
    a = adu.places_from_store("ZZ", zz, 2025).set_index("geoid")
    assert (t.loc[a.index, "place_type"] == a["place_type"]).all()
    assert set(t["place_type_source"]) <= {"acs_cbsa", "default_town"}
    assert not t["is_holdout"].any()  # ZZ has no holdouts
    assert t["parcel_sources"].isna().all() and t["permit_sources"].isna().all()  # national data only
    assert t["hpi_geo"].notna().all()  # falls back to the state series


def test_sources_are_sorted_and_joined():
    juris = pd.DataFrame({"geoid": ["1", "2"]})
    permits = pd.DataFrame({"jurisdiction_geoid": ["1", "1", "1", None], "source": ["b", "a", "b", "c"]})

    class Store:
        def read(self, state, table):
            return None

    import lotline.model.adu_types as at

    real = at.jurisdiction_types
    at.jurisdiction_types = lambda store, state: pd.Series({"1": "core"})
    try:
        tags = place_inputs.place_tags("MN", Store(), juris, None, permits).set_index("geoid")
    finally:
        at.jurisdiction_types = real
    assert tags.loc["1", "permit_sources"] == "a;b" and pd.isna(tags.loc["2", "permit_sources"])
    assert tags["place_type"].tolist() == ["core", "town"]
    assert tags["place_type_source"].tolist() == ["acs_cbsa", "default_town"]


def test_registered_as_the_last_build_step_and_validates(zz):
    from lotline import registry
    from lotline.schemas import validate

    names = [s.name for s in registry._national()]
    assert names[-1] == "place_inputs"
    out = validate(place_inputs.build("ZZ", zz, years=[2024, 2025]), "place_inputs")
    assert len(out) == 8 and out["models"].str.len().gt(0).all()


def test_plain_fetch_builds_place_inputs_after_every_other_source(monkeypatch, tmp_path):
    """`lotline fetch --state XX` runs sources in name order, but place_inputs reads every other table, so it
    goes last (`RUN_LAST`), after e.g. `rlis_parcels` and `portland_permits`."""
    import types

    from lotline import cli, registry
    from lotline.registry import Source

    ran = []

    def module(name, last=False):
        def load(state, store, refresh=False):
            ran.append(name)
            return pd.DataFrame()

        return types.SimpleNamespace(SOURCE=name, load=load, RUN_LAST=last)

    fake = {
        n: Source(n, module(n, n == "place_inputs"), "t", None)
        for n in ("acs", "place_inputs", "portland_permits", "rlis_parcels")
    }
    monkeypatch.setattr(registry, "sources_for", lambda state: fake)
    monkeypatch.setattr("lotline.validation.holdout.assert_no_leak", lambda df, table, state: None)
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(tmp_path))
    assert cli.main(["fetch", "--state", "OR"]) == 0
    assert ran == ["acs", "portland_permits", "rlis_parcels", "place_inputs"]
