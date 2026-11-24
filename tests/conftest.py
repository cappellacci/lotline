"""Shared test fixtures."""

import pandas as pd
import pytest

import lotline.config
from lotline.build import eligible
from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.model import eligible_proxy as proxy
from lotline.model.scenarios import adu
from lotline.validation import holdout


@pytest.fixture
def v5_blind(monkeypatch):
    """The holdout registry with every V5 test still blind (Charlotte, NC; St. Paul, MN).

    Both were scored and released (Charlotte 2026-11-09, D-071; St. Paul 2026-11-16, D-098), so the live
    config no longer hides their outcomes. Adapter tests that check the filter itself use them as their
    examples; they run against the blind registry, as the filter behaves for any test not yet released."""
    real = holdout.holdouts_for

    def blind(state):
        return [h.model_copy(update={"released_on": None, "released_note": None}) for h in real(state)]

    monkeypatch.setattr(holdout, "holdouts_for", blind)


# ---- a synthetic national-data-only state "ZZ" (WS-SCALE tasks 0 and 4) ----------------------------------
# Three places and a county remainder in county 99001; ACS-fallback eligible parcels; BPS 2010-2025; no
# permits, no parcels, no reforms file, not in `adu.REFORM_STATES`. The five listed states get only a
# `jurisdictions` table (every GEOID in their reform files, population 20,000), which the rule priors read.

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
                "denominator_quality": "low",
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
