"""Holdout registry and the blinding filter (BUILD_PLAN §5.4, validation plan §2).

Held-out outcomes are removed from every table **by default**. A test can be unblinded only once its frozen
prediction, `results/frozen/<test_id>.json`, has been committed and that commit is on `main`. So the
prediction provably existed before anyone looked at the outcome.

Annual tables are filtered conservatively: a year is held out if any day of it falls in the outcome window.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from lotline.config import Holdout, load_state

REPO_ROOT = Path(__file__).resolve().parents[3]
FROZEN_DIR = "results/frozen"


class UnblindError(RuntimeError):
    """Raised when a test is unblinded before its frozen prediction is on main."""


def frozen_path(test_id: str, repo: Path = REPO_ROOT) -> Path:
    return repo / FROZEN_DIR / f"{test_id}.json"


def check_unblind(test_id: str, repo: Path = REPO_ROOT, main: str = "main") -> None:
    """Allow unblinding only if the frozen prediction file was committed in a commit reachable from `main`."""
    path = frozen_path(test_id, repo)
    if not path.exists():
        raise UnblindError(f"{test_id}: no frozen prediction at {path.relative_to(repo)}")
    rel = str(path.relative_to(repo))
    added = _git(repo, "log", "--diff-filter=A", "--format=%H", "-1", "--", rel)
    if not added:
        raise UnblindError(f"{test_id}: {rel} exists but is not committed")
    on_main = subprocess.run(
        ["git", "merge-base", "--is-ancestor", added, main], cwd=repo, capture_output=True
    ).returncode
    if on_main != 0:
        raise UnblindError(f"{test_id}: the commit adding {rel} ({added[:10]}) is not on {main}")


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def holdouts_for(state: str) -> list[Holdout]:
    return load_state(state).holdouts


def held_out_mask(
    df: pd.DataFrame,
    holdouts: Iterable[Holdout],
    *,
    geoid_col: str = "geoid",
    date_col: str | None = None,
    year_col: str | None = None,
) -> pd.Series:
    """True for rows that fall inside any holdout's place and outcome window."""
    if (date_col is None) == (year_col is None):
        raise ValueError("pass exactly one of date_col or year_col")
    mask = pd.Series(False, index=df.index)
    for h in holdouts:
        place = df[geoid_col].astype("string") == h.geoid
        if year_col:
            years = df[year_col]
            in_window = (years >= h.outcome_from.year) & (years <= h.outcome_until.year)
        else:
            dates = pd.to_datetime(df[date_col])
            in_window = (dates >= pd.Timestamp(h.outcome_from)) & (dates <= pd.Timestamp(h.outcome_until))
        mask |= (place & in_window).fillna(False).astype(bool)
    return mask


def apply(
    df: pd.DataFrame,
    state: str,
    *,
    unblind: Iterable[str] = (),
    holdouts: Iterable[Holdout] | None = None,
    repo: Path = REPO_ROOT,
    **cols: str,
) -> pd.DataFrame:
    """Drop held-out rows for `state`, except tests explicitly unblinded (each checked by check_unblind).

    `cols` are passed to held_out_mask (geoid_col, and one of date_col / year_col).
    """
    unblind = set(unblind)
    registry = list(holdouts) if holdouts is not None else holdouts_for(state)
    unknown = unblind - {h.test_id for h in registry}
    if unknown:
        raise UnblindError(f"unknown test ids for {state}: {sorted(unknown)}")
    for test_id in unblind:
        check_unblind(test_id, repo)
    still_blind = [h for h in registry if h.test_id not in unblind]
    return df.loc[~held_out_mask(df, still_blind, **cols)].copy()
