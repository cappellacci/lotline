"""Engine runs as data, for the results dashboard (`model/dashboard.py`).

A run folder holds the CSVs a `--full` run writes (`scripts/dev/estimate_mm.py`, D-024;
`scripts/dev/estimate_pooled_adu.py`, D-025) and a manifest, `run.yaml`: the model and its analysis-plan
entry, a short description of the method, the data scope, the configuration, the status and, once someone has
read the results, the reading. The run scripts write the manifest when they start and update it when they
finish (`start_manifest`, `finish_manifest`); runs made before that have one written by hand from their logs
and plan entries.

`load_run` puts either model's CSVs into one shape (overall effect, effect terms, checks, robustness,
randomization and bootstrap draws, leave one out, out-of-sample tests, added homes), so runs can be compared.
A run with no `estimates.csv` (one that stopped, or never estimated) loads with its manifest only.
Tests: tests/model/test_runs.py.
"""

from __future__ import annotations

import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

MANIFEST = "run.yaml"
STATUSES = ("started", "completed", "no_estimate")

# Short method descriptions copied into each manifest when a run starts, so a manifest keeps the text its run
# used. The full specifications are the analysis-plan entries named in `plan_entry`.
METHODS = {
    "D-024": (
        "Staggered difference-in-differences on Census BPS permits for 2-4 unit homes, places of 10,000+ "
        "people. Main model: D-025's negative binomial with normal place random effects (switch of "
        "2026-10-21), effects by years since a by-right rule (0-1, 2-3, 4+) scaled by its dose, plus "
        "modifiers (price-to-cost, home value) and a rate term. Inference: wild cluster score bootstrap by "
        "place and randomization inference that reassigns adoption paths within state and size band."
    ),
    "D-025": (
        "Pooled hierarchical negative binomial on ADU permits: place random effects integrated by "
        "Gauss-Hermite quadrature, year effects, effects by years since an ADU rule (0-1, 2-3, 4+), "
        "modifiers and a rate term. Inference: wild cluster score bootstrap by place (Webb weights) and "
        "randomization inference over adoption years; five checks, a transport test and HonestDiD bounds "
        "when the pre-trend check fails."
    ),
}

# Effect terms shown on the dashboard, in order, with plain labels; the two models name them differently.
TERM_LABELS = {
    "att": "Overall effect",
    "overall": "Overall effect",
    "beta_0": "Years 0-1",
    "beta_0_1": "Years 0-1",
    "beta_2": "Years 2-3",
    "beta_2_3": "Years 2-3",
    "beta_4": "Years 4+",
    "beta_4p": "Years 4+",
    "theta_pcr": "Price-to-cost modifier",
    "theta_log_value": "Home value modifier",
    "theta_pre_permits": "Pre-reform permits modifier",
    "theta_hh_growth": "Household growth modifier",
    "rho": "Rate x treated",
    "delta": "Other rule on the lot",  # D-024: an ADU rule; D-025: 2-4 units by right
}
OVERALL = ("att", "overall")
# Robustness fits under one name across runs: the October D-024 run's main model was the Poisson-gamma ("re")
# and its robustness line D-025's negative binomial ("nb"); from 2026-10-21 the two swap places.
FIT_LABELS = {
    "main (re)": "Main: Poisson-gamma",
    "main (nb)": "Main: negative binomial",
    "re": "Poisson-gamma",
    "nb": "Negative binomial (D-025's)",
    "ppml": "PPML",
    "imputation": "Borusyak imputation",
    "additive imputation": "Additive imputation (D-031)",
    "binary dose": "Binary by-right dose",
    "four modifiers": "All four modifiers",
    "sensitivity tags": "Firm dates only",
    "firm dates only": "Firm dates only",
}


def _git_commit(repo: Path) -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_manifest(folder: Path) -> dict:
    path = Path(folder) / MANIFEST
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _write_manifest(folder: Path, m: dict) -> Path:
    path = Path(folder) / MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(m, sort_keys=False, allow_unicode=True, width=110))
    return path


def start_manifest(
    folder: Path,
    *,
    model: str,
    title: str,
    plan_entry: str,
    scope: dict,
    config: dict,
    repo: Path | None = None,
) -> Path:
    """Write `run.yaml` with status "started": the model's method text (`METHODS`), the commit, the command
    and the start time. Called by a run script before its first fit, so a run that stops still has one."""
    if model not in METHODS:
        raise ValueError(f"unknown model {model!r}; choose from {sorted(METHODS)}")
    m = {
        "id": Path(folder).name,
        "title": title,
        "model": model,
        "plan_entry": plan_entry,
        "status": "started",
        "started": _now(),
        "commit": _git_commit(repo or Path(__file__).resolve().parents[3]),
        "command": " ".join(sys.argv),
        "method": METHODS[model],
        "scope": scope,
        "config": config,
    }
    return _write_manifest(folder, m)


def panel_scope(panel: pd.DataFrame, outcome: str, **extra) -> dict:
    """A manifest's data scope from an estimation panel (columns `place`, `state`, `year`, `T`, and `y` when
    some years have no outcome). By hand: places 1 (MN, T 2018) and 2 (TX, never treated), 2016-2018 ->
    states MN, TX; 2 places, 6 place-years, 1 treated, 1 adopting in the window."""
    places = panel.drop_duplicates("place")
    treated = places[places["T"].notna()]
    years = (int(panel["year"].min()), int(panel["year"].max()))
    rows = panel["y"].notna() if "y" in panel.columns else pd.Series(True, index=panel.index)
    return {
        "states": sorted(panel["state"].dropna().unique().tolist()),
        "years": f"{years[0]}-{years[1]}",
        "outcome": outcome,
        "places": int(len(places)),
        "place_years": int(rows.sum()),
        "treated": int(len(treated)),
        "adopting_in_window": int(treated["T"].between(*years).sum()),
        "places_by_state": {str(k): int(v) for k, v in places["state"].value_counts().sort_index().items()},
        **extra,
    }


def finish_manifest(folder: Path, status: str = "completed", note: str = "") -> Path:
    """Set a run's status (and an optional note) and its finish time."""
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}; choose from {STATUSES}")
    m = read_manifest(folder)
    m.update(status=status, finished=_now())
    if note:
        m["status_note"] = note
    return _write_manifest(folder, m)


def _csv(folder: Path, name: str) -> pd.DataFrame | None:
    path = folder / f"{name}.csv"
    if not path.exists():
        return None
    try:
        # codes and labels stay text (`iterrows` would otherwise turn place 2701486 into 2701486.0)
        return pd.read_csv(path, dtype={c: str for c in ("place", "left_out", "name", "test", "year")})
    except pd.errors.EmptyDataError:  # a stage that found nothing to write (e.g. no transport rows)
        return None


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _bool(v) -> bool | None:
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v in ("True", "False"):
        return v == "True"
    return None if _num(v) is None else bool(v)


def _text(v) -> str:
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)


def _interval(row, est: str = "estimate") -> dict:
    return {"estimate": _num(row.get(est)), "low": _num(row.get("low")), "high": _num(row.get("high"))}


def _names(folder: Path) -> dict[str, str]:
    names: dict[str, str] = {}
    for name in ("added_homes", "transport"):
        df = _csv(folder, name)
        if df is not None and {"place", "name"} <= set(df.columns):
            names.update(dict(zip(df["place"].astype(str), df["name"].astype(str), strict=False)))
    return names


def _checks(df: pd.DataFrame | None) -> list[dict]:
    out = []
    for _, r in (df if df is not None else pd.DataFrame()).iterrows():
        row = r.to_dict()
        est = "estimate" if _num(row.get("estimate")) is not None else "estimate_att"
        out.append(
            {
                "name": _text(row.get("check")),
                "pass": _bool(row.get("pass")),
                **_interval(row, est),
                "statistic": _num(row.get("statistic")),
                "p": _num(row.get("p")),
                "note": "; ".join(t for t in (_text(row.get("note")), _text(row.get("convergence"))) if t),
            }
        )
    return out


def _robustness(folder: Path) -> list[dict]:
    """Every alternative fit's overall effect: D-024's `robustness.csv` rows, D-025's `robust_*.csv` files and
    `sensitivity.csv` rows, and the tag sensitivity (`sensitivity_tags.csv`)."""
    out = []
    df = _csv(folder, "robustness")
    if df is not None:
        for _, r in df[df["term"].isin(OVERALL)].iterrows():
            fit = _text(r["fit"])
            out.append({"fit": FIT_LABELS.get(fit, fit), **_interval(r.to_dict())})
    for path in sorted(folder.glob("robust_*.csv")) + sorted(folder.glob("sensitivity_tags.csv")):
        df = pd.read_csv(path)
        if "term" not in df.columns:
            continue
        rows = df[df["term"].isin(OVERALL)]
        fit = path.stem.removeprefix("robust_").replace("_", " ")
        fit = FIT_LABELS.get(fit, fit)
        for _, r in rows.iterrows():
            out.append({"fit": fit, **_interval(r.to_dict())})
    df = _csv(folder, "sensitivity")
    if df is not None and "check" in df.columns:
        for _, r in df.iterrows():
            out.append({"fit": _text(r["check"]), **_interval(r.to_dict())})
    return out


def _draws(df: pd.DataFrame | None, cols: tuple[str, ...]) -> list[float]:
    if df is None:
        return []
    col = next((c for c in cols if c in df.columns), None)
    return [] if col is None else [x for x in (_num(v) for v in df[col]) if x is not None]


def _randomization(df: pd.DataFrame | None) -> dict | None:
    if df is None or df.empty:
        return None
    obs = "att" if "att" in df.columns else "overall"
    return {
        "observed": _num(df[obs].iloc[0]),
        "p": _num(df["p"].iloc[0]),
        "draws": _draws(df, ("att_permuted", "overall_permuted")),
        "failed": int(df["failed"].iloc[0]) if "failed" in df.columns else None,
    }


def _leave_one_out(df: pd.DataFrame | None, names: dict[str, str]) -> list[dict]:
    if df is None:
        return []
    key = "left_out" if "left_out" in df.columns else "place"
    val = "att" if "att" in df.columns else "overall_without"
    return [
        {"left_out": names.get(str(r[key]), str(r[key])), "estimate": _num(r[val])} for _, r in df.iterrows()
    ]


def _records(df: pd.DataFrame | None, cols: list[str]) -> list[dict]:
    if df is None:
        return []
    keep = [c for c in cols if c in df.columns]
    text = ("place", "name", "test", "year")  # a transport table's year is a year or "total"
    return [
        {c: (_text(v) if c in text else _num(v)) for c, v in r.items()} for r in df[keep].to_dict("records")
    ]


def load_run(folder: Path) -> dict:
    """One run folder as plain data (JSON-ready; missing numbers are None). Keys: `id`, `manifest`, `status`,
    `overall`, `terms`, `checks`, `robustness`, `randomization`, `bootstrap`, `leave_one_out`, `transport`,
    `transport_verdict`, `added_homes`."""
    folder = Path(folder)
    m = read_manifest(folder)
    est = _csv(folder, "estimates")
    status = m.get("status") or ("completed" if est is not None else "no_estimate")
    if status == "started" and est is not None:
        status = "completed"
    terms, overall = [], None
    if est is not None:
        for _, r in est.iterrows():
            t = str(r["term"])
            if t not in TERM_LABELS:
                continue
            row = {"term": t, "label": TERM_LABELS[t], **_interval(r.to_dict())}
            if t in OVERALL:
                overall = row
            terms.append(row)
    names = _names(folder)
    tv = _csv(folder, "transport_verdict")
    if tv is not None and "test" not in tv.columns:
        tv = tv.assign(test="Transport test")
    transport = _csv(folder, "transport")
    if transport is not None and "test" not in transport.columns:
        transport = transport.assign(test="Transport test")
    return {
        "id": m.get("id") or folder.name,
        "manifest": m,
        "status": status,
        "overall": overall,
        "terms": terms,
        "checks": _checks(_csv(folder, "checks")),
        "robustness": _robustness(folder),
        "randomization": _randomization(_csv(folder, "randomization")),
        "bootstrap": _draws(_csv(folder, "bootstrap_draws"), OVERALL),
        "leave_one_out": _leave_one_out(_csv(folder, "leave_one_out"), names),
        "transport": _records(transport, ["test", "place", "name", "year", "observed", "mean", "p10", "p90"]),
        "transport_verdict": [
            {
                "test": _text(r["test"]),
                "pass": _bool(r["pass"]),
                "coverage": _num(r.get("yearly_coverage_80")),
            }
            for _, r in (tv if tv is not None else pd.DataFrame()).iterrows()
        ],
        "added_homes": _records(
            _csv(folder, "added_homes"), ["place", "name", "years", "added", "low", "high"]
        ),
    }


def find_runs(root: Path) -> list[Path]:
    """Every folder under `root` holding a `run.yaml`, oldest start first."""
    found = [p.parent for p in Path(root).rglob(MANIFEST)]
    return sorted(found, key=lambda f: (str(read_manifest(f).get("started", "")), f.name))
