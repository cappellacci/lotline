"""Results bundle (model/results.py, #310): the browser's arithmetic by hand, θ's back-solve reproduces the
engine, the overlap flag, and a bundle round-trips through JSON. Synthetic inputs only.

The committed fixture tests/fixtures/results/zz/bundle.json is what WS-APP builds and tests the page against;
regenerate it with `uv run python tests/model/test_results.py` after a schema change.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pandera import errors as pa_errors

from lotline.config import Parameter
from lotline.model import aggregate, results
from lotline.model.scenarios import adu
from lotline.schemas import SCENARIOS

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "results" / "zz" / "bundle.json"


def _need(value, low, high, kind):
    return Parameter(
        value=value, low=low, high=high, unit="homes", source=f"test {kind}", notes=f"kind: {kind}"
    )


NEED = {
    "household_growth_5y_zz": _need(2000, 1500, 2500, "household_growth_5y"),
    "shortage_stock_zz": _need(5000, 4000, 9000, "shortage_stock"),
}


def test_homes_from_draws_by_hand():
    # 1,000 eligible, pencil 0.5 -> 500; θ 0.04 -> 20 permits; completion 1.0, net-new 0.6 -> 12; displacement
    # 0.25 -> 9 net statewide. A stacked run's overlap 0.5 halves the permits.
    row = {
        "eligible_tier1": 600.0,
        "eligible_tier2": 300.0,
        "eligible_tier3": 100.0,
        "theta": 0.04,
        "pencil_out_share": 0.5,
        "completion_factor": 1.0,
        "net_new_share": 0.6,
        "displacement_share": 0.25,
    }
    h = aggregate.homes_from_draws(
        pd.DataFrame([row | {"overlap_share": np.nan}, row | {"overlap_share": 0.5}])
    )
    assert h["legal"] == pytest.approx([1000, 1000])
    assert h["pencils"] == pytest.approx([500, 500])
    assert h["permits_added"] == pytest.approx([20, 10])
    assert h["homes_in_place"] == pytest.approx([12, 6])
    assert h["homes_net_statewide"] == pytest.approx([9, 4.5])


def _run_draws(n=4, places=3, years=5, seed=0):
    rng = np.random.default_rng(seed)
    added = rng.uniform(0, 5, (n, places, years))
    params = [{"adu_net_new_share": 0.65, "adu_formalization_share": 0.1}] * n
    return {
        "eligible": np.tile([1000.0, 500.0, 200.0], (n, 1)),
        "pencil": rng.uniform(0.1, 0.9, (n, places)),
        "added": added,
        "homes": added * 0.65 * 0.9,
        "params": params,
    }


def _places():
    return pd.DataFrame({"geoid": ["1", "2", "3"], "data_tier": [1, 1, 3]})


def test_theta_back_solve_reproduces_engine_permits_and_homes():
    rd = _run_draws()
    d = results.adu_draws(_places(), rd, np.random.default_rng(1))
    h = aggregate.homes_from_draws(d)
    assert h["permits_added"] == pytest.approx(rd["added"].sum(axis=(1, 2)))
    engine_homes = rd["homes"].sum(axis=(1, 2))
    assert h["homes_in_place"] == pytest.approx(engine_homes * d["completion_factor"].to_numpy())
    assert d["eligible_tier1"].to_numpy() == pytest.approx([1500] * 4)  # places 1 and 2
    assert d["eligible_tier3"].to_numpy() == pytest.approx([200] * 4)
    assert (d["eligible_tier2"] == 0).all()
    # pencil-out share is the eligible-weighted mean of each place's feasible share
    w = (rd["eligible"] * rd["pencil"]).sum(axis=1) / rd["eligible"].sum(axis=1)
    assert d["pencil_out_share"].to_numpy() == pytest.approx(w)


def test_adu_run_return_draws_matches_its_own_totals():
    p = adu.central_params()
    places = pd.DataFrame(
        {
            "geoid": ["1", "2"],
            "eligible_parcels": [2000.0, 800.0],
            "rent": [1100.0, 1400.0],
            "home_value": [p["adu_ref_home_value_usd"] / 2] * 2,
            "mortgage_rate": [np.nan] * 2,
            "rule_class": ["none", "partial"],
            "rule_age": [np.nan, 3.0],
            "observed_rate": [np.nan] * 2,
        }
    )
    _, totals = adu.run(places, 2025, draws=60)
    _, totals2, rd = adu.run(places, 2025, draws=60, return_draws=True)
    pd.testing.assert_frame_equal(totals, totals2)  # asking for draws changes nothing
    added = rd["added"].sum(axis=2)  # draws x places
    assert added.mean(axis=0) == pytest.approx(totals["adu_permits_added_mean"].to_numpy())
    assert rd["eligible"].shape == (60, 2) and (rd["eligible"] == [2000.0, 800.0]).all()
    assert ((rd["pencil"] > 0) & (rd["pencil"] <= 1)).all()


def test_overlap_flag_thresholds():
    e = np.array([90.0, 10.0])
    assert results.overlap_flag(e, [False, False])[0] == "high"
    assert results.overlap_flag(e, [False, True]) == ("medium", pytest.approx(0.10))
    assert results.overlap_flag(e, [True, False])[0] == "low"


def make_fixture() -> dict[str, pd.DataFrame]:
    """A small synthetic bundle for state ZZ (20 draws, ADU), with both housing-need kinds."""
    n = 20
    rd = _run_draws(n=n, seed=7)
    d = results.adu_draws(_places(), rd, np.random.default_rng(11)).assign(state="ZZ")
    parts = results.summarize("ZZ", d, 2025, {"adu": results.year_shares(rd)}, need_params=NEED)
    meta = pd.DataFrame(
        [
            {
                "state": "ZZ",
                "state_role": "development",
                "data_tier": 1,
                "commit_sha": "0" * 40,
                "run_at": "2026-11-06T00:00:00Z",
                "engine_version": "0.0.1",
                "schemas_version": "1.10",
                "config_hash": "0" * 64,
                "origin_year": 2025,
                "horizon_years": 5,
                "n_draws": n,
                "seed": 11,
                "eligible_proxy": False,
                "overlap_flag": "medium",
                "overlap_note": "Synthetic fixture: 20% of eligible parcels outside the calibration range",
                "caveats": None,
                "scenarios_pending": ", ".join(s for s in SCENARIOS if s != "adu"),
            }
        ]
    )
    scorecard = pd.DataFrame(
        [
            {
                "state": "ZZ",
                "check_id": "V1",
                "label": "Baseline beats the simple benchmarks (synthetic)",
                "metric": "CRPS skill",
                "value": 0.12,
                "target": "> 0",
                "verdict": "pass",
                "report_path": None,
            }
        ]
    )
    return {"meta": meta, "draws": d, **parts, "scorecard": scorecard}


def test_bundle_round_trips(tmp_path):
    b = results.validate_bundle(make_fixture())
    path = results.write_bundle(b, tmp_path / "zz" / "bundle.json")
    back = results.read_bundle(path)
    for part in results.PARTS:
        pd.testing.assert_frame_equal(back[part], b[part], check_dtype=False, check_exact=False, rtol=1e-12)


def test_committed_fixture_is_valid_and_matches_the_generator():
    back = results.read_bundle(FIXTURE)
    fresh = results.validate_bundle(make_fixture())
    for part in results.PARTS:
        pd.testing.assert_frame_equal(
            back[part], fresh[part], check_dtype=False, check_exact=False, rtol=1e-12
        )


def test_fixture_totals_are_the_draws_reaggregated():
    """Parity contract: the bundle's totals = homes_from_draws over its own draws (what the page does)."""
    b = results.read_bundle(FIXTURE)
    h = aggregate.homes_from_draws(b["draws"])
    five = b["totals"][b["totals"]["period"] == "2026-2030"].set_index("outcome")
    for outcome in ("permits_added", "homes_in_place", "homes_net_statewide"):
        p10, p50, p90 = np.percentile(h[outcome], [10, 50, 90])
        assert five.loc[outcome, ["p10", "p50", "p90"]].to_numpy(dtype=float) == pytest.approx(
            [p10, p50, p90]
        )
    yearly = b["totals"][(b["totals"]["outcome"] == "permits_added") & (b["totals"]["period"] != "2026-2030")]
    assert sorted(yearly["period"]) == ["2026", "2027", "2028", "2029", "2030"]
    need = b["need"].set_index("denominator_kind")
    assert need.loc["household_growth_5y", "is_headline"] and not need.loc["shortage_stock", "is_headline"]
    assert need.loc["shortage_stock", "share_p50"] == pytest.approx(
        np.percentile(h["homes_net_statewide"], 50) / 5000
    )


def test_invalid_bundle_is_refused():
    b = make_fixture()
    with pytest.raises(KeyError):
        results.validate_bundle({k: v for k, v in b.items() if k != "need"})
    bad = dict(b, draws=b["draws"].assign(scenario="parking"))
    with pytest.raises(pa_errors.SchemaErrors):
        results.validate_bundle(bad)


if __name__ == "__main__":
    print(results.write_bundle(make_fixture(), FIXTURE))
    print(json.loads(FIXTURE.read_text())["meta"]["state"])
