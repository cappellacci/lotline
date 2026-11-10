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
- `observed`: what was actually permitted in the years before the window (`observed_table`): ADU permits where
  local data flag them, and homes in 2-4 unit buildings from BPS.

Which scenarios: the engine runs the ADU and missing-middle (D-063) scenarios statewide. Fees (a statewide
baseline forecast for every place) and the stacked combinations (`model/combine.py` not yet written) are
listed in `meta.scenarios_pending`, never filled with stand-ins.

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

PARTS = ("meta", "draws", "funnel", "totals", "need", "scorecard", "baseline", "observed")
TABLE = {part: f"results_{part}" for part in PARTS}
ENGINE_SCENARIOS = ("adu", "missing_middle")  # scenarios `build_bundle` can fill today
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
    raw = {"meta": pd.DataFrame([doc["meta"]])} | {
        part: pd.DataFrame(doc[part], columns=columns(TABLE[part]) if not doc[part] else None)
        for part in PARTS
        if part != "meta"
    }
    return validate_bundle(raw)


def build_bundle(state: str, store, *, role: str | None = None, origin: int | None = None, draws=None):
    """Run every scenario the engine supports for one state and assemble the eight tables (unwritten)."""
    from lotline.model.scenarios import adu, mm

    st = state.upper()
    agg = load_params("aggregate")
    origin = int(agg["results_origin_year"].value) if origin is None else int(origin)
    n = int(draws or agg["results_draws"].value)
    seed = int(agg["results_seed"].value)
    rng = np.random.default_rng(seed)

    places = adu.places_from_store(st, store, origin)
    places = places[places["rent"].notna() & places["home_value"].notna()].reset_index(drop=True)
    places["state"] = st
    tier3 = bool(proxy.proxy_states(places))
    _, totals_adu, run_draws = adu.run(places, origin, draws=n, eligible_proxy=tier3, return_draws=True)
    d_adu = adu_draws(places, run_draws, rng)
    _, res_mm, _ = mm.run(st, store, origin, n=n)
    d = pd.concat([d_adu, mm_draws(res_mm, rng)], ignore_index=True).assign(state=st)
    parts = summarize(
        st, d, origin, {"adu": year_shares(run_draws), "missing_middle": mm_year_shares(res_mm)}
    )

    flag, median_distance = overlap_flag(places["eligible_parcels"], totals_adu["calibration_distance"])
    tier_parcels = places.groupby("data_tier")["eligible_parcels"].sum() if "data_tier" in places else None
    caveats = []
    if tier3:
        caveats.append(
            "National data only: eligible parcels are ACS single-family homes scaled by D-056 (zoning not "
            "observed); statewide results only."
        )
    meta = pd.DataFrame(
        [
            {
                "state": st,
                "state_role": role or ("national_only" if tier3 else "development"),
                "data_tier": int(tier_parcels.idxmax())
                if tier_parcels is not None and len(tier_parcels)
                else 3,
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
                "scenarios_pending": ", ".join(s for s in SCENARIOS if s not in ENGINE_SCENARIOS),
            }
        ]
    )
    panel = panels.load(st, store, theme="adu", rule_version=eligible.RULE_VERSION)
    class_draws = baseline_class_draws(panel, st, origin)
    base = baseline_table(panel, st, origin, class_draws=class_draws)
    k = int(agg["historical_floor_years"].value)
    adu_counts = adu.observed_adu_counts(store.read(st, "permits"), origin - k + 1, origin)
    rows = historical_floor_rows(st, places, run_draws, adu_counts, panel, d, origin, class_draws)
    scorecard = pd.DataFrame(rows, columns=_columns("scorecard")).assign(state=st)
    seen = observed_table(panel, store.read(st, "permits"), store.read(st, "jurisdictions"), st, origin)
    return {"meta": meta, "draws": d, **parts, "scorecard": scorecard, "baseline": base, "observed": seen}
