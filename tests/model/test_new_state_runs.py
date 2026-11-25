"""WS-SCALE task 0: a new state with national data only runs end to end.

A synthetic tier-3 state "ZZ" has no permit table, no `config/reforms/zz.csv` and is not in
`adu.REFORM_STATES`. Its bundle builds, is labelled `national_only`, and it borrows the listed states' rule
priors without feeding them ("borrow only", Ben 2026-11-17). All data is synthetic; the five listed states get
only a `jurisdictions` table (every GEOID in their reform files, population 20,000).
"""

from __future__ import annotations

import pandas as pd
import pytest

from lotline.config import CONFIG_DIR
from lotline.model.scenarios import adu


def test_reforms_of_an_unlisted_state_without_a_file_are_empty():
    assert "ZZ" not in adu.REFORM_STATES
    r = adu.load_reforms("ZZ")
    assert r.empty and {"reform_id", "jurisdiction_geoid", "theme", "effective_date"} <= set(r)
    with pytest.raises(FileNotFoundError):  # a listed state must have its file
        adu.load_reforms("MN", config_dir=CONFIG_DIR / "no-such-dir")


def test_borrow_only_the_new_state_feeds_no_pool():
    every = adu.reforms_with("ZZ", load=lambda st: pd.DataFrame({"st": [st]}))
    assert list(every) == [*adu.REFORM_STATES, "ZZ"]
    assert list(adu.pooled_states(every)) == list(adu.REFORM_STATES)
    assert list(adu.reforms_with("MN", load=lambda st: pd.DataFrame())) == list(adu.REFORM_STATES)


def test_no_permit_table_means_no_observed_adus():
    assert adu.observed_adu_counts(None, 2018, 2025).empty
    out = adu.observed_adu_counts(None, 2018, 2025, undercount=object())
    assert out.empty and {"geoid", "year", "adu_permits", "source", "counted", "k_row"} <= set(out)


def test_a_new_national_only_state_builds_a_bundle(zz):
    from lotline.model import results

    assert zz.read("zz", "permits") is None
    bundle = results.build_bundle("ZZ", zz, draws=20)
    meta = bundle["meta"].iloc[0]
    assert meta["state_role"] == "national_only" and bool(meta["eligible_proxy"])
    assert int(meta["data_tier"]) == 3
    results.validate_bundle(bundle)
    seen = bundle["observed"]
    assert "adu_permits" not in set(seen["measure"])  # no permits, so no observed ADU rows


def test_the_new_state_borrows_priors_without_moving_them(zz):
    _, with_zz = adu.rule_inputs("ZZ", zz, ["9900001", "9900002", "9900003"], pd.Timestamp("2025-12-31"))
    _, without = adu.rule_inputs("MN", zz, [], pd.Timestamp("2025-12-31"))
    pr = with_zz["priors"]
    pd.testing.assert_frame_equal(pr[pr["state"] != "ZZ"].reset_index(drop=True), without["priors"])
    own = pr[pr["state"] == "ZZ"]  # the new state reads every coded place by size band, not one pooled mean
    assert sorted(own["band"]) == [0, 1, 2] and own["source"].str.startswith("all states").all()
    assert "ZZ" not in set(with_zz["coded"]["state"])
