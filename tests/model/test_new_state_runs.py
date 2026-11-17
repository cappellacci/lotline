"""WS-SCALE task 0: a new state with national data only runs end to end.

A synthetic tier-3 state "ZZ" has no permit table, no `config/reforms/zz.csv` and is not in
`adu.REFORM_STATES`. Its bundle builds, is labelled `national_only`, and it borrows the listed states' rule
priors without feeding them ("borrow only", Ben 2026-11-17). All data is synthetic; the five listed states get
only a `jurisdictions` table (every GEOID in their reform files, population 20,000).
"""

from __future__ import annotations

import pandas as pd
import pytest

import lotline.config
from lotline.build import eligible
from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.model import eligible_proxy as proxy
from lotline.model.scenarios import adu

ZZ_YAML = """state: ZZ
name: Zedland
fips: "99"
bps_region: West Region
"""
PLACES = [("9900001", "Alpha", 40_000), ("9900002", "Beta", 12_000), ("9900003", "Gamma", 3_000)]
COUNTY = "99001"


def _write(store: DataStore, st: str, table: str, df: pd.DataFrame) -> None:
    path = store.processed(st, table, "synthetic")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def _jurisdictions(st: str, rows) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "state": st,
            "geoid": [r[0] for r in rows],
            "name": [r[1] for r in rows],
            "kind": [r[2] for r in rows],
            "county_geoid": [r[3] for r in rows],
            "bps_id": [r[0] for r in rows],
            "pop_2020": pd.array([r[4] for r in rows], dtype="Int64"),
            "data_tier": pd.array([3] * len(rows), dtype="Int64"),
            "cbsa_code": None,
            "cbsa_type": None,
            "in_bps": pd.array([True] * len(rows), dtype="boolean"),
        }
    )


def _zz_store(root) -> DataStore:
    store = DataStore(root)
    rows = [(g, n, "place", COUNTY, pop) for g, n, pop in PLACES]
    rows.append((COUNTY, "Zed County (unincorporated)", "county_unincorporated", COUNTY, 5_000))
    _write(store, "zz", "jurisdictions", _jurisdictions("ZZ", rows))
    geoids = [r[0] for r in rows]
    _write(
        store,
        "zz",
        "eligible_parcels",
        pd.DataFrame(
            {
                "state": "ZZ",
                "jurisdiction_geoid": geoids * 2,
                "year": pd.array([2020] * len(geoids) + [2023] * len(geoids), dtype="Int64"),
                "theme": ["adu"] * len(geoids) + ["missing_middle"] * len(geoids),
                "rule_version": eligible.RULE_VERSION,
                "eligible_parcels": pd.array([8_000, 2_500, 700, 1_200] * 2, dtype="Int64"),
                "data_tier": pd.array([3] * 2 * len(geoids), dtype="Int64"),
                "denominator_source": proxy.ACS_SOURCE,
                "denominator_quality": "acs",
            }
        ),
    )
    years = list(range(2010, 2026))
    bps = []
    for g, n, _kind, _, _ in rows:
        for y in years:
            bps.append(
                {
                    "state": "ZZ",
                    "bps_id": g,
                    "geoid": g,
                    "county_geoid": COUNTY,
                    "name": n,
                    "year": y,
                    "months_reported": 12,
                    **{f"bldgs_{c}": 2 for c in ("1", "2", "3_4", "5p")},
                    **{f"units_{c}": u for c, u in (("1", 20), ("2", 2), ("3_4", 3), ("5p", 10))},
                    **{f"units_{c}_rep": u for c, u in (("1", 20), ("2", 2), ("3_4", 3), ("5p", 10))},
                    "imputed": False,
                }
            )
    bps = pd.DataFrame(bps)
    for c in [c for c in bps if c.startswith(("bldgs", "units", "months", "year"))]:
        bps[c] = bps[c].astype("Int64")
    _write(store, "zz", "bps_place_year", bps)
    geos = ["national:US", "state:99", f"county:{COUNTY}"]
    _write(
        store,
        "zz",
        "market_geo_year",
        pd.DataFrame(
            [
                {
                    "geo": geo,
                    "year": y,
                    "cpi_u": 200.0 + 5 * (y - 2010),
                    "hpi": 100.0 + 3 * (y - 2010),
                    "mortgage_rate": 4.0,
                    "ppi_resid_inputs": 100.0 + 2 * (y - 2010),
                }
                for geo in geos
                for y in years
            ]  # fmt: skip
        ).assign(year=lambda d: d["year"].astype("Int64")),
    )
    acs = []
    for g, kind in [(r[0], r[2]) for r in rows]:
        geo = f"{adu.ACS_PREFIX[kind]}:{g}"
        for y in (2015, 2023):
            for var, val in (("B25064_001", 1_100.0), ("B25077_001", 280_000.0), ("B25024_001", 3_000.0)):
                acs.append({"geo": geo, "end_year": y, "table_id": var[:6], "variable": var, "label": var,
                            "estimate": val, "moe": 0.0})  # fmt: skip
    _write(
        store,
        "zz",
        "acs_geo_year",
        pd.DataFrame(acs).assign(end_year=lambda d: d["end_year"].astype("Int64")),
    )
    for st in adu.REFORM_STATES:
        geo = sorted(set(adu.load_reforms(st)["jurisdiction_geoid"].dropna().astype(str)))
        _write(store, st, "jurisdictions", _jurisdictions(st, [(g, g, "place", None, 20_000) for g in geo]))
    return store


@pytest.fixture
def zz(monkeypatch, tmp_path):
    cfg = tmp_path / "config"
    (cfg / "states").mkdir(parents=True)
    (cfg / "states" / "zz.yaml").write_text(ZZ_YAML)
    real = lotline.config.load_state

    def load_state(state, config_dir=CONFIG_DIR):
        return real(state, cfg) if state.upper() == "ZZ" else real(state, config_dir)

    monkeypatch.setattr(lotline.config, "load_state", load_state)
    from lotline.validation import holdout

    monkeypatch.setattr(holdout, "load_state", load_state)
    return _zz_store(tmp_path / "data")


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
    _, with_zz = adu.rule_inputs("ZZ", zz, [g for g, _, _ in PLACES], pd.Timestamp("2025-12-31"))
    _, without = adu.rule_inputs("MN", zz, [], pd.Timestamp("2025-12-31"))
    pd.testing.assert_frame_equal(with_zz["priors"], without["priors"])
    assert "ZZ" not in set(with_zz["coded"]["state"])
