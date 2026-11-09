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


def test_overlap_flag_on_the_weighted_median_distance():
    # 60 parcels at 0.3, 40 at 2.0 -> median 0.3 -> high; swap the weights -> median 2.0 -> low
    assert results.overlap_flag([60.0, 40.0], [0.3, 2.0]) == ("high", pytest.approx(0.3))
    assert results.overlap_flag([40.0, 60.0], [0.3, 2.0]) == ("low", pytest.approx(2.0))
    assert results.overlap_flag([10.0, 90.0], [0.0, 0.8])[0] == "medium"
    assert results.overlap_flag([50.0, 50.0], [0.5, 0.9])[0] == "high"  # boundary 0.5 is high
    assert results.weighted_median([3.0, 1.0, 2.0], [1.0, 1.0, 1.0]) == 2.0


def _baseline_panel() -> pd.DataFrame:
    """Two synthetic places, 2010-2025, fixed counts per size class (for the fixture's `baseline` part)."""
    rows = []
    for geoid, county, parcels, units in (
        ("Z1", "C1", 4000, (30, 4, 6, 40)),
        ("Z2", "C1", 1500, (9, 0, 2, 0)),
    ):
        for year in range(2010, 2026):
            row = {
                "state": "ZZ",
                "geoid": geoid,
                "county_geoid": county,
                "year": year,
                "eligible_parcels": parcels,
            }
            for s, u in zip(("1", "2", "3_4", "5p"), units, strict=True):
                u = u + (year % 3)  # some year-to-year spread
                row[f"units_{s}"] = u
                row[f"units_{s}_rep"] = u
            rows.append(row)
    return pd.DataFrame(rows)


def make_fixture() -> dict[str, pd.DataFrame]:
    """A small synthetic bundle for state ZZ (20 draws, ADU), with both housing-need kinds and a baseline."""
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
                "schemas_version": "1.11",
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
    base = results.baseline_table(_baseline_panel(), "ZZ", 2025)
    return {"meta": meta, "draws": d, **parts, "scorecard": scorecard, "baseline": base}


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
    five = b["totals"][b["totals"]["period"] == "2027-2031"].set_index("outcome")
    for outcome in ("permits_added", "homes_in_place", "homes_net_statewide"):
        p10, p50, p90 = np.percentile(h[outcome], [10, 50, 90])
        assert five.loc[outcome, ["p10", "p50", "p90"]].to_numpy(dtype=float) == pytest.approx(
            [p10, p50, p90]
        )
    yearly = b["totals"][(b["totals"]["outcome"] == "permits_added") & (b["totals"]["period"] != "2027-2031")]
    assert sorted(yearly["period"]) == ["2027", "2028", "2029", "2030", "2031"]
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


# ---- lotline results --all ---------------------------------------------------------------------------


def _fake_cli(monkeypatch, tmp_path, states, fail=()):
    import sys
    import types

    from lotline import cli, config

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "all_states", lambda: list(states))

    def fake_build(state, store, **kw):
        if state in fail:
            raise FileNotFoundError(f"no processed tables for {state}")
        b = make_fixture()
        return {k: v.assign(state=state) if "state" in v else v for k, v in b.items()}

    monkeypatch.setattr(results, "build_bundle", fake_build)
    monkeypatch.setattr(results, "tree_is_clean", lambda: True)
    pages = []

    def build_app(results_dir, out_dir):
        pages.append(sorted(p.parent.name for p in Path(results_dir).glob("*/bundle.json")))
        out = Path(out_dir) / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("<html></html>")
        return out

    monkeypatch.setitem(sys.modules, "lotline.app.build", types.SimpleNamespace(build_app=build_app))
    return cli, pages


def test_results_all_writes_every_bundle_then_the_page(monkeypatch, tmp_path):
    cli, pages = _fake_cli(monkeypatch, tmp_path, ["AA", "BB"])
    assert cli.main(["results", "--all"]) == 0
    assert pages == [["aa", "bb"]]  # the page is built after every bundle is written
    assert results.read_bundle(tmp_path / "reports/results/bb/bundle.json")["meta"]["state"].iloc[0] == "BB"
    assert (tmp_path / "reports/app/index.html").exists()


def test_results_all_keeps_going_past_a_failing_state(monkeypatch, tmp_path, capsys):
    cli, pages = _fake_cli(monkeypatch, tmp_path, ["AA", "BB"], fail=("AA",))
    assert cli.main(["results", "--all"]) == 1
    assert pages == [["bb"]]
    assert "no bundle for AA" in capsys.readouterr().out


def test_results_all_says_when_the_page_build_is_missing(monkeypatch, tmp_path, capsys):
    import sys

    cli, _ = _fake_cli(monkeypatch, tmp_path, ["AA"])
    monkeypatch.setitem(sys.modules, "lotline.app.build", None)  # import fails as if absent
    assert cli.main(["results", "--all"]) == 2
    assert "PR #313" in capsys.readouterr().out
    assert cli.main(["results", "--all", "--state", "AA"]) == 2


# ---- missing middle (D-063) ----


def test_mm_draws_by_hand():
    from lotline.model.scenarios.mm import Result

    # one draw: legal 1,000 (tier 1), pencils 400, 20 homes in 8 buildings that replace 6 houses
    res = Result(
        buildings=np.array([[8.0, 0, 0, 0, 0]]), homes_gross=np.array([[20.0, 0, 0, 0, 0]]),
        teardowns=np.array([[6.0, 0, 0, 0, 0]]), places=pd.DataFrame(),
        legal=np.array([[1000.0, 0.0, 0.0]]), pencils=np.array([400.0]),
    )  # fmt: skip
    d = results.mm_draws(res, np.random.default_rng(1)).iloc[0]
    assert d["scenario"] == "missing_middle"
    assert d["theta"] == pytest.approx(0.05)  # 20 / 400
    assert d["pencil_out_share"] == pytest.approx(0.4)
    assert d["net_new_share"] == pytest.approx(0.7)  # (20 − 6) / 20
    assert 0.74 <= d["completion_factor"] <= 0.88  # completion_factor_multifamily


def test_mm_draws_reproduce_the_scenario():
    from lotline.model.scenarios import mm

    places = pd.DataFrame(
        {"geoid": ["a", "b", "c"], "eligible": [5000.0, 20000.0, 800.0], "dose": [0.0, 0.5, np.nan],
         "band": [2, 2, 1], "f_ratio": [1.2, 0.8, 1.0], "f_share": [0.47, 0.31, 0.39],
         "house_share": [0.9, 0.7, 1.0], "data_tier": [1, 1, 3]}
    )  # fmt: skip
    draws = pd.DataFrame({"theta": np.full(300, 0.002), "alpha": np.full(300, 2.0),
                          "units": np.full(300, 2.2), "teardown_scale": np.full(300, 0.8)})  # fmt: skip
    res = mm.simulate(places, draws, 0.5, 0.75, seed=4)
    d = results.mm_draws(res, np.random.default_rng(2))
    h = aggregate.homes_from_draws(d)
    assert h["permits_added"] == pytest.approx(res.homes_gross.sum(axis=1))
    net = res.homes_net.sum(axis=1)
    assert h["homes_in_place"] == pytest.approx(net * d["completion_factor"].to_numpy())
    # legal by tier: a 5,000 + b 20,000 × 0.5 in tier 1; c 800 × (1 − its band draw) in tier 3
    assert d["eligible_tier1"].to_numpy() == pytest.approx(np.full(300, 15000.0))
    assert (d["eligible_tier2"] == 0).all()
    shares = results.mm_year_shares(res)
    assert shares.sum(axis=1)[res.homes_gross.sum(axis=1) > 0] == pytest.approx(1.0)
