"""Every state settings file (`config/states/<st>.yaml`) passes the schema and agrees with the repo.

`load_state` checks each file's own shape (pydantic, extra keys forbidden). These tests add what one file
can't check alone (WS-SCALE task 2, issue #455): GEOIDs belong to the state, files the settings name exist,
source names are real sources, and no two states claim the same FIPS code or ZIP prefixes. Parametrized
over `all_states()`, so a new state's file is checked with no test edit.
"""

from __future__ import annotations

import pandas as pd
import pytest

from lotline.config import CONFIG_DIR, all_states, load_state
from lotline.registry import sources_for

STATES = all_states()
BPS_REGIONS = {"Northeast Region", "Midwest Region", "South Region", "West Region"}


def _is_geoid(state_fips: str, geoid: str, lengths=(7, 10)) -> bool:
    return geoid.isdigit() and len(geoid) in lengths and geoid.startswith(state_fips)


def test_the_five_states_are_checked():
    assert {"MN", "NC", "OH", "OR", "TX"} <= set(STATES)


@pytest.mark.parametrize("state", STATES)
def test_file_loads_and_names_itself(state):
    cfg = load_state(state)
    assert cfg.state == state
    assert cfg.bps_region in BPS_REGIONS
    assert cfg.name.strip() == cfg.name and cfg.name


@pytest.mark.parametrize("state", STATES)
def test_every_geoid_belongs_to_the_state(state):
    cfg = load_state(state)
    bad = {
        "holdouts": [
            h.geoid
            for h in cfg.holdouts
            if not (h.geoid == cfg.fips if h.statewide else _is_geoid(cfg.fips, h.geoid))
        ],
        "reporting_geoids": [
            g for h in cfg.holdouts for g in h.reporting_geoids if not _is_geoid(cfg.fips, g, (5, 7, 10))
        ],
        "local_jurisdictions": [g for g in cfg.local_jurisdictions if not _is_geoid(cfg.fips, g)],
        "data_tiers": [g for g in cfg.data_tiers if not _is_geoid(cfg.fips, g, (5, 7, 10))],
        "train_until": [g for g in cfg.train_until if not _is_geoid(cfg.fips, g)],
        "parcel_sources": [
            g for g in cfg.parcel_sources if g != "*" and not _is_geoid(cfg.fips, g, (5, 7, 10))
        ],
    }
    assert not {k: v for k, v in bad.items() if v}, f"{state}: GEOIDs outside the state or malformed"


@pytest.mark.parametrize("state", STATES)
def test_holdout_ids_name_the_state(state):
    cfg = load_state(state)
    ids = [h.test_id for h in cfg.holdouts]
    assert all(t.split("-")[1] == state for t in ids)
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("state", STATES)
def test_data_tiers_and_local_names_are_well_formed(state):
    cfg = load_state(state)
    assert set(cfg.data_tiers.values()) <= {1, 2, 3}
    assert all(name.strip() for name in cfg.local_jurisdictions.values())


@pytest.mark.parametrize("state", STATES)
def test_parcel_sources_name_real_parcel_sources(state):
    cfg = load_state(state)
    if not cfg.parcel_sources:
        return
    assert "*" in cfg.parcel_sources, f"{state}: parcel_sources needs a '*' default for the other places"
    known = {getattr(s.module, "SOURCE", None) for s in sources_for(state).values()}
    unknown = set(cfg.parcel_sources.values()) - known
    assert not unknown, f"{state}: parcel_sources names unknown sources {sorted(unknown)}"


@pytest.mark.parametrize("state", STATES)
def test_named_files_exist(state):
    cfg = load_state(state)
    if cfg.land_use_crosswalk:
        assert (CONFIG_DIR.parent / cfg.land_use_crosswalk).is_file(), cfg.land_use_crosswalk


@pytest.mark.parametrize("state", STATES)
def test_aliases_point_inside_the_state(state):
    path = CONFIG_DIR / "crosswalks" / f"{state.lower()}_aliases.csv"
    if not path.exists():
        return
    fips = load_state(state).fips
    geoids = pd.read_csv(path, dtype=str)["geoid"]
    assert geoids.map(lambda g: _is_geoid(fips, g, (5, 7, 10))).all()


@pytest.mark.parametrize("state", STATES)
def test_sources_are_documented(state):
    cfg = load_state(state)
    names = [s.name for s in cfg.sources]
    assert len(names) == len(set(names)), f"{state}: duplicate source names"
    assert all(s.url.startswith(("http://", "https://")) for s in cfg.sources)
    assert all(s.license.strip() for s in cfg.sources)


@pytest.mark.parametrize("state", STATES)
def test_zip3_ranges_are_ordered(state):
    for lo, hi in load_state(state).zip3_ranges:
        assert 0 <= lo <= hi <= 999


def test_states_do_not_share_fips_or_zip_prefixes():
    cfgs = [load_state(s) for s in STATES]
    fips = [c.fips for c in cfgs]
    assert len(fips) == len(set(fips))
    owner: dict[int, str] = {}
    for c in cfgs:
        for lo, hi in c.zip3_ranges:
            for z in range(lo, hi + 1):
                assert z not in owner, f"ZIP prefix {z:03d} is in both {owner[z]} and {c.state}"
                owner[z] = c.state


@pytest.mark.parametrize("state", STATES)
def test_rules_name_modules_that_exist_and_read_them(state):
    """Every named adapter rule (task 8) lists modules that exist and mention the rule id."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "src" / "lotline"
    modules = {p.stem: p for p in [*src.glob("adapters/states/*/*.py"), *src.glob("build/*.py")]}
    for rule_id, rule in load_state(state).rules.items():
        for name in rule.used_by:
            assert name in modules, f"{state} rule {rule_id}: no module {name}"
        readers = [n for n in rule.used_by if f'"{rule_id}"' in modules[n].read_text()]
        assert readers, f"{state} rule {rule_id}: none of {rule.used_by} reads it"
        assert rule.source.strip() and rule.what.strip() and rule.assumption.strip()


def test_rule_range_and_lookup():
    from pydantic import ValidationError

    from lotline.config import AdapterRule, state_rule

    base = dict(unit="share", what="w", assumption="a", source="s", used_by=["x"])
    AdapterRule(value=0.95, low=0.9, high=0.99, **base)
    with pytest.raises(ValidationError):
        AdapterRule(value=0.95, low=0.96, high=0.99, **base)
    with pytest.raises(ValidationError):
        AdapterRule(value=0.95, low=0.9, **base)
    assert state_rule("OH", "adu_repeat_days") == 730
    with pytest.raises(KeyError, match="no rule"):
        state_rule("OH", "no_such_rule")


def test_a_state_file_with_another_states_fips_is_refused():
    """Nightly review, 2026-11-25: a FIPS typo would silently build another state's data."""
    from lotline.config import STATE_FIPS, StateConfig

    base = {"state": "WI", "name": "Wisconsin", "fips": "55", "bps_region": "midwest"}
    assert StateConfig.model_validate(base).fips == STATE_FIPS["WI"]
    with pytest.raises(ValueError, match="Census FIPS code is '55'"):
        StateConfig.model_validate({**base, "fips": "27"})
    test_state = {**base, "state": "ZZ", "fips": "99"}  # codes outside the table (test states) are free
    assert StateConfig.model_validate(test_state).state == "ZZ"


def test_fhfa_zip_rows_need_the_states_zip_prefixes():
    from lotline.adapters.national import fhfa

    rows = pd.DataFrame({"geo": ["zip5:53703"], "name": ["53703"]})
    with pytest.raises(ValueError, match="zip3_ranges"):
        fhfa.for_state(rows, "zip5", "WI", "55", [])
    assert len(fhfa.for_state(rows, "zip5", "WI", "55", [(530, 549)])) == 1
