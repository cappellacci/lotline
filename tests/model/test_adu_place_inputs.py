"""ADU switch-over to `place_inputs` (WS-SCALE, contract-change #455): `adu.places_from_store` reads the
shared per-place inputs from the stored table at year == origin, and builds that year itself when the table
is absent.

Synthetic state "ZZ" (fixture `zz` in tests/conftest.py)."""

import pandas as pd

from lotline.build import place_inputs
from lotline.model.scenarios import adu


def _store_table(store, df):
    path = store.processed("zz", place_inputs.TABLE, "synthetic")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def test_without_a_stored_table_it_builds_the_origin_year(zz):
    assert zz.read("ZZ", place_inputs.TABLE) is None
    a = adu.places_from_store("ZZ", zz, 2025).set_index("geoid")
    t = place_inputs.build("ZZ", zz, [2025]).set_index("geoid")
    pd.testing.assert_series_equal(t.loc[a.index, "rent"], a["rent"], check_names=False, check_dtype=False)
    assert (t.loc[a.index, "eligible_parcels_adu"] == a["eligible_parcels"]).all()


def test_adu_reads_the_stored_table(zz):
    t = place_inputs.build("ZZ", zz, [2024, 2025])
    g = t.loc[(t["year"] == 2025) & (t["eligible_parcels_adu"].fillna(0) > 0), "geoid"].iloc[0]
    hit = (t["geoid"] == g) & (t["year"] == 2025)
    # mark one place in the stored table: twice the rent, 7 eligible lots, and a core city
    t.loc[hit, "rent"] = t.loc[hit, "rent"] * 2
    t.loc[hit, "eligible_parcels_adu"] = 7.0
    t.loc[hit, "place_type"] = adu.CORE
    before = adu.places_from_store("ZZ", zz, 2025).set_index("geoid")
    _store_table(zz, t)
    after = adu.places_from_store("ZZ", zz, 2025).set_index("geoid")
    assert after.loc[g, "rent"] == 2 * before.loc[g, "rent"]
    assert after.loc[g, "eligible_parcels"] == 7.0
    assert after.loc[g, "place_type"] == t.loc[hit, "place_type"].iloc[0]
    others = after.index != g
    # nothing else moves
    pd.testing.assert_series_equal(after.loc[others, "rent"], before.loc[others, "rent"])


def test_only_the_origin_year_is_read(zz):
    t = place_inputs.build("ZZ", zz, [2024, 2025])
    t.loc[t["year"] == 2024, "rent"] = 1.0  # a different origin's row must not leak in
    _store_table(zz, t)
    a = adu.places_from_store("ZZ", zz, 2025)
    assert (a["rent"] != 1.0).all()
