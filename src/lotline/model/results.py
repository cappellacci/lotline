"""The results bundle: what `lotline results --state XX` writes for the static app (#310; WS-ENGINE brief).

`reports/results/<st>/bundle.json` holds eight tables (schemas `results_*`, schemas.py 1.12):

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

Which scenarios: the engine runs the ADU and missing-middle (D-063) scenarios statewide, and the fee scenario
over every place the baseline forecasts (D-076) twice, as D-065 labels them: `fees`, the Handbook benchmark
($50,000 cut in half), and `fees_local_half`, real local fees cut in half. Each reform is run on its own
(Ben, 2026-11-17). A scenario the engine cannot run is listed in `meta.scenarios_pending`, never filled with
a stand-in.

Factors the scenario module does not draw itself are drawn here, triangular over config/params/aggregate.yaml
(low, value, high), from `results_seed`: `completion_factor_single_family` (ADU),
`completion_factor_multifamily` (missing middle) and `displacement_share`.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd

import lotline
from lotline.build import eligible, panels
from lotline.config import CONFIG_DIR, load_params
from lotline.model import aggregate, baseline, gutcheck
from lotline.model import eligible_proxy as proxy
from lotline.schemas import SCENARIOS, SCHEMAS_VERSION, validate

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
)
TABLE = {part: f"results_{part}" for part in PARTS}
ENGINE_SCENARIOS = ("adu", "missing_middle", "fees", "fees_local_half")  # scenarios `build_bundle` can fill
# D-065: the bundle's fee scenarios and the `scenarios.fees` mode behind each
FEE_SCENARIOS = {"fees": "handbook", "fees_local_half": "local_half"}
REPO = Path(__file__).resolve().parents[3]


# ---- metadata ---------------------------------------------------------------------------------------------


def config_hash(config_dir: Path = CONFIG_DIR) -> str:
    """sha256 over every file under config/ (sorted relative paths and their bytes)."""
    h = hashlib.sha256()
    for path in sorted(p for p in config_dir.rglob("*") if p.is_file()):
        h.update(str(path.relative_to(config_dir)).encode())
        h.update(b"\0")
        h.update(path.read_bytes())
    return h.hexdigest()


def commit_sha(repo: Path = REPO) -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True)
    return out.stdout.strip()


def tree_state(repo: Path = REPO) -> bool | None:
    """`tree_is_clean`, but None when git can't tell (no repository, no git): `results_meta.tree_clean`."""
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


def tree_is_clean(repo: Path = REPO) -> bool:
    """True when tracked files match HEAD, so `commit_sha` fully identifies the code that ran."""
    out = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo, capture_output=True, text=True
    )
    return out.returncode == 0 and not out.stdout.strip()


def weighted_median(x, w) -> float:
    """The smallest x at which the cumulative weight reaches half the total (weights >= 0, total > 0)."""
    x, w = np.asarray(x, dtype=float), np.asarray(w, dtype=float)
    order = np.argsort(x, kind="stable")
    cum = np.cumsum(w[order])
    return float(x[order][np.searchsorted(cum, 0.5 * cum[-1])])


def overlap_flag(eligible: np.ndarray, distance: np.ndarray, params=None) -> tuple[str, float]:
    """State overlap flag from the eligible-weighted median calibration distance of its places.

    `distance` is `hazard.calibration_distance(...)["total"]` per place (log distance outside the calibration
    range, 0 inside). high at or below `overlap_flag_medium_distance` (0.5: the widening adds a log-sd of 0.5,
    P10-P90 about x0.5-x1.9 at the central widening), low above `overlap_flag_low_distance` (1.0), medium
    between. By hand: places with 60 and 40 eligible parcels at distances 0.3 and 2.0 -> median 0.3, high.
    """
    p = params or load_params("aggregate")
    e = np.asarray(eligible, dtype=float)
    if not e.sum() > 0:
        return "low", float("nan")
    median = weighted_median(distance, e)
    if median > p["overlap_flag_low_distance"].value:
        return "low", median
    if median > p["overlap_flag_medium_distance"].value:
        return "medium", median
    return "high", median


# ---- draws -> tables ------------------------------------------------------------------------------------


def triangular(name: str, n: int, rng: np.random.Generator, file: str = "aggregate") -> np.ndarray:
    s = load_params(file)[name]
    return np.full(n, s.value) if s.low == s.high else rng.triangular(s.low, s.value, s.high, n)


def adu_draws(places: pd.DataFrame, run_draws: Mapping, rng: np.random.Generator) -> pd.DataFrame:
    """`results_draws` rows for the ADU scenario from `adu.run(..., return_draws=True)`'s last element.

    Per draw d: eligible by data tier (after the D-056 scale where applied); pencil-out share = the eligible-
    weighted mean of the pro forma's feasible share; θ = five-year permits added ÷ (eligible × pencil-out);
    net-new share = adu_net_new_share × (1 − adu_formalization_share) of that draw; completion and
    displacement drawn here.
    """
    elig = np.asarray(run_draws["eligible"], dtype=float)  # draws x places
    n = elig.shape[0]
    tiers = places["data_tier"].to_numpy() if "data_tier" in places else np.full(elig.shape[1], 3)
    by_tier = {t: elig[:, tiers == t].sum(axis=1) for t in (1, 2, 3)}
    total = elig.sum(axis=1)
    pencils = (elig * np.asarray(run_draws["pencil"], dtype=float)).sum(axis=1)
    pencil_share = np.divide(pencils, total, out=np.zeros(n), where=total > 0)
    added = np.asarray(run_draws["added"], dtype=float).sum(axis=(1, 2))
    theta = np.divide(added, pencils, out=np.zeros(n), where=pencils > 0)
    sets = run_draws["params"]
    net_new = np.array([p["adu_net_new_share"] * (1 - p["adu_formalization_share"]) for p in sets])
    return pd.DataFrame(
        {
            "scenario": "adu",
            "draw": np.arange(n),
            "eligible_tier1": by_tier[1],
            "eligible_tier2": by_tier[2],
            "eligible_tier3": by_tier[3],
            "theta": theta,
            "pencil_out_share": pencil_share,
            "completion_factor": triangular("completion_factor_single_family", n, rng),
            "net_new_share": net_new,
            "displacement_share": triangular("displacement_share", n, rng),
            "overlap_share": np.nan,
        }
    )


def mm_draws(res, rng: np.random.Generator) -> pd.DataFrame:
    """`results_draws` rows for the missing-middle scenario from `scenarios.mm.simulate`'s `Result` (D-063).

    Per draw d: legal = parcels the Handbook rule newly opens, E × (1 − current dose), by data tier;
    pencil-out share = their feasible-share-weighted mean F(PCR); θ = five-year homes permitted (gross, in
    the added 2-4 unit buildings) ÷ pencil-out parcels; net-new share = 1 − houses torn down ÷ homes
    permitted, that draw's; completion (2+ unit buildings) and displacement drawn here.

    By hand: legal 1,000 in tier 1, pencils 400, 20 homes in 8 buildings that replace 6 houses -> θ 0.05,
    pencil-out 0.4, net-new 0.7; `aggregate.homes_from_draws` then gives 20 permits and 14 × completion homes.
    """
    legal = np.asarray(res.legal, dtype=float)
    n = legal.shape[0]
    total = legal.sum(axis=1)
    pencils = np.asarray(res.pencils, dtype=float)
    gross = res.homes_gross.sum(axis=1)
    torn = res.teardowns.sum(axis=1)
    return pd.DataFrame(
        {
            "scenario": "missing_middle",
            "draw": np.arange(n),
            "eligible_tier1": legal[:, 0],
            "eligible_tier2": legal[:, 1],
            "eligible_tier3": legal[:, 2],
            "theta": np.divide(gross, pencils, out=np.zeros(n), where=pencils > 0),
            "pencil_out_share": np.divide(pencils, total, out=np.zeros(n), where=total > 0),
            "completion_factor": triangular("completion_factor_multifamily", n, rng),
            "net_new_share": np.divide(gross - torn, gross, out=np.ones(n), where=gross > 0),
            "displacement_share": triangular("displacement_share", n, rng),
            "overlap_share": np.nan,
        }
    )


def fee_rows(scenario: str, sim: Mapping, tier: int, rng: np.random.Generator) -> pd.DataFrame:
    """`results_draws` rows for a fee scenario (`fee_rows_and_types` without the size table)."""
    return fee_rows_and_types(scenario, sim, tier, rng)[0]


def fee_rows_and_types(
    scenario: str, sim: Mapping, tier: int, rng: np.random.Generator
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`results_draws` rows for a fee scenario from `scenarios.fees.simulate` (D-065, D-076).

    A fee cut opens no lots, so the funnel's first stage holds homes instead: eligible = the five-year
    baseline homes in the building sizes a cut covers (1, 2 and 3-4 units; 5+ take no dose, D-073), all in
    the state's data tier; pencil-out share = 1; θ = five-year homes added ÷ those homes (the cut's % change,
    ramp included). Completion is drawn here per class (single-family for 1-unit, multifamily for 2-4) and
    weighted by that draw's added homes; net-new share = 1 (the model adds new buildings and tears none
    down); displacement drawn here.

    By hand: 10,000 covered homes, 150 added (120 houses, 30 in 2-4 unit buildings), completion 0.95 and
    0.85 -> θ 0.015, completion 0.93; `aggregate.homes_from_draws` gives 150 permits and 139.5 homes in place.

    The second table is `results_fee_types` for `fees_local_half` (empty otherwise, or without a size split):
    per size and draw the homes added, that size's completion draw (the same draws as above) and baseline.
    """
    n = sim["n"]
    by_class = sim["added_by_class"]
    if by_class:
        covered = sum(sim["by_size"][c].sum() for c in by_class)
        sf = by_class["1"].sum(axis=(1, 2))
        mf = sum(by_class[c].sum(axis=(1, 2)) for c in by_class if c != "1")
    else:  # no size split: every unit takes the house's dose (D-032)
        covered = sim["base"].sum()
        sf = sim["added"].sum(axis=(1, 2))
        mf = np.zeros(n)
    added = sf + mf
    c_sf = triangular("completion_factor_single_family", n, rng)
    c_mf = triangular("completion_factor_multifamily", n, rng)
    completion = np.divide(sf * c_sf + mf * c_mf, added, out=c_sf.copy(), where=added > 0)
    tiers = {t: (covered if t == tier else 0.0) for t in (1, 2, 3)}
    types = pd.DataFrame(columns=[c for c in _columns("fee_types")])
    if scenario == "fees_local_half" and by_class:
        types = pd.concat(
            [
                pd.DataFrame(
                    {
                        "scenario": scenario,
                        "size": c,
                        "draw": np.arange(n),
                        "fee_change_share": 0.5,
                        "units_added": by_class[c].sum(axis=(1, 2)),
                        "completion_factor": c_sf if c == "1" else c_mf,
                        "baseline_homes": float(sim["by_size"][c].sum()),
                    }
                )
                for c in by_class
            ],
            ignore_index=True,
        )
    rows = pd.DataFrame(
        {
            "scenario": scenario,
            "draw": np.arange(n),
            "eligible_tier1": tiers[1],
            "eligible_tier2": tiers[2],
            "eligible_tier3": tiers[3],
            "theta": added / covered if covered > 0 else np.zeros(n),
            "pencil_out_share": 1.0,
            "completion_factor": completion,
            "net_new_share": 1.0,
            "displacement_share": triangular("displacement_share", n, rng),
            "overlap_share": np.nan,
        }
    )
    return rows, types


FEE_STOPS = tuple(round(x / 10, 1) for x in range(-5, 11) if x != 0)  # the slider: up 50% to abolished


def fee_types_with_stops(places: pd.DataFrame, origin: int, draws: int, types: pd.DataFrame) -> pd.DataFrame:
    """`results_fee_types` with every slider stop added for each size that is not linear in the fee change.

    The engine's grid (`fees.change_grid`, same draws as `fees.simulate`) at every stop in `FEE_STOPS`: a size
    whose homes added equal (s ÷ 0.5) × the half cut in every draw and stop (the elasticity route) keeps
    only its 0.5 rows, which the page scales. Any other size (houses on the lot-feasibility route, places
    with a parcel roll) gets the grid's value at every stop, with the draw's completion and the size's
    baseline. Raises if the grid's half cut differs from `types` (they must be the same draws).
    """
    from lotline.model.scenarios import fees

    if types is None or not len(types):
        return types
    grid = fees.change_grid(places, origin, list(FEE_STOPS), draws=draws)
    w = grid.pivot_table(index=["draw", "size"], columns="share", values="units_added", aggfunc="sum")
    tol = 1e-6 * max(1.0, float(w[0.5].abs().max()))
    t = types.assign(draw=types["draw"].astype(int)).set_index(["draw", "size"]).sort_index()
    if not np.allclose(
        w[0.5].reindex(t.index).to_numpy(dtype=float), t["units_added"].to_numpy(float), atol=tol
    ):
        raise ValueError("results_fee_types does not match the engine's grid at a cut of half")
    extra = []
    for size in sorted(set(t.index.get_level_values("size"))):
        ws = w.xs(size, level="size")
        if all(np.allclose(ws[s], (s / 0.5) * ws[0.5], atol=tol) for s in FEE_STOPS):
            continue
        half = t.xs(size, level="size")
        for s in FEE_STOPS:
            if s == 0.5:
                continue
            at_s = ws[s].reindex(half.index).to_numpy(float)
            extra.append(half.assign(fee_change_share=s, units_added=at_s).reset_index().assign(size=size))
    return pd.concat([types, *extra], ignore_index=True) if extra else types


def fee_year_shares(sim: Mapping) -> np.ndarray:
    """Each draw's fee-scenario homes by year as a share of its five-year total (draws x years)."""
    return year_shares({"added": sim["added"]})


def adu_place_type_table(state: str, places: pd.DataFrame, run_draws: Mapping) -> pd.DataFrame:
    """`results_adu_place_types`: the ADU scenario by place type (D-088), from `adu.run`'s draws.

    Per type: places; lots = the median over draws of its eligible lots; base and added = each draw's
    current-rules and added gross ADUs summed over the type's places, averaged over the window years, then
    P10/P50/P90 across draws. By hand: two suburb places with 3 and 5 current-rules ADUs a year and 1 and 2
    added, in every draw -> base 8, added 3.
    """
    kind = places["place_type"].fillna("suburb").to_numpy() if "place_type" in places else None
    cur = np.asarray(run_draws["current"], dtype=float)  # draws x places x years
    add = np.asarray(run_draws["added"], dtype=float)
    elig = np.asarray(run_draws["eligible"], dtype=float)
    rows = []
    for t in ("core", "suburb", "town"):
        on = (kind == t) if kind is not None else np.full(cur.shape[1], t == "suburb")
        if not on.any():
            continue
        b = cur[:, on, :].sum(axis=1).mean(axis=1)
        a = add[:, on, :].sum(axis=1).mean(axis=1)
        (b10, b50, b90), (a10, a50, a90) = np.percentile(b, [10, 50, 90]), np.percentile(a, [10, 50, 90])
        rows.append(
            {
                "state": state,
                "place_type": t,
                "places": int(on.sum()),
                "lots": float(np.median(elig[:, on].sum(axis=1))),
                "base_p10": b10,
                "base": b50,
                "base_p90": b90,
                "added_p10": a10,
                "added": a50,
                "added_p90": a90,
            }
        )
    return pd.DataFrame(rows, columns=["state", *_columns("adu_place_types")])


def adu_baseline_years(state: str, run_draws: Mapping, origin: int, own=None) -> pd.DataFrame:
    """`results_adu_baseline`: statewide current-rules gross ADUs per window year, P10/P50/P90 over draws.

    With `own` (a bool per place: its no-reform rate comes from its own ADU counts), each year also gets the
    mean and, where some places have own counts, `own_counts` and `model` rows: percentiles of each group's
    own sum, and means that add up to the `all` row's (the page splits the bar by them).
    By hand: places with 10 and 4 ADUs a year in every draw, the first with own counts -> all 14, own_counts
    10, model 4; means the same.
    """
    cur_by_place = np.asarray(run_draws["current"], dtype=float)  # draws x places x years
    _, _, first = baseline.window(origin)
    years = range(cur_by_place.shape[2])
    if own is None:
        cur = cur_by_place.sum(axis=1)
        rows = [{"state": state, "period": str(first + y), **_pct(cur[:, y])} for y in years]
        cols = [c for c in _columns("adu_baseline") if c not in ("basis", "mean")]
        return pd.DataFrame(rows, columns=["state", *cols])
    own = np.asarray(own, dtype=bool)
    groups = {"all": np.ones_like(own)} | ({"own_counts": own, "model": ~own} if own.any() else {})
    rows = []
    for basis, m in groups.items():
        cur = cur_by_place[:, m, :].sum(axis=1)
        for y in years:
            a = cur[:, y]
            rows.append(
                {"state": state, "period": str(first + y), "basis": basis, **_pct(a), "mean": a.mean()}
            )
    return pd.DataFrame(rows, columns=["state", *_columns("adu_baseline")])


def affordability_table(state: str, places, run_draws: Mapping, res_mm, fee_places, store) -> pd.DataFrame:
    """`results_affordability`: who the new homes serve (`model/affordability.py`), from the inputs the
    scenarios already used. Empty (no rows) when no HUD income limits file is registered."""
    from lotline.model import affordability

    market = store.read(state, "market_geo_year")
    inputs = affordability.inputs(places, run_draws, getattr(res_mm, "places", None), fee_places, market)
    out = affordability.table(state, inputs)
    return (
        out.astype({"places": "Int64"})
        if len(out)
        else pd.DataFrame(columns=["state", *_columns("affordability")])
    )


def state_stock(
    acs: pd.DataFrame | None, state: str, origin: int, fips: str | None = None
) -> tuple[float, int] | None:
    """The state's housing units (ACS B25024_001, newest 5-year vintage ending by `origin`) and its year."""
    from lotline.config import load_state

    if acs is None or acs.empty:
        return None
    geo = f"state:{fips or load_state(state).fips}"
    rows = acs[(acs["geo"] == geo) & (acs["variable"] == "B25024_001") & (acs["end_year"] <= origin)]
    rows = rows.dropna(subset=["estimate"]).sort_values("end_year")
    return (float(rows["estimate"].iloc[-1]), int(rows["end_year"].iloc[-1])) if len(rows) else None


def shortfall_table(
    state: str, base: pd.DataFrame, acs, origin: int, need_params=None, fips=None
) -> pd.DataFrame:
    """`results_shortfall`: the need left after homes built anyway (`model/shortfall.py`). No row when the
    state has no shortage estimate, no housing stock or no five-year all-sizes baseline."""
    from lotline.model import shortfall

    cols = ["state", *_columns("shortfall")]
    have = aggregate.need(state, need_params)
    stock = state_stock(acs, state, origin, fips)
    five = base[(base["size_class"] == "all") & base["period"].str.contains("-")] if len(base) else base
    if aggregate.SHORTAGE not in have or stock is None or not len(five):
        return pd.DataFrame(columns=cols)
    sh = have[aggregate.SHORTAGE]
    gr = have.get(aggregate.GROWTH)
    growth = (gr.low, gr.value, gr.high) if gr is not None else (0.0, 0.0, 0.0)
    r = load_params("aggregate")["stock_loss_rate"]
    b = five.iloc[0]
    g = shortfall.gap(
        (sh.low, sh.value, sh.high),
        growth,
        stock[0],
        (r.low, r.value, r.high),
        (b["p10"], b["p50"], b["p90"]),
    )
    row = {
        "state": state, "shortage_low": sh.low, "shortage": sh.value, "shortage_high": sh.high,
        "growth_low": growth[0], "growth": growth[1], "growth_high": growth[2],
        "stock": stock[0], "stock_year": stock[1],
        "built_p10": b["p10"], "built": b["p50"], "built_p90": b["p90"], **g,
    }  # fmt: skip
    return pd.DataFrame([row], columns=cols).astype({"stock_year": "Int64"})


def mm_year_shares(res) -> np.ndarray:
    """Each draw's gross missing-middle homes by year as a share of its five-year total (draws x years)."""
    by_year = np.asarray(res.homes_gross, dtype=float)
    tot = by_year.sum(axis=1, keepdims=True)
    return np.divide(by_year, tot, out=np.zeros_like(by_year), where=tot > 0)


def year_shares(run_draws: Mapping) -> np.ndarray:
    """Each draw's permits by year as a share of its five-year total (draws x years)."""
    by_year = np.asarray(run_draws["added"], dtype=float).sum(axis=1)
    tot = by_year.sum(axis=1, keepdims=True)
    return np.divide(by_year, tot, out=np.zeros_like(by_year), where=tot > 0)


def _pct(a) -> dict[str, float]:
    p10, p50, p90 = np.percentile(np.asarray(a, dtype=float), [10, 50, 90])
    return {"p10": p10, "p50": p50, "p90": p90}


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


def _columns(part: str) -> list[str]:
    from lotline.schemas import columns

    return [c for c in columns(TABLE[part]) if c != "state"]


# ---- the baseline ---------------------------------------------------------------------------------------


def baseline_class_draws(panel: pd.DataFrame, state: str, origin: int, params=None):
    """Statewide baseline draws per BPS size class, {size: (window years x draws)} with "all" their sum per
    draw, and the set of places forecast (`baseline_table`)."""
    p = params or load_params("baseline")
    reported = bool(p["use_reported_only"].value)
    _, horizon, _ = baseline.window(origin, p)
    panel = panel[panel["state"] == state.upper()]
    by_class, modelled = {}, set()
    for size in baseline.SIZE_CLASSES:
        table, draws = baseline.forecast_draws(
            panel, baseline.outcome_column(size, reported), origin, params=p
        )
        h = table["horizon"].to_numpy()
        by_class[size] = np.stack([draws[h == k].sum(axis=0) for k in range(1, horizon + 1)]).astype(float)
        modelled |= set(table["geoid"])
    return {"all": sum(by_class.values()), **by_class}, modelled


def baseline_table(
    panel: pd.DataFrame, state: str, origin: int, params=None, class_draws=None
) -> pd.DataFrame:
    """The `baseline` part: statewide homes permitted with no policy change, per size class and period.

    For each BPS size class, `baseline.forecast_draws` gives every place's simulated counts over the window
    (D-061: origin 2025 -> 2027-2031); a draw's statewide count for a year is the sum over places. Places in
    one state share the cycle path within a draw, and every size class samples the same cycle years
    (`baseline.cycle_years` is seeded by state and origin, not by class), so draws line up across classes and
    "all" is their sum within each draw. P10/P50/P90 are taken from those sums, never by adding percentiles.

    `coverage_share`: the origin-year units of the places forecast over the units of every place in the
    panel that year, on the same basis (reported or with imputation). Null when the origin year has none.
    """
    p = params or load_params("baseline")
    reported = bool(p["use_reported_only"].value)
    _, horizon, first = baseline.window(origin, p)
    st = state.upper()
    panel = panel[panel["state"] == st]
    by_class, modelled = class_draws or baseline_class_draws(panel, st, origin, p)
    by_class = {**by_class, "2_4": by_class["2"] + by_class["3_4"]}

    cols = [baseline.outcome_column(s, reported) for s in baseline.SIZE_CLASSES]
    at_origin = panel[panel["year"] == origin]
    units = at_origin[cols].sum(axis=1, min_count=1).fillna(0)
    total = float(units.sum())
    covered = float(units[at_origin["geoid"].isin(modelled)].sum())
    coverage = covered / total if total > 0 else None

    rows = []
    for size, a in by_class.items():  # a: (horizon, draws)
        periods = [(f"{first}-{first + horizon - 1}", a.sum(axis=0))]
        periods += [(str(first + k), a[k]) for k in range(horizon)]
        for period, x in periods:
            rows.append({"size_class": size, "period": period, **_pct(x), "mean": float(x.mean())})
    return pd.DataFrame(rows).assign(
        places=len(modelled),
        coverage_share=coverage,
        basis="reported" if reported else "with_imputation",
        state=st,
    )


# ---- the scorecard ---------------------------------------------------------------------------------------


def historical_floor_rows(
    state: str,
    places: pd.DataFrame,
    run_draws: Mapping,
    adu_counts: pd.DataFrame,
    panel: pd.DataFrame,
    draws: pd.DataFrame,
    origin: int,
    class_draws=None,
) -> list[dict]:
    """`historical_floor` rows (`gutcheck.historical_floor`) for the ADU and missing-middle scenarios.

    - ADUs: places whose local permits flag ADUs, less any still-blind holdout place. With reform = current-
      rules gross ADUs + added, per draw and window year, on those places; observed = their ADU permits.
    - Missing middle: every BPS place. With reform = the baseline's 2-unit and 3-4 unit homes (per draw) +
      the scenario's gross permits added (window total spread evenly); observed = BPS 2-4 unit homes on the
      baseline's basis. Baseline and scenario draws are paired by index (they are independent).
    `class_draws`: `baseline_class_draws`' result, if already computed.
    """
    from lotline.config import load_state
    from lotline.model.scenarios import adu

    st = state.upper()
    why = gutcheck.reasons().get(st, {})
    rows = []
    blind = adu.holdout_stops(load_state(st).holdouts)
    counts = adu_counts[~adu_counts["geoid"].isin(blind)]
    if "*" not in blind and len(counts):
        on = places["geoid"].isin(set(counts["geoid"])).to_numpy()
        cur = np.asarray(run_draws["current"], dtype=float)[:, on, :].sum(axis=1)
        add = np.asarray(run_draws["added"], dtype=float)[:, on, :].sum(axis=1)
        observed = counts.groupby("year")["adu_permits"].sum()
        observed = observed.reindex(range(int(observed.index.min()), origin + 1), fill_value=0)  # floor years
        scope = f"{int(on.sum())} places whose permits flag ADUs"
        rows.append(
            gutcheck.historical_floor("adu", cur + add, observed, origin, scope=scope, reason=why.get("adu"))
        )
    mm = draws[draws["scenario"] == "missing_middle"].sort_values("draw")
    if len(mm):
        reported = bool(load_params("baseline")["use_reported_only"].value)
        by_class, _ = class_draws or baseline_class_draws(panel, st, origin)
        base = (by_class["2"] + by_class["3_4"]).T  # draws x years
        added = aggregate.homes_from_draws(mm)["permits_added"]
        with_reform = base[np.arange(len(added)) % len(base)] + added[:, None] / base.shape[1]
        cols = [baseline.outcome_column(s, reported) for s in ("2", "3_4")]
        p = panel[panel["state"] == st]
        observed = p.groupby("year")[cols].sum().sum(axis=1)
        rows.append(
            gutcheck.historical_floor(
                "missing_middle",
                with_reform,
                observed,
                origin,
                scope="BPS 2-4 unit homes, every place",
                reason=why.get("missing_middle"),
            )
        )
    return rows


def observed_table(
    panel: pd.DataFrame, permits, jurisdictions, state: str, origin: int, years: int = 7, params=None
) -> pd.DataFrame:
    """The `observed` part: what was actually permitted in the `years` years ending at the origin.

    - `homes_2_4`: units in 2-unit and 3-4 unit buildings, summed over every BPS place in the
      (holdout-filtered) panel, on the baseline's basis (`use_reported_only`); `places` counts the places
      with a row that year.
    - `adu_permits`: `adu.observed_adu_counts` (sources that flag ADUs; the larger count where two cover one
      place), summed over places; `places` = every place in those sources over the years, and
      `population_share` the covered places' share of the 2020 population of the state's places (GEOIDs
      longer than 5 characters on both sides, so county remainders are left out). Without permits, or none
      flagged, there are no ADU rows.
    By hand: 2-unit 4 + 3-4 unit 6 in one place and 2 in another in 2025 -> homes_2_4 = 12 from 2 places.
    """
    from lotline.model.scenarios import adu

    p = params or load_params("baseline")
    reported = bool(p["use_reported_only"].value)
    first = origin - years + 1
    st = state.upper()
    w = panel[(panel["state"] == st) & panel["year"].between(first, origin)]
    cols = [baseline.outcome_column(s, reported) for s in ("2", "3_4")]
    rows = []
    for year in range(first, origin + 1):
        y = w[w["year"] == year]
        rows.append(
            {
                "measure": "homes_2_4",
                "year": year,
                "value": float(y[cols].sum().sum()),
                "places": int(y["geoid"].nunique()),
                "population_share": None,
                "basis": "reported" if reported else "with_imputation",
            }
        )
    if permits is not None and len(permits) and adu._is_adu(permits).any():
        counts = adu.observed_adu_counts(permits, first, origin)
        by_year = counts.groupby("year")["adu_permits"].sum()
        covered = set(counts["geoid"])
        share = None
        if jurisdictions is not None and "pop_2020" in jurisdictions:
            pop = jurisdictions.set_index("geoid")["pop_2020"].astype(float)
            places_pop = pop[pop.index.str.len() > 5].sum()
            in_places = pop.reindex(sorted(g for g in covered if len(g) > 5)).sum()
            share = min(1.0, float(in_places / places_pop)) if places_pop > 0 else None
        for year in range(first, origin + 1):
            rows.append(
                {
                    "measure": "adu_permits",
                    "year": year,
                    "value": float(by_year.get(year, 0)),
                    "places": len(covered),
                    "population_share": share,
                    "basis": "flagged_permits",
                }
            )
    return pd.DataFrame(rows).assign(state=st)


# ---- the bundle -----------------------------------------------------------------------------------------


def validate_bundle(bundle: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Every part validated against its `results_*` schema (raises with every error)."""
    missing = set(PARTS) - set(bundle)
    if missing:
        raise KeyError(f"bundle is missing {sorted(missing)}")
    out = {part: validate(bundle[part].reset_index(drop=True), TABLE[part]) for part in PARTS}
    if len(out["meta"]) != 1:
        raise ValueError("a bundle has exactly one meta row")
    unknown = set(out["draws"]["scenario"]) - set(SCENARIOS)
    if unknown:
        raise ValueError(f"unknown scenarios {sorted(unknown)}")
    return out


def _records(df: pd.DataFrame) -> list[dict]:
    """JSON-safe records: missing values become null, numpy scalars plain Python."""
    return json.loads(df.to_json(orient="records", double_precision=15))


def write_bundle(bundle: Mapping[str, pd.DataFrame], path: Path) -> Path:
    """Validate and write `bundle.json`: {meta: {...}, draws: [...], funnel: [...], ...}."""
    b = validate_bundle(bundle)
    doc = {"meta": _records(b["meta"])[0]} | {part: _records(b[part]) for part in PARTS if part != "meta"}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=False) + "\n")
    return path


def read_bundle(path: Path) -> dict[str, pd.DataFrame]:
    """Read and validate a `bundle.json` back into the eight tables."""
    from lotline.schemas import columns

    doc = json.loads(Path(path).read_text())
    raw = {"meta": pd.DataFrame([doc["meta"]])} | {  # parts added later read as empty in older bundles
        part: pd.DataFrame(doc.get(part) or [], columns=columns(TABLE[part]) if not doc.get(part) else None)
        for part in PARTS
        if part != "meta"
    }
    return validate_bundle(raw)


def build_bundle(state: str, store, *, role: str | None = None, origin: int | None = None, draws=None):
    """Run every scenario the engine supports for one state and assemble the eight tables (unwritten)."""
    from lotline.model import fee_inputs
    from lotline.model.scenarios import adu, fees, mm

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
    _, totals_adu, run_draws = adu.run(places, origin, draws=n, eligible_proxy=tier3, return_draws=True)
    d_adu = adu_draws(places, run_draws, rng)
    _, res_mm, _ = mm.run(st, store, origin, n=n)
    tier_parcels = places.groupby("data_tier")["eligible_parcels"].sum() if "data_tier" in places else None
    tier = int(tier_parcels.idxmax()) if tier_parcels is not None and len(tier_parcels) else 3
    fee_places = fee_inputs.statewide_places(st, store, origin)
    fee_sims = {k: fees.simulate(fee_places, origin, mode=m, draws=n) for k, m in FEE_SCENARIOS.items()}
    d_mm = mm_draws(res_mm, rng)  # the shared rng's order: ADU, missing middle, then each fee scenario
    fee_parts = [fee_rows_and_types(k, sim, tier, rng) for k, sim in fee_sims.items()]
    d = pd.concat([d_adu, d_mm, *(rows for rows, _ in fee_parts)], ignore_index=True).assign(state=st)
    fee_types = pd.concat([types for _, types in fee_parts], ignore_index=True).assign(state=st)
    fee_types = fee_types_with_stops(fee_places, origin, n, fee_types)
    shares = {"adu": year_shares(run_draws), "missing_middle": mm_year_shares(res_mm)}
    shares.update({k: fee_year_shares(sim) for k, sim in fee_sims.items()})
    parts = summarize(st, d, origin, shares)

    flag, median_distance = overlap_flag(places["eligible_parcels"], totals_adu["calibration_distance"])
    caveats = []
    if tier3:
        caveats.append(
            "National data only: eligible parcels are ACS single-family homes scaled by D-056 (zoning not "
            "observed); statewide results only."
        )
    tested = post_test(st, origin)
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
                "horizon_years": int(np.asarray(run_draws["added"]).shape[2]),
                "n_draws": n,
                "seed": seed,
                "eligible_proxy": tier3,
                "overlap_flag": flag,
                "overlap_note": f"median calibration distance {median_distance:.2f} (0 = inside the range)",
                "caveats": " ".join(caveats) or None,
                "scenarios_pending": ", ".join(s for s in SCENARIOS if s not in ENGINE_SCENARIOS) or None,
                "tree_clean": tree_state(),
                "post_test": tested[0],
                "post_test_note": tested[1],
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
        "adu_place_types": adu_place_type_table(st, places, run_draws),
        "adu_baseline": adu_baseline_years(
            st, run_draws, origin, own=places["observed_rate"].notna().to_numpy()
        ),
        "affordability": affordability_table(st, places, run_draws, res_mm, fee_places, store),
        "shortfall": shortfall_table(st, base, store.read(st, "acs_geo_year"), origin),
        "fee_types": fee_types,
    }
