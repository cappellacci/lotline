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


def _saved_from(store, tmp_path, monkeypatch, years=(2025,)):
    """The calibration step's two tables built from `store` (here the synthetic one) into a temp folder that
    `saved_priors` reads."""
    from lotline.model.scenarios import adu_rule_inputs as ri

    for name, text in ri.borrowed_pools(store, years).items():
        (tmp_path / name).write_text(text)
    monkeypatch.setattr(ri, "PRIORS_DIR", tmp_path)


def test_the_new_state_borrows_priors_without_moving_them(zz, tmp_path, monkeypatch):
    _saved_from(zz, tmp_path, monkeypatch)
    _, with_zz = adu.rule_inputs("ZZ", zz, ["9900001", "9900002", "9900003"], pd.Timestamp("2025-12-31"))
    _, without = adu.rule_inputs("MN", zz, [], pd.Timestamp("2025-12-31"))
    pr = with_zz["priors"]
    pd.testing.assert_frame_equal(pr[pr["state"] != "ZZ"].reset_index(drop=True), without["priors"])
    own = pr[pr["state"] == "ZZ"]  # the new state reads every coded place by size band, not one pooled mean
    assert sorted(own["band"]) == [0, 1, 2] and own["source"].str.startswith("all states").all()
    assert "ZZ" not in set(with_zz["coded"]["state"])
    pd.testing.assert_frame_equal(with_zz["field_counts"], without["field_counts"], check_dtype=False)


def test_the_new_state_reads_no_other_state_table(zz, tmp_path, monkeypatch):
    """Ben 2026-11-27: a new state's results don't depend on what else is in the data folder. With the saved
    tables, ZZ's rule inputs read only ZZ's own tables."""
    _saved_from(zz, tmp_path, monkeypatch)
    read = []
    real = zz.read
    monkeypatch.setattr(zz, "read", lambda st, table: read.append(st.upper()) or real(st, table))
    adu.rule_inputs("ZZ", zz, ["9900001", "9900002", "9900003"], pd.Timestamp("2025-12-31"))
    assert set(read) <= {"ZZ"}


def test_an_origin_with_no_saved_priors_is_an_error(zz, tmp_path, monkeypatch):
    _saved_from(zz, tmp_path, monkeypatch)
    with pytest.raises(KeyError, match="no saved ADU rule priors for origin 2014"):
        adu.rule_inputs("ZZ", zz, ["9900001"], pd.Timestamp("2015-12-31"), pd.Timestamp("2014-12-31"))
    with pytest.raises(ValueError, match="31 December"):
        adu.rule_inputs("ZZ", zz, ["9900001"], pd.Timestamp("2025-06-30"))


def test_saved_priors_label_the_borrowed_rows_for_the_state(tmp_path, monkeypatch):
    """By hand: a saved year with one listed-state row (MN band 0) and three borrowed rows (state "*");
    for Wisconsin the "*" rows come back as WI and the MN row is untouched; counts come back as saved."""
    from lotline.model.scenarios import adu_rule_inputs as ri

    p = "0.5,0.1,0.1,0.1,0.2,0.3"
    (tmp_path / ri.PRIORS_FILE).write_text(
        "origin,state,band,n_coded,source,p_none,p_owner,p_other,p_both,p_handbook,p_partial\n"
        f"2020,MN,0,9,state and band,{p}\n"
        + "".join(f'2020,*,{b},4,"all states, band",{p}\n' for b in range(3))
        + f'2019,*,0,1,"all states, band",{p}\n'
    )
    (tmp_path / ri.COUNTS_FILE).write_text("origin,state,field,known,restricting\n2020,MN,owner_occ,10,4\n")
    monkeypatch.setattr(ri, "PRIORS_DIR", tmp_path)
    counts, priors = ri.saved_priors("WI", pd.Timestamp("2020-12-31"))
    assert priors["state"].tolist() == ["MN", "WI", "WI", "WI"]
    assert priors["band"].tolist() == [0, 0, 1, 2]
    assert counts.to_dict("records") == [{"state": "MN", "field": "owner_occ", "known": 10, "restricting": 4}]
