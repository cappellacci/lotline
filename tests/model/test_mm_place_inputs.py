"""Missing middle reads its per-place inputs from `place_inputs` (WS-SCALE switch-over).

Synthetic state "ZZ" (fixture `zz` in tests/conftest.py). The stored table is edited by hand so each test
can see which value the scenario picked up.
"""

import pandas as pd

from lotline.build import place_inputs
from lotline.model.scenarios import mm

ALPHA, BETA, GAMMA = "9900001", "9900002", "9900003"


def _store_table(zz, edit) -> None:
    t = place_inputs.build("ZZ", zz, years=[2025])
    edit(t)
    path = zz.processed("zz", place_inputs.TABLE, "synthetic")
    path.parent.mkdir(parents=True, exist_ok=True)
    t.to_parquet(path, index=False)


def test_reads_the_stored_table(zz):
    def edit(t):
        t.loc[t["geoid"] == ALPHA, "house_share"] = 0.25
        t.loc[t["geoid"] == ALPHA, "rent"] = 2_000.0
        t.loc[t["geoid"] == ALPHA, "size_band"] = 2

    _store_table(zz, edit)
    p = mm.places_from_store("ZZ", zz, 2025).set_index("geoid")
    assert p.at[ALPHA, "house_share"] == 0.25 and p.at[ALPHA, "house_share_source"] == "roll"
    assert p.at[ALPHA, "rent"] == 2_000.0 and p.at[ALPHA, "band"] == 2


def test_without_the_table_builds_the_origin_year(zz):
    built = mm.places_from_store("ZZ", zz, 2025)
    _store_table(zz, lambda t: None)
    pd.testing.assert_frame_equal(mm.places_from_store("ZZ", zz, 2025), built)


def test_keeps_a_place_whose_lots_all_overlap(zz):
    """The place set is every place with eligible lots before the D-020 overlap is removed: a remainder left
    with 0 lots stays in (0 homes), one with no lots at all is out."""

    def edit(t):
        t.loc[t["geoid"] == BETA, ["eligible_parcels_mm", "overlap_removed_mm"]] = [0.0, 2_500.0]
        t.loc[t["geoid"] == GAMMA, ["eligible_parcels_mm", "eligible_parcels_reported_mm"]] = [0.0, 0.0]

    _store_table(zz, edit)
    p = mm.places_from_store("ZZ", zz, 2025).set_index("geoid")
    assert BETA in p.index and p.at[BETA, "eligible"] == 0.0
    assert GAMMA not in p.index


def test_house_share_fill_rule(zz):
    """MM's fill: a missing share is 1 on an ACS-fallback denominator (houses only), else the median.
    By hand: ZZ's denominators are all ACS fallback, so a blank share becomes 1, not the median 0.5."""

    def edit(t):
        t.loc[t["geoid"] == ALPHA, "house_share"] = None
        t.loc[t["geoid"] == BETA, "house_share"] = 0.5

    _store_table(zz, edit)
    p = mm.places_from_store("ZZ", zz, 2025).set_index("geoid")
    assert p.at[ALPHA, "house_share"] == 1.0 and p.at[ALPHA, "house_share_source"] == "acs_houses_only"
    assert p.at[BETA, "house_share"] == 0.5
