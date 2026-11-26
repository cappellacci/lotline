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
from lotline.model import affordability, aggregate, results, scenarios
from lotline.model.scenarios import adu, bundle_adu, bundle_fees, bundle_mm
from lotline.schemas import SCENARIOS, columns

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
        "current": rng.uniform(0, 3, (n, places, years)),
        "homes": added * 0.65 * 0.9,
        "params": params,
    }


def _rows(run, name, rng):
    """`results_draws` rows for a scenario run labelled `name` (what `build_bundle` does per variant)."""
    run.scenario = name
    return results.scenario_draws(run, rng)


def adu_rows(places, rd, rng):
    return _rows(bundle_adu.from_draws(places, rd), "adu", rng)


def _places():
    return pd.DataFrame({"geoid": ["1", "2", "3"], "data_tier": [1, 1, 3]})


def test_theta_back_solve_reproduces_engine_permits_and_homes():
    rd = _run_draws()
    d = adu_rows(_places(), rd, np.random.default_rng(1))
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
    d = adu_rows(_places(), rd, np.random.default_rng(11)).assign(state="ZZ")
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
                "schemas_version": "1.12",
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
    permits = pd.DataFrame(
        {
            "jurisdiction_geoid": ["Z1"] * 6 + ["Z2"] * 2,
            "issue_year": [2020, 2021, 2023, 2024, 2025, 2025, 2022, 2025],
            "source": "zz_permits",
            "building_type_std": ["ADU"] * 7 + ["SFD"],
            "adu_type": None,
        }
    )
    juris = pd.DataFrame({"geoid": ["Z1", "Z2", "Z3"], "pop_2020": [6000, 2000, 2000]})
    seen = results.observed_table(_baseline_panel(), permits, juris, "ZZ", 2025)
    typed = _places().assign(place_type=["core", "suburb", "suburb"])
    return {
        "meta": meta,
        "draws": d,
        **parts,
        "scorecard": scorecard,
        "baseline": base,
        "observed": seen,
        "adu_place_types": results.adu_place_type_table("ZZ", typed, rd),
        "adu_baseline": results.adu_baseline_years("ZZ", rd, 2025),
        "affordability": affordability.table("ZZ", _affordability_inputs(typed, rd), n=200, seed=3).astype(
            {"places": "Int64"}
        ),
        "shortfall": results.shortfall_table("ZZ", base, _acs_stock(), 2025, need_params=NEED, fips="99"),
        "fee_types": pd.DataFrame(columns=columns("results_fee_types")),  # ADU-only fixture: no fee slider
        "scenarios": results.scenarios_table("ZZ", {"adu": (scenarios.get("adu"), None)}),
    }


def _acs_stock(units: float = 100_000.0):
    """Synthetic acs_geo_year: the state's housing units (B25024_001) in two vintages; the newer is used."""
    return pd.DataFrame(
        {
            "geo": "state:99",
            "end_year": [2023, 2024],
            "variable": "B25024_001",
            "estimate": [units * 0.98, units],
        }
    )


def test_shortfall_by_hand():
    """NEED: growth 2,000 (1,500 to 2,500); shortage 5,000 (4,000 to 9,000); 100,000 homes at 0.3% (0.2% to
    0.5%) a year lose 1,500 (1,000 to 2,500); need 8,500 (7,000 to 13,500) less what the no-change forecast
    builds."""
    b = results.baseline_table(_baseline_panel(), "ZZ", 2025)
    t = results.shortfall_table("ZZ", b, _acs_stock(), 2025, need_params=NEED, fips="99").iloc[0]
    five = b[(b["size_class"] == "all") & (b["period"] == "2027-2031")].iloc[0]
    assert (t["lost_low"], t["lost"], t["lost_high"]) == pytest.approx((1000, 1500, 2500))
    assert t["stock"] == 100_000 and t["stock_year"] == 2024
    assert t["need"] == pytest.approx(5000 + 2000 + 1500)
    assert t["gap"] == pytest.approx(8500 - five["p50"])
    assert t["gap_low"] == pytest.approx(4000 + 1500 + 1000 - five["p90"])
    assert t["gap_high"] == pytest.approx(9000 + 2500 + 2500 - five["p10"])


def test_shortfall_needs_a_stock_and_a_shortage():
    b = results.baseline_table(_baseline_panel(), "ZZ", 2025)
    assert results.shortfall_table("ZZ", b, None, 2025, need_params=NEED, fips="99").empty
    only_growth = {k: v for k, v in NEED.items() if k.startswith("household")}
    assert results.shortfall_table("ZZ", b, _acs_stock(), 2025, need_params=only_growth, fips="99").empty


def _market():
    """Synthetic market_geo_year: national CPI (2025 = 2026 level, so MFI needs no deflation) and HUD rows."""
    cpi = pd.DataFrame({"geo": "national:US", "year": pd.array([2025, 2026], dtype="Int64"), "cpi_u": 300.0})
    hud = pd.DataFrame(
        {
            "geo": ["county:99001", "county:99003"],
            "year": pd.array([2026, 2026], dtype="Int64"),
            "hud_mfi": [132_300.0, 100_000.0],
            **{
                f"hud_l50_{n}": [f * 66_150, f * 50_000]
                for n, f in zip(range(1, 6), (0.7, 0.8, 0.9, 1.0, 1.08), strict=True)
            },
        }
    )
    return pd.concat([cpi, hud], ignore_index=True)


def _affordability_inputs(typed, rd):
    places = typed.assign(
        county_geoid=["99001", "99001", "99003"], rent=[1500.0, 1200.0, 1000.0],
        home_value=[400_000.0, 300_000.0, 250_000.0],
    )  # fmt: skip
    mm = pd.DataFrame({"geoid": ["1", "2", "3"], "added_homes_net_mean": [30.0, 10.0, 0.0]})
    fee = pd.DataFrame(
        {"geoid": ["1", "2", "3"], "local_fee_per_unit": [30_000.0, 20_000.0, 10_000.0],
         "local_fee_per_unit_U2": [20_000.0, 15_000.0, np.nan]}
    )  # fmt: skip
    return affordability.inputs(places, rd, mm, fee, _market())


def test_affordability_inputs_join_hud_weights_and_fees():
    rd = _run_draws()
    p = _affordability_inputs(_places().assign(place_type=["core", "suburb", "suburb"]), rd).set_index(
        "geoid"
    )
    assert p.loc["1", "mfi"] == pytest.approx(132_300) and p.loc["3", "mfi"] == pytest.approx(100_000)
    assert p.loc["1", "l50_1"] / p.loc["1", "l50_4"] == pytest.approx(0.7)
    assert p.loc["2", "weight_adu"] == pytest.approx(np.median(rd["added"][:, 1, :].sum(axis=1)))
    assert p.loc["1", "weight_mm"] == 30.0
    assert p.loc["3", "fee_plex"] == pytest.approx(17_500)  # missing: the state median of the others


def test_affordability_inputs_without_hud_rows_leave_mfi_missing():
    rd = _run_draws()
    places = _places().assign(place_type="suburb", county_geoid="99001", rent=1000.0, home_value=2e5)
    market = _market()
    p = affordability.inputs(places, rd, None, None, market[market["geo"] == "national:US"])
    assert p["mfi"].isna().all() and affordability.table("ZZ", p, n=5).empty


def test_adu_place_types_and_baseline_by_hand():
    """Docstring example: two suburbs with 3 and 5 current-rules ADUs a year and 1 and 2 added, every draw and
    year; one core city with 10 and 4. Base and added are per year, summed over the type's places."""
    n, yrs = 3, 5
    cur = np.zeros((n, 3, yrs)) + np.array([3.0, 5.0, 10.0])[None, :, None]
    add = np.zeros((n, 3, yrs)) + np.array([1.0, 2.0, 4.0])[None, :, None]
    rd = {"current": cur, "added": add, "eligible": np.tile([100.0, 200.0, 50.0], (n, 1))}
    places = pd.DataFrame({"geoid": ["a", "b", "c"], "place_type": ["suburb", "suburb", "core"]})
    t = results.adu_place_type_table("ZZ", places, rd).set_index("place_type")
    assert list(t.index) == ["core", "suburb"]  # no towns here, so no town row
    assert t.loc["suburb", ["places", "lots", "base", "added"]].tolist() == [2, 300, 8, 3]
    assert t.loc["core", ["base_p10", "base", "base_p90", "added"]].tolist() == [10, 10, 10, 4]
    y = results.adu_baseline_years("ZZ", rd, 2025)
    assert y["period"].tolist() == ["2027", "2028", "2029", "2030", "2031"] and (y["p50"] == 18).all()
    assert "basis" not in y  # without `own`, the pre-1.21 shape


def test_adu_baseline_split_by_basis_by_hand():
    """adu_baseline_years docstring: places with 10 and 4 ADUs a year in every draw, the first with own
    counts -> all 14, own_counts 10, model 4; the means add up. No own counts -> the `all` rows only."""
    n, yrs = 3, 5
    cur = np.zeros((n, 2, yrs)) + np.array([10.0, 4.0])[None, :, None]
    y = results.adu_baseline_years("ZZ", {"current": cur}, 2025, own=[True, False]).set_index(
        ["basis", "period"]
    )
    assert y.loc[("all", "2027"), "p50"] == 14 and y.loc[("own_counts", "2027"), "p50"] == 10
    assert y.loc[("model", "2031"), ["p10", "p50", "p90", "mean"]].tolist() == [4, 4, 4, 4]
    by = y["mean"].groupby(level="basis").sum()
    assert by["all"] == pytest.approx(by["own_counts"] + by["model"])
    results.validate(y.reset_index(), "results_adu_baseline")
    none = results.adu_baseline_years("ZZ", {"current": cur}, 2025, own=[False, False])
    assert set(none["basis"]) == {"all"} and len(none) == yrs


def test_an_older_bundle_without_the_adu_parts_still_reads(tmp_path):
    b = results.validate_bundle(make_fixture())
    path = results.write_bundle(b, tmp_path / "zz" / "bundle.json")
    doc = json.loads(path.read_text())
    for part in ("adu_place_types", "adu_baseline", "affordability", "shortfall", "fee_types"):
        del doc[part]
    del doc["meta"]["scenarios"]  # before schemas 1.25
    path.write_text(json.dumps(doc))
    back = results.read_bundle(path)
    assert back["scenarios"].empty
    assert (
        back["adu_place_types"].empty
        and back["adu_baseline"].empty
        and back["affordability"].empty
        and back["shortfall"].empty
        and back["fee_types"].empty
    )


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
    bad = dict(b, draws=b["draws"].assign(scenario="Parking!"))  # not a scenario name
    with pytest.raises(pa_errors.SchemaErrors):
        results.validate_bundle(bad)
    unknown = dict(b, draws=b["draws"].assign(scenario="parking"))  # well formed, but no module declares it
    with pytest.raises(ValueError, match="unknown scenarios"):
        results.validate_bundle(unknown)


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
    monkeypatch.setattr(results, "tree_state", lambda: True)
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
    d = _rows(bundle_mm.from_result(res), "missing_middle", np.random.default_rng(1)).iloc[0]
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
    run = bundle_mm.from_result(res)
    d = _rows(run, "missing_middle", np.random.default_rng(2))
    h = aggregate.homes_from_draws(d)
    assert h["permits_added"] == pytest.approx(res.homes_gross.sum(axis=1))
    net = res.homes_net.sum(axis=1)
    assert h["homes_in_place"] == pytest.approx(net * d["completion_factor"].to_numpy())
    # legal by tier: a 5,000 + b 20,000 × 0.5 in tier 1; c 800 × (1 − its band draw) in tier 3
    assert d["eligible_tier1"].to_numpy() == pytest.approx(np.full(300, 15000.0))
    assert (d["eligible_tier2"] == 0).all()
    shares = run.year_shares
    assert shares.sum(axis=1)[res.homes_gross.sum(axis=1) > 0] == pytest.approx(1.0)


def test_fee_rows_by_hand():
    """D-065 fee scenarios in the bundle: covered homes as the first stage, θ the % change, completion
    weighted by class. Docstring example: 10,000 covered homes, 120 houses and 30 plex homes added."""
    yrs = 5
    by_size = {
        c: np.full((1, yrs), v / yrs) for c, v in (("1", 8_000), ("2", 1_200), ("3_4", 800), ("5p", 5_000))
    }
    added = {
        "1": np.full((1, 1, yrs), 120 / yrs),
        "2": np.full((1, 1, yrs), 20 / yrs),
        "3_4": np.full((1, 1, yrs), 10 / yrs),
    }
    sim = {
        "n": 1,
        "by_size": by_size,
        "added_by_class": added,
        "added": sum(added.values()),
        "base": sum(by_size.values()),
    }

    class Fixed:  # triangular() draws: single-family 0.95, multifamily 0.85, displacement 0.25
        def triangular(self, lo, mode, hi, n):
            return np.full(n, mode)

    import unittest.mock as mock

    vals = {
        "completion_factor_single_family": 0.95,
        "completion_factor_multifamily": 0.85,
        "displacement_share": 0.25,
    }
    with mock.patch.object(
        results, "triangular", lambda name, n, rng, file="aggregate": np.full(n, vals[name])
    ):
        run = bundle_fees.from_sim(sim, 2)
        rows = _rows(run, "fees", Fixed())
    r = rows.iloc[0]
    assert (r.eligible_tier1, r.eligible_tier2, r.eligible_tier3) == (0, 10_000, 0)  # 5+ units take no dose
    assert r.theta == pytest.approx(0.015) and r.pencil_out_share == 1 and r.net_new_share == 1
    assert r.completion_factor == pytest.approx(0.93)
    h = aggregate.homes_from_draws(rows)
    assert h["permits_added"][0] == pytest.approx(150) and h["homes_in_place"][0] == pytest.approx(139.5)
    assert run.year_shares[0] == pytest.approx(np.full(yrs, 0.2))


def test_fee_types_by_hand():
    """`results_fee_types` (D-077 slider): per size the draw's homes added at the half cut, its completion
    draw and baseline; the sizes add up to the draw's `fees_local_half` row. Fixture as in
    `test_fee_rows_by_hand`: 120 houses, 20 duplex and 10 three-to-four-unit homes added on 8,000, 1,200 and
    800 baseline homes."""
    import unittest.mock as mock

    yrs = 5
    by_size = {
        c: np.full((1, yrs), v / yrs) for c, v in (("1", 8_000), ("2", 1_200), ("3_4", 800), ("5p", 5_000))
    }
    added = {c: np.full((1, 1, yrs), v / yrs) for c, v in (("1", 120), ("2", 20), ("3_4", 10))}
    sim = {"n": 1, "by_size": by_size, "added_by_class": added, "added": sum(added.values()),
           "base": sum(by_size.values())}  # fmt: skip
    vals = {"completion_factor_single_family": 0.95, "completion_factor_multifamily": 0.85,
            "displacement_share": 0.25}  # fmt: skip
    with mock.patch.object(
        results, "triangular", lambda name, n, rng, file="aggregate": np.full(n, vals[name])
    ):
        local = bundle_fees.from_sim(sim, 2, "local_half")
        rows = _rows(local, "fees_local_half", None)
        types = bundle_fees.size_types(local)
        bench = bundle_fees.from_sim(sim, 2, "handbook")
        _rows(bench, "fees", None)
        none = bundle_fees.size_types(bench)
    assert none.empty  # only the real-local-fee scenario gets the slider table
    t = types.set_index("size")
    assert t.loc["1", "units_added"] == pytest.approx(120) and t.loc["2", "units_added"] == pytest.approx(20)
    assert t.loc["3_4", "units_added"] == pytest.approx(10)
    assert list(t["completion_factor"]) == pytest.approx([0.95, 0.85, 0.85])
    assert list(t["baseline_homes"]) == pytest.approx([8_000, 1_200, 800])
    assert (t["fee_change_share"] == 0.5).all()
    covered = rows.iloc[0][["eligible_tier1", "eligible_tier2", "eligible_tier3"]].sum()
    assert t["units_added"].sum() == pytest.approx(rows.iloc[0].theta * covered)  # 150 = 0.015 x 10,000
    # completion weighted by each size's homes reproduces the draw's blended completion (0.93)
    blend = (t["units_added"] * t["completion_factor"]).sum() / t["units_added"].sum()
    assert blend == pytest.approx(rows.iloc[0].completion_factor)
    results.validate(types.assign(state="MN"), "results_fee_types")


def _half_cut_types(places, draws=20):
    from lotline.model.scenarios import fees

    g = fees.change_grid(places, 2025, [0.5], draws=draws)
    t = g.groupby(["draw", "size"], as_index=False)["units_added"].sum()
    return t.assign(
        scenario="fees_local_half", fee_change_share=0.5, completion_factor=0.9, baseline_homes=1.0
    )


def test_fee_stops_kept_only_where_a_size_is_not_linear(monkeypatch):
    """Elasticity only: every size is linear, so only the half cut is kept, and a mismatched half cut raises.
    A size that is not linear (houses on the lot-feasibility route, here a hand-made grid: 10 at the half cut,
    12 when abolished, 0 for a rise) gets the grid's value at every stop; linear sizes keep the half cut."""
    from lotline.model.scenarios import fees

    from .test_fee_scenario import by_size_frame

    linear = by_size_frame(U2=10_000.0, U3_4=6_000.0).assign(local_fee_low=10_000.0, local_fee_high=10_000.0)
    t = _half_cut_types(linear)
    assert results.fee_types_with_stops(linear, 2025, 20, t).equals(t)
    with pytest.raises(ValueError, match="does not match"):
        results.fee_types_with_stops(linear, 2025, 20, t.assign(units_added=t["units_added"] * 1.1 + 1))

    def grid(places, origin, shares, draws):
        rows = []
        for s in shares:
            house = 10.0 if s == 0.5 else (12.0 if s > 0.5 else (s / 0.5) * 10.0 if s > 0 else 0.0)
            for d in range(draws):
                plex = 4.0 * s / 0.5
                key = {"share": s, "draw": d, "state": "MN"}
                rows += [key | {"size": "1", "units_added": house}, key | {"size": "2", "units_added": plex}]
        return pd.DataFrame(rows)

    monkeypatch.setattr(fees, "change_grid", grid)
    half = pd.DataFrame(
        [{"draw": d, "size": z, "units_added": u} for d in range(3) for z, u in (("1", 10.0), ("2", 4.0))]
    )
    half = half.assign(
        scenario="fees_local_half", fee_change_share=0.5, completion_factor=0.9, baseline_homes=1.0
    )
    out = results.fee_types_with_stops(linear, 2025, 3, half)
    houses = out[out["size"] == "1"].set_index(["fee_change_share", "draw"])["units_added"]
    assert sorted(out.loc[out["size"] == "1", "fee_change_share"].unique()) == sorted(results.FEE_STOPS)
    assert houses[(1.0, 0)] == 12.0 and houses[(0.6, 2)] == 12.0 and houses[(-0.3, 1)] == 0.0
    assert houses[(0.2, 0)] == pytest.approx(4.0)
    assert set(out.loc[out["size"] == "2", "fee_change_share"]) == {0.5}  # linear: the page scales it
    results.validate(out.assign(state="MN"), "results_fee_types")


def test_post_test_lists_released_tests_whose_window_the_data_reach(tmp_path):
    """#506 by hand: a released statewide test from 2020 is listed at origin 2025, not at origin 2019; a blind
    test is never listed; a state with no config file has none."""
    import yaml

    from lotline.config import CONFIG_DIR

    doc = yaml.safe_load((CONFIG_DIR / "states" / "wi.yaml").read_text())  # a valid state file, renamed
    doc["state"] = "ZZ"
    base = {"outcome_until": "2099-12-31", "reason": "r"}
    doc["holdouts"] = [
        {**base, "test_id": "V1-ZZ-OPEN", "place": "Testland (statewide)", "geoid": doc["fips"],
         "outcome_from": "2020-01-01", "released_on": "2026-01-02", "released_note": "scored"},
        {**base, "test_id": "V1-ZZ-BLIND", "place": "Testville", "geoid": doc["fips"] + "00001",
         "outcome_from": "2021-01-01"},
    ]  # fmt: skip
    (tmp_path / "states").mkdir()
    (tmp_path / "states" / "zz.yaml").write_text(yaml.safe_dump(doc))
    ids, note = results.post_test("ZZ", 2025, tmp_path)
    assert ids == "V1-ZZ-OPEN"
    assert note == (
        "Built after the Testland (statewide) test was scored: these results use 2020-2025 outcomes it "
        "predicted blind."
    )
    assert results.post_test("ZZ", 2019, tmp_path) == (None, None)
    assert results.post_test("QQ", 2025, tmp_path) == (None, None)


def test_wisconsin_is_marked_post_test():
    ids, note = results.post_test("WI", 2025)
    assert ids == "V8-WI-TRANSFER" and "2020-2025" in note


def test_tree_state_is_none_outside_a_repository(tmp_path):
    assert results.tree_state(tmp_path) is None


def test_an_older_bundle_without_the_new_meta_fields_still_reads(tmp_path):
    b = results.validate_bundle(make_fixture())
    b["meta"] = b["meta"].assign(tree_clean=True, post_test=None, post_test_note=None)
    path = results.write_bundle(results.validate_bundle(b), tmp_path / "zz" / "bundle.json")
    doc = json.loads(path.read_text())
    for row in doc["meta"] if isinstance(doc["meta"], list) else [doc["meta"]]:
        for k in ("tree_clean", "post_test", "post_test_note"):
            row.pop(k, None)
    path.write_text(json.dumps(doc))
    assert "tree_clean" not in results.read_bundle(path)["meta"]


def test_commit_sha_without_git_uses_the_env_then_the_stamp_then_zeros(monkeypatch, tmp_path):
    """Outside a repository: LOTLINE_COMMIT wins; then src/lotline/COMMIT (filled in by `git archive` and
    GitHub's Download ZIP); a missing or unfilled stamp ($Format:%H$) gives all zeros."""
    monkeypatch.delenv("LOTLINE_COMMIT", raising=False)
    fake = tmp_path / "pkg" / "model" / "results.py"
    fake.parent.mkdir(parents=True)
    monkeypatch.setattr(results, "__file__", str(fake))
    assert results.commit_sha(tmp_path) == results.UNKNOWN_COMMIT
    (tmp_path / "pkg" / "COMMIT").write_text("$Format:%H$\n")
    assert results.commit_sha(tmp_path) == results.UNKNOWN_COMMIT
    monkeypatch.setenv("LOTLINE_COMMIT", "ABCDEF1234567")
    assert results.commit_sha(tmp_path) == "abcdef1234567"


def test_the_repo_ships_an_unfilled_commit_stamp():
    stamp = Path(results.__file__).resolve().parents[1] / "COMMIT"
    assert stamp.read_text(encoding="utf-8").strip() == "$Format:%H$"


def test_commit_sha_reads_a_filled_stamp(monkeypatch, tmp_path):
    monkeypatch.delenv("LOTLINE_COMMIT", raising=False)
    fake = tmp_path / "pkg" / "model" / "results.py"
    fake.parent.mkdir(parents=True)
    (tmp_path / "pkg" / "COMMIT").write_text("0123456789abcdef0123456789abcdef01234567\n")
    monkeypatch.setattr(results, "__file__", str(fake))
    assert results.commit_sha(tmp_path) == "0123456789abcdef0123456789abcdef01234567"


def test_commit_sha_without_git_installed(monkeypatch, tmp_path):
    def no_git(*a, **k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(results.subprocess, "run", no_git)
    monkeypatch.setenv("LOTLINE_COMMIT", "1234567")
    assert results.commit_sha(tmp_path) == "1234567"
    assert results.tree_state(tmp_path) is None
