"""The results bundle: what `lotline results --state XX` writes for the static app (#310; WS-ENGINE brief).

`reports/results/<st>/bundle.json` holds these tables (schemas `results_*`, schemas.py 1.25):

- `meta`: one row: commit, run time, engine and schema versions, config hash, origin, draws, seed, the state's
  role, data tier, overlap flag and caveats, and which scenarios the engine cannot run yet.
- `draws`: per scenario and draw, the factors the page re-multiplies when a slider moves
  (`aggregate.homes_from_draws`). θ is back-solved from the engine's own additions, so at default sliders the
  product is exactly the engine's draw (#310 Q1).
- `funnel`: Legal -> Pencils -> Built, P10/P50/P90.
- `totals`: the parity target, computed here from the same draws by `aggregate.homes_from_draws`.
- `need`: share of housing need for each denominator kind the state has (D-057), the headline marked.
- `scorecard`: validation rows. So far the `historical_floor` gut check per scenario (`model/gutcheck.py`,
  `historical_floor_rows`): with-reform permits a year against the trailing observed average.
- `baseline`: the no-policy-change forecast (`model/baseline.py`), homes permitted statewide per BPS building
  size and period, so the page can show the level the scenarios add to (`baseline_table`).
- `affordability`: who the new homes serve (`model/affordability.py`, WS-NEED-AMI part B): rent or price,
  income needed and share of area median income per home type and place type, market and break-even.
  Context, not a scenario result; empty without a registered HUD income limits file.
- `observed`: what was actually permitted in the years before the window (`observed_table`): ADU permits where
  local data flag them, and homes in 2-4 unit buildings from BPS.

Which scenarios: every module in the scenario registry (`lotline.model.scenarios.all()`, #554), each through
the one contract there; `meta.scenarios` (`results_scenarios`) lists them with their labels. Today the
engine runs the ADU and missing-middle (D-063) scenarios statewide, and the fee scenario
over every place the baseline forecasts (D-076) twice, as D-065 labels them: `fees`, the Handbook benchmark
($50,000 cut in half), and `fees_local_half`, real local fees cut in half. Each reform is run on its own
(Ben, 2026-11-17). A scenario the engine cannot run is listed in `meta.scenarios_pending`, never filled with
a stand-in.

The context tables are built in `results_tables.py` (overlap flag, fee slider grid, ADU place types,
affordability, shortfall) and `results_baseline.py` (baseline, observed record, gut check); this module
draws, assembles, validates, writes and reads the bundle.

Factors the scenario module does not draw itself are drawn here, triangular over config/params/aggregate.yaml
(low, value, high), from `results_seed`: `completion_factor_single_family` (ADU),
`completion_factor_multifamily` (missing middle) and `displacement_share`.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

import lotline
from lotline.build import eligible, panels
from lotline.config import CONFIG_DIR, load_params
from lotline.model import aggregate, baseline
from lotline.model import eligible_proxy as proxy
from lotline.model.results_baseline import (  # noqa: F401 (results.<name> keeps working)
    baseline_class_draws,
    baseline_table,
    historical_floor_rows,
    observed_table,
)
from lotline.model.results_tables import (  # noqa: F401 (results.<name> keeps working)
    FEE_STOPS,
    _columns,
    _pct,
    adu_baseline_years,
    adu_place_type_table,
    affordability_table,
    fee_types_with_stops,
    overlap_flag,
    shortfall_table,
    state_stock,
    weighted_median,
    year_shares,
)
from lotline.schemas import SCENARIOS, SCHEMAS_VERSION, validate

if TYPE_CHECKING:
    from lotline.model.scenarios import ScenarioRun

PARTS = (
    "meta",
    "draws",
    "funnel",
    "totals",
    "need",
    "scorecard",
    "baseline",
    "observed",
    "adu_place_types",
    "adu_baseline",
    "affordability",
    "shortfall",
    "fee_types",
    "scenarios",
)
TABLE = {part: f"results_{part}" for part in PARTS}
SCENARIO_PARTS = ("adu_place_types", "adu_baseline", "fee_types")  # filled by a scenario's extra_tables


def __getattr__(name: str):
    """`ENGINE_SCENARIOS` (every scenario `build_bundle` fills) and `FEE_SCENARIOS` (D-065: the fee model's
    bundle scenarios and the `scenarios.fees` mode behind each), derived from the scenario registry."""
    from lotline.model import scenarios

    if name == "ENGINE_SCENARIOS":
        return scenarios.bundle_names()
    if name == "FEE_SCENARIOS":
        return scenarios.get("fees").variants
    raise AttributeError(name)


REPO = Path(__file__).resolve().parents[3]


# ---- metadata ---------------------------------------------------------------------------------------------


def config_hash(config_dir: Path = CONFIG_DIR) -> str:
    """sha256 over every file under config/ (sorted relative paths and their bytes)."""
    h = hashlib.sha256()
    for path in sorted(p for p in config_dir.rglob("*") if p.is_file()):
        h.update(path.relative_to(config_dir).as_posix().encode())  # same on Windows
        h.update(b"\0")
        h.update(path.read_bytes())
    return h.hexdigest()


def input_hashes(state: str, store) -> dict[str, str]:
    """sha256 of each processed table the state has (its parquet files, by name and bytes), by table name.

    Recorded in the bundle (`input_tables`, `input_hash`) so a rerun that comes out different can be traced
    to the data or to the code: the same hashes and config_hash with a different result means the code."""
    root = Path(store.processed(state, "x")).parent  # processed/<st>/
    out = {}
    for folder in sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []:
        h = hashlib.sha256()
        files = sorted(folder.rglob("*.parquet"))
        for f in files:
            h.update(f.relative_to(folder).as_posix().encode())
            h.update(b"\0")
            h.update(f.read_bytes())
        if files:
            out[folder.name] = h.hexdigest()
    return out


def combined_hash(hashes: Mapping[str, str]) -> str:
    """One sha256 over `name=hash` lines, sorted by name."""
    return hashlib.sha256("".join(f"{k}={v}\n" for k, v in sorted(hashes.items())).encode()).hexdigest()


UNKNOWN_COMMIT = "0" * 40  # all zeros: git's own "no commit" id
_SHA = re.compile(r"^[0-9a-f]{7,40}$")


def commit_sha(repo: Path = REPO) -> str:
    """The commit the code came from, for `results_meta.commit_sha`. In order: `git rev-parse HEAD`; the
    `LOTLINE_COMMIT` environment variable; `src/lotline/COMMIT`, which `git archive` and GitHub's "Download
    ZIP" fill in (`.gitattributes` export-subst); else all zeros, with `tree_clean` then null (unknown)."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True)
        if out.returncode == 0 and _SHA.match(out.stdout.strip()):
            return out.stdout.strip()
    except OSError:  # no git installed
        pass
    env = os.environ.get("LOTLINE_COMMIT", "").strip().lower()
    if _SHA.match(env):
        return env
    stamp = Path(__file__).resolve().parents[1] / "COMMIT"
    text = stamp.read_text(encoding="utf-8").strip() if stamp.exists() else ""
    return text if _SHA.match(text) else UNKNOWN_COMMIT


def tree_state(repo: Path = REPO) -> bool | None:
    """`results_meta.tree_clean`: True when tracked files match HEAD (so `commit_sha` fully identifies the
    code that ran), False when they don't, None when git can't tell (no repository, no git)."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo, capture_output=True, text=True
        )
    except OSError:
        return None
    return None if out.returncode else not out.stdout.strip()


def post_test(state: str, origin: int, config_dir: Path | None = None) -> tuple[str | None, str | None]:
    """(`post_test`, `post_test_note`) for `results_meta` (#506): this state's released holdout tests whose
    outcome window opens by the origin year, so the run's data include outcomes the test was scored on.

    By hand: Wisconsin, origin 2025, V8-WI-TRANSFER (outcomes from 2020, released 2026-11-19) ->
    ("V8-WI-TRANSFER", "Built after the Wisconsin (statewide) test was scored: these results use 2020-2025
    outcomes it predicted blind."). A test still blind, or one whose window opens after the origin year, is
    not listed. (None, None) when nothing is listed."""
    from lotline.config import CONFIG_DIR, load_state

    folder = config_dir or CONFIG_DIR
    if not (folder / "states" / f"{state.lower()}.yaml").exists():  # a state with no config has no holdouts
        return None, None
    cfg = load_state(state, folder)
    hits = [h for h in cfg.holdouts if h.released_on and h.outcome_from.year <= origin]
    if not hits:
        return None, None
    notes = [
        f"the {h.place} test was scored: these results use {h.outcome_from.year}-{origin} outcomes it "
        "predicted blind"
        for h in hits
    ]
    return ", ".join(h.test_id for h in hits), "Built after " + "; and after ".join(notes) + "."


# ---- draws -> tables ------------------------------------------------------------------------------------


def triangular(name: str, n: int, rng: np.random.Generator, file: str = "aggregate") -> np.ndarray:
    s = load_params(file)[name]
    return np.full(n, s.value) if s.low == s.high else rng.triangular(s.low, s.value, s.high, n)


def scenario_draws(run: ScenarioRun, rng: np.random.Generator) -> pd.DataFrame:
    """`results_draws` rows for one scenario run (the scenario contract's `ScenarioRun`, #554).

    The scenario gives eligible by tier, θ, pencil-out share and net-new share. Drawn here from the shared
    `rng`, triangular over config/params/aggregate.yaml, in this order: one completion factor per completion
    class the run lists (`completion_factor_<class>`), then the displacement share. With one class the
    factor is used as drawn; with several it is the mean weighted by each class's added homes in that draw
    (the first class's draw where none are added). Stored on `run.completion_draws` for `extra_tables`.

    By hand: 120 houses and 30 homes in 2-4 unit buildings added, completion 0.95 and 0.85 -> 0.93.
    """
    n = len(np.asarray(run.year_shares))
    c = {k: triangular(f"completion_factor_{k}", n, rng) for k in run.completion}
    run.completion_draws = c
    if len(c) == 1:
        completion = next(iter(c.values()))
    else:
        first = next(iter(c))
        added = sum(np.asarray(w, dtype=float) for w in run.completion.values())
        num = sum(np.asarray(run.completion[k], dtype=float) * c[k] for k in c)
        completion = np.divide(num, added, out=c[first].copy(), where=added > 0)
    t1, t2, t3 = run.eligible
    return pd.DataFrame(
        {
            "scenario": run.scenario,
            "draw": np.arange(n),
            "eligible_tier1": t1,
            "eligible_tier2": t2,
            "eligible_tier3": t3,
            "theta": run.theta,
            "pencil_out_share": run.pencil_out_share,
            "completion_factor": completion,
            "net_new_share": run.net_new_share,
            "displacement_share": triangular("displacement_share", n, rng),
            "overlap_share": np.nan,
        }
    )


def summarize(
    state: str,
    draws: pd.DataFrame,
    origin: int,
    years: Mapping[str, np.ndarray] | None = None,
    need_params=None,
) -> dict[str, pd.DataFrame]:
    """funnel, totals and need tables from `results_draws` (all scenarios), via `aggregate.homes_from_draws`.

    `years` maps a scenario to its draws x years shares (`year_shares`) for the per-year totals; without it
    only the five-year window is written.
    """
    funnel, totals, need = [], [], []
    for scenario, g in draws.groupby("scenario", sort=False):
        g = g.sort_values("draw")
        h = aggregate.homes_from_draws(g)
        for stage, key, unit in (
            ("legal", "legal", "parcels"),
            ("pencils", "pencils", "parcels"),
            ("built", "homes_in_place", "homes"),
        ):
            funnel.append({"stage": stage, "unit": unit, "scenario": scenario, **_pct(h[key])})
        shares = (years or {}).get(scenario)
        _, window_years, first = baseline.window(origin)  # D-061: origin 2025 -> 2027-2031
        horizon = shares.shape[1] if shares is not None else window_years
        for outcome in ("permits_added", "homes_in_place", "homes_net_statewide"):
            a = h[outcome]
            periods = [(f"{first}-{first + horizon - 1}", a)]
            if shares is not None:
                periods += [(str(first + y), a * shares[:, y]) for y in range(horizon)]
            for period, x in periods:
                totals.append(
                    {"scenario": scenario, "outcome": outcome, "period": period, **_pct(x), "mean": x.mean()}
                )
        have = aggregate.need(state, need_params)
        headline = aggregate.headline_kind(state, need_params) if have else None
        for kind, d in have.items():
            if d.low <= 0:
                continue  # a falling projection has no share (D-057)
            s = aggregate.share_of_need(h["homes_net_statewide"], state, kind, need_params)
            need.append(
                {
                    "scenario": scenario,
                    "denominator_kind": kind,
                    "label": s["label"],
                    "denominator": s["denominator"],
                    "denominator_low": s["denominator_low"],
                    "denominator_high": s["denominator_high"],
                    "share_p10": s["share_p10"],
                    "share_p50": s["share_p50"],
                    "share_p90": s["share_p90"],
                    "share_p50_at_need_low": s["share_p50_at_need_low"],
                    "share_p50_at_need_high": s["share_p50_at_need_high"],
                    "is_headline": kind == headline,
                    "source": s["denominator_source"],
                }
            )
    st = state.upper()
    return {
        "funnel": pd.DataFrame(funnel).assign(state=st),
        "totals": pd.DataFrame(totals).assign(state=st),
        "need": pd.DataFrame(need, columns=_columns("need")).assign(state=st),
    }


# ---- the bundle -----------------------------------------------------------------------------------------


def validate_bundle(bundle: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Every part validated against its `results_*` schema (raises with every error)."""
    missing = set(PARTS) - set(bundle)
    if missing:
        raise KeyError(f"bundle is missing {sorted(missing)}")
    out = {part: validate(bundle[part].reset_index(drop=True), TABLE[part]) for part in PARTS}
    if len(out["meta"]) != 1:
        raise ValueError("a bundle has exactly one meta row")
    from lotline.model import scenarios

    unknown = set(out["draws"]["scenario"]) - set(scenarios.bundle_names())
    if unknown:
        raise ValueError(f"unknown scenarios {sorted(unknown)}")
    return out


def _records(df: pd.DataFrame) -> list[dict]:
    """JSON-safe records: missing values become null, numpy scalars plain Python."""
    return json.loads(df.to_json(orient="records", double_precision=15))


def write_bundle(bundle: Mapping[str, pd.DataFrame], path: Path) -> Path:
    """Validate and write `bundle.json`: {meta: {...}, draws: [...], funnel: [...], ...}."""
    b = validate_bundle(bundle)
    meta = _records(b["meta"])[0] | {"scenarios": _records(b["scenarios"].drop(columns="state"))}
    doc = {"meta": meta} | {part: _records(b[part]) for part in PARTS if part not in ("meta", "scenarios")}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=False) + "\n")
    return path


def read_bundle(path: Path) -> dict[str, pd.DataFrame]:
    """Read and validate a `bundle.json` back into the eight tables."""
    from lotline.schemas import columns

    doc = json.loads(Path(path).read_text())
    meta = dict(doc["meta"])
    listed = meta.pop("scenarios", None)  # `meta.scenarios` (schemas 1.25); none in older bundles
    if listed:
        doc["scenarios"] = [{"state": meta["state"], **row} for row in listed]
    raw = {"meta": pd.DataFrame([meta])} | {  # parts added later read as empty in older bundles
        part: pd.DataFrame(doc.get(part) or [], columns=columns(TABLE[part]) if not doc.get(part) else None)
        for part in PARTS
        if part != "meta"
    }
    return validate_bundle(raw)


def scenarios_table(state: str, runs: Mapping[str, tuple]) -> pd.DataFrame:
    """`results_scenarios` (written as `meta.scenarios`): one row per scenario run, in bundle order."""
    rows = []
    for name, (sc, _) in runs.items():
        lab = sc.labels(name)
        rows.append(
            {
                "state": state,
                "scenario": name,
                "model": sc.name,
                "title": lab["title"],
                "definition": lab["definition"],
                "handbook": lab.get("handbook"),
                "tables": ", ".join(sc.tables) or None,
            }
        )
    return pd.DataFrame(rows, columns=["state", *_columns("scenarios")])


def build_bundle(state: str, store, *, role: str | None = None, origin: int | None = None, draws=None):
    """Run every scenario in the registry (`lotline.model.scenarios.all()`, #554) for one state and assemble
    the bundle's tables (unwritten).

    Each scenario's variants run in bundle order; their draws share one completion-and-displacement `rng`
    (`scenario_draws`), so the order is part of the result. The ADU, missing-middle and fee runs also feed
    the bundle's context tables (overlap flag, gut check, affordability), which read them by name.
    """
    from lotline.model import scenarios
    from lotline.model.scenarios import adu

    st = state.upper()
    agg = load_params("aggregate")
    origin = int(agg["results_origin_year"].value) if origin is None else int(origin)
    n = int(draws or agg["results_draws"].value)
    seed = int(agg["results_seed"].value)
    rng = np.random.default_rng(seed)

    places = adu.places_from_store(st, store, origin)
    # place_inputs fills a missing rent or home value with the state median (WS-SCALE task 5 rule 2), so no
    # place is dropped for lack of prices; a gap here means the stored table predates that rule.
    gaps = places["rent"].isna() | places["home_value"].isna()
    if gaps.any():
        raise ValueError(
            f"{st}: {int(gaps.sum())} places have no rent or home value; rebuild place_inputs "
            f"(lotline fetch --state {st} --source place_inputs --offline)"
        )
    places["state"] = st
    tier3 = bool(proxy.proxy_states(places))
    tier_parcels = places.groupby("data_tier")["eligible_parcels"].sum() if "data_tier" in places else None
    tier = int(tier_parcels.idxmax()) if tier_parcels is not None and len(tier_parcels) else 3
    inputs = scenarios.Inputs(st, store, origin, n, places=places, data_tier=tier, eligible_proxy=tier3)

    runs = {}  # bundle scenario name -> (Scenario, ScenarioRun)
    for sc in scenarios.all():
        for name in sc.variants:
            runs[name] = (sc, sc.run(inputs, name))
    d = pd.concat([scenario_draws(r, rng) for _, r in runs.values()], ignore_index=True).assign(state=st)
    extra: dict[str, list[pd.DataFrame]] = {}
    for sc, r in runs.values():
        for part, table in sc.extra_tables(r).items():
            extra.setdefault(part, []).append(table)
    filled = {
        part: (got[0] if len(got) == 1 else pd.concat(got, ignore_index=True)).assign(state=st)
        for part, got in extra.items()
    }
    shares = {name: r.year_shares for name, (_, r) in runs.items()}
    parts = summarize(st, d, origin, shares)
    run_adu = runs["adu"][1].raw
    run_draws, totals_adu = run_adu["draws"], run_adu["totals"]
    res_mm = runs["missing_middle"][1].raw if "missing_middle" in runs else None
    fee_places = inputs.shared("fee_places", lambda: None)

    flag, median_distance = overlap_flag(places["eligible_parcels"], totals_adu["calibration_distance"])
    caveats = []
    if tier3:
        caveats.append(
            "National data only: eligible parcels are ACS single-family homes scaled by D-056 (zoning not "
            "observed); statewide results only."
        )
    tested = post_test(st, origin)
    inputs_used = input_hashes(st, store)
    meta = pd.DataFrame(
        [
            {
                "state": st,
                "state_role": role or ("national_only" if tier3 else "development"),
                "data_tier": tier,
                "commit_sha": commit_sha(),
                "run_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "engine_version": lotline.__version__,
                "schemas_version": SCHEMAS_VERSION,
                "config_hash": config_hash(),
                "origin_year": origin,
                "horizon_years": runs["adu"][1].horizon,
                "n_draws": n,
                "seed": seed,
                "eligible_proxy": tier3,
                "overlap_flag": flag,
                "overlap_note": f"median calibration distance {median_distance:.2f} (0 = inside the range)",
                "caveats": " ".join(caveats) or None,
                "scenarios_pending": ", ".join(s for s in SCENARIOS if s not in runs) or None,
                "tree_clean": tree_state(),
                "post_test": tested[0],
                "post_test_note": tested[1],
                "input_hash": combined_hash(inputs_used),
                "input_tables": json.dumps(inputs_used, sort_keys=True),
            }
        ]
    )
    panel = panels.load(st, store, theme="adu", rule_version=eligible.RULE_VERSION)
    class_draws = baseline_class_draws(panel, st, origin)
    base = baseline_table(panel, st, origin, class_draws=class_draws)
    k = int(agg["historical_floor_years"].value)
    from lotline.model import undercount as uc

    # D-078: the trailing observed average scales each source's ADU permits by its central undercount k
    adu_counts = adu.observed_adu_counts(store.read(st, "permits"), origin - k + 1, origin, uc.central())
    rows = historical_floor_rows(st, places, run_draws, adu_counts, panel, d, origin, class_draws)
    scorecard = pd.DataFrame(rows, columns=_columns("scorecard")).assign(state=st)
    seen = observed_table(panel, store.read(st, "permits"), store.read(st, "jurisdictions"), st, origin)
    return {
        "meta": meta,
        "draws": d,
        **parts,
        "scorecard": scorecard,
        "baseline": base,
        "observed": seen,
        "affordability": affordability_table(st, places, run_draws, res_mm, fee_places, store),
        "shortfall": shortfall_table(st, base, store.read(st, "acs_geo_year"), origin),
        **{p: pd.DataFrame(columns=["state", *_columns(p)]) for p in SCENARIO_PARTS},  # none filled them
        **filled,
        "scenarios": scenarios_table(st, runs),
    }
