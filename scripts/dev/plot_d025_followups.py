#!/usr/bin/env python3
"""Charts for the D-025 follow-ups (D-031 dated notes): as-run vs corrected main, the event study, and the
HonestDiD sensitivity. Reads committed run outputs only; no estimation.

    uv run python scripts/dev/plot_d025_followups.py

Inputs: reports/adu-d025/run-2026-10-20-log.txt (the as-run main, printed table),
reports/adu-d025/corrected-2026-10-21/estimates.csv, and, when present, the HonestDiD outputs in
reports/adu-d025/corrected-2026-10-21/ (event_study.csv, honest_bounds.csv, honest_bands.csv). Writes PNGs to
reports/adu-d025/figures/.
"""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path("reports/adu-d025")
CORR = ROOT / "corrected-2026-10-21"
OUT = ROOT / "figures"

# reference palette (dataviz skill, light mode); slots 1-2 validated: CVD ΔE 24.7, normal 33.6
SURFACE, TEXT, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = {"As-run main (2026-10-20)": "#2a78d6", "Corrected household growth (2026-10-21)": "#eb6834"}
TERMS = {
    "theta_hh_growth": "Household growth modifier (θ, per SD)",
    "beta_0_1": "Effect, 0–1 years after adoption",
    "beta_2_3": "Effect, 2–3 years after adoption",
    "beta_4p": "Effect, 4+ years after adoption",
    "overall": "Overall effect",
}


def style(ax, xlabel: str) -> None:
    ax.set_facecolor(SURFACE)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT2, length=0)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel(xlabel, color=TEXT2)


def as_run_table() -> pd.DataFrame:
    """The as-run main's estimates table, parsed from the first run's log."""
    lines = (ROOT / "run-2026-10-20-log.txt").read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip().startswith("term"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("overall")) + 1
    return pd.read_csv(io.StringIO("\n".join(lines[start:end])), sep=r"\s+")


def comparison() -> Path:
    tabs = {
        "As-run main (2026-10-20)": as_run_table().set_index("term"),
        "Corrected household growth (2026-10-21)": pd.read_csv(CORR / "estimates.csv").set_index("term"),
    }
    fig, ax = plt.subplots(figsize=(8.5, 4.6), facecolor=SURFACE)
    terms = list(TERMS)
    for j, (label, tab) in enumerate(tabs.items()):
        for i, t in enumerate(terms):
            y = len(terms) - 1 - i + (0.17 if j == 0 else -0.17)
            r = tab.loc[t]
            ax.plot([r["low"], r["high"]], [y, y], color=SERIES[label], linewidth=2, solid_capstyle="round")
            ax.plot(
                r["estimate"],
                y,
                "o",
                color=SERIES[label],
                markersize=8,
                markeredgecolor=SURFACE,
                markeredgewidth=2,
                label=label if i == 0 else None,
            )
            ax.annotate(
                f"{r['estimate']:.2f}",
                (r["high"], y),
                xytext=(6, 0),
                textcoords="offset points",
                va="center",
                fontsize=8,
                color=TEXT2,
            )
    ax.axvline(0, color=TEXT2, linewidth=1)
    ax.set_yticks(range(len(terms)), [TERMS[t] for t in reversed(terms)], color=TEXT)
    style(ax, "Log scale: additional ADU permits relative to no by-right rule (90% intervals)")
    fig.suptitle(
        "Correcting household growth barely moves the ADU estimate",
        x=0.01,
        ha="left",
        color=TEXT,
        fontsize=12,
        fontweight="bold",
    )
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.0),
        ncol=2,
        frameon=False,
        fontsize=8,
        labelcolor=TEXT2,
        handletextpad=0.3,
    )
    fig.tight_layout()
    path = OUT / "asrun_vs_corrected.png"
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return path


def event_study() -> Path | None:
    """Leads (k = −3…−1) and bands from the pre-trend-leads refit, with 90% intervals (event_study.csv:
    term, k_label, estimate, low, high)."""
    f = CORR / "event_study.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    fig, ax = plt.subplots(figsize=(8.5, 4.2), facecolor=SURFACE)
    color = SERIES["Corrected household growth (2026-10-21)"]
    x = range(len(d))
    ax.vlines(x, d["low"], d["high"], color=color, linewidth=2)
    ax.plot(x, d["estimate"], "o", color=color, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.axhline(0, color=TEXT2, linewidth=1)
    n_pre = int((d["term"].str.startswith("lead")).sum())
    ax.axvline(n_pre - 0.5, color=GRID, linewidth=1, linestyle="--")
    ax.text(n_pre - 0.45, ax.get_ylim()[1], " adoption", color=TEXT2, fontsize=8, va="top")
    ax.set_xticks(list(x), d["k_label"], color=TEXT)
    ax.set_facecolor(SURFACE)
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.tick_params(colors=TEXT2, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_ylabel("Log difference vs. 4+ years before / never treated", color=TEXT2)
    ax.set_xlabel("Years relative to the by-right ADU rule", color=TEXT2)
    ax.set_title(
        "ADU permits were already rising before adoption (pre-trend leads)",
        loc="left",
        color=TEXT,
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout()
    path = OUT / "event_study_corrected.png"
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return path


def honest() -> Path | None:
    """Robust 90% intervals against M̄ (relative magnitudes) and M (smoothness) for the pooled effect, with
    the original estimate and the breakdown M̄ (honest_bounds.csv from pooled_adu.honest_bounds, plus a
    row restriction='original')."""
    f = CORR / "honest_bounds.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    orig = d[d["restriction"] == "original"].iloc[0]
    color = SERIES["Corrected household growth (2026-10-21)"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), facecolor=SURFACE, sharey=True)
    panels = (
        ("relative magnitudes", "M̄ (post-adoption drift / largest pre-adoption step)"),
        ("smoothness", "M (change in the pre-trend's slope, log points per year²)"),
    )
    for ax, (kind, xlabel) in zip(axes, panels, strict=True):
        s = d[d["restriction"] == kind]
        xs = ["original", *[f"{m:g}" for m in s["m"]]]
        lows = [orig["ci_low"], *s["ci_low"]]
        highs = [orig["ci_high"], *s["ci_high"]]
        ax.vlines(range(len(xs)), lows, highs, color=[TEXT2] + [color] * len(s), linewidth=3)
        ax.plot([0], [orig["set_low"]], "o", color=TEXT2, markersize=8)
        ax.axhline(0, color=TEXT2, linewidth=1)
        ax.set_xticks(range(len(xs)), xs, color=TEXT)
        ax.set_facecolor(SURFACE)
        for sp in ("top", "right", "bottom"):
            ax.spines[sp].set_visible(False)
        ax.spines["left"].set_color(GRID)
        ax.tick_params(colors=TEXT2, length=0)
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xlabel(xlabel, color=TEXT2, fontsize=9)
        ax.set_title(kind.capitalize(), loc="left", color=TEXT, fontsize=10)
        if kind == "relative magnitudes" and "breakdown" in d.columns and pd.notna(orig.get("breakdown")):
            ax.text(
                len(xs) - 0.6,
                ax.get_ylim()[1],
                f"breakdown M̄ = {orig['breakdown']:.2f}",
                ha="right",
                va="top",
                color=TEXT2,
                fontsize=9,
            )
    axes[0].set_ylabel("Pooled effect, robust 90% interval (log)", color=TEXT2)
    fig.suptitle(
        "How large a continued pre-trend would erase the ADU effect? (HonestDiD)",
        x=0.01,
        ha="left",
        color=TEXT,
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout()
    path = OUT / "honestdid_corrected.png"
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for p in (comparison(), event_study(), honest()):
        print(p or "skipped (input not computed yet)")


if __name__ == "__main__":
    main()
