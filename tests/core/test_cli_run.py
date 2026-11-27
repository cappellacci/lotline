"""The one-command path and plain errors (usability review, 2026-11-27): `lotline run`, `lotline app`, the
state check, the missing-tables check, fetch that keeps going past a failing source, and no Census key
needed offline."""

import sys
import types
from types import SimpleNamespace

import pandas as pd

from lotline import cli, config, registry


def test_an_unknown_state_is_one_plain_line(monkeypatch, capsys):
    monkeypatch.setattr(config, "all_states", lambda: ["MN", "NC"])
    assert cli.main(["results", "--state", "zz"]) == 2
    out = capsys.readouterr().out
    assert out.startswith("error: ZZ is not set up. Configured states: MN NC.")
    assert "Traceback" not in out


def test_results_before_any_fetch_names_the_fetch_command(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "all_states", lambda: ["MN"])
    monkeypatch.setattr("lotline.model.results.tree_state", lambda: True)
    assert cli.main(["results", "--state", "MN"]) == 2
    out = capsys.readouterr().out
    assert "acs_geo_year" in out and "uv run lotline fetch --state MN" in out


def test_fetch_keeps_going_past_a_source_that_fails(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("LOTLINE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "all_states", lambda: ["MN"])

    def hand_download(state, store, refresh=False):
        raise FileNotFoundError("register the file first: lotline manifest register ...")

    good = SimpleNamespace(load=lambda state, store, refresh=False: pd.DataFrame({"geoid": ["2700001"]}))
    sources = {
        "manual_src": registry.Source("manual_src", SimpleNamespace(load=hand_download), "t_manual", None),
        "good_src": registry.Source("good_src", good, "t_good", None),
    }
    monkeypatch.setattr(registry, "sources_for", lambda state: sources)
    monkeypatch.setattr(registry, "fetch_order", lambda available: ["manual_src", "good_src"])
    monkeypatch.setattr("lotline.validation.holdout.assert_no_leak", lambda df, table, state: None)
    assert cli.main(["fetch", "--state", "MN"]) == 1
    out = capsys.readouterr().out
    assert "MN manual_src: SKIPPED" in out
    assert "MN good_src: 1 rows" in out  # the source after the failing one still built
    assert "1 source(s) were skipped" in out


def test_app_with_no_results_says_what_to_run(monkeypatch, tmp_path, capsys):
    fake = types.SimpleNamespace(
        find_bundles=lambda results_dir=None: [],
        DATA_SUMMARY=tmp_path / "s.json",
        OUT_DIR=tmp_path,
        build_app=None,
    )
    monkeypatch.setitem(sys.modules, "lotline.app.build", fake)
    assert cli.main(["app"]) == 2
    assert "lotline run --state XX" in capsys.readouterr().out


def test_run_does_every_step_and_keeps_other_states_on_the_page(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(config, "all_states", lambda: ["AA", "BB"])
    other = tmp_path / "reports/results/bb/bundle.json"
    other.parent.mkdir(parents=True)
    other.write_text("{}")
    calls = []
    monkeypatch.setattr(cli, "_fetch_states", lambda states, **k: calls.append(("fetch", states)) or [])
    monkeypatch.setattr(cli, "_commit_note", lambda: None)

    def one(state, store, role=None, out=None, origin=None, draws=None):
        p = tmp_path / f"reports/results/{state.lower()}/bundle.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}")
        calls.append(("bundle", state))
        return p

    monkeypatch.setattr(cli, "_one_bundle", one)
    fake = types.SimpleNamespace(
        find_bundles=lambda results_dir=None: [tmp_path / "reports/results/aa/bundle.json", other]
    )
    monkeypatch.setitem(sys.modules, "lotline.app.build", fake)
    monkeypatch.setattr(
        cli,
        "_page",
        lambda bundles=None, data_tab=True: (
            calls.append(("page", sorted(b.parent.name for b in bundles))) or 0
        ),
    )
    assert cli.main(["run", "--state", "aa"]) == 0
    assert calls == [("fetch", ["AA"]), ("bundle", "AA"), ("page", ["aa", "bb"])]
    assert "step 3 of 3" in capsys.readouterr().out


def test_an_offline_build_needs_no_census_key(monkeypatch, tmp_path):
    from lotline.adapters.national import acs
    from lotline.io import DataStore, offline

    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    monkeypatch.setattr(acs, "_dotenv_value", lambda key: None)
    with offline.offline_build(DataStore(tmp_path)):
        assert acs.api_key() == acs.OFFLINE_KEY


def test_dotenv_falls_back_to_the_checkout(monkeypatch, tmp_path):
    from lotline.io import store

    repo_env = tmp_path / "repo.env"
    repo_env.write_text("LOTLINE_DATA_DIR=/data/from/checkout\n")
    monkeypatch.setattr(store, "REPO_ENV", repo_env)
    monkeypatch.chdir(tmp_path)  # no .env here
    assert store._dotenv_value("LOTLINE_DATA_DIR") == "/data/from/checkout"
