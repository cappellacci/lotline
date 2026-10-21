#!/usr/bin/env python3
"""Charts for the D-025 follow-ups (D-031 dated notes): as-run vs corrected main, the event study, and the
HonestDiD sensitivity. Reads committed run outputs only; no estimation.

    uv run python scripts/dev/plot_d025_followups.py

Inputs: reports/adu-d025/run-2026-10-20-log.txt (the as-run main, printed table),
reports/adu-d025/corrected-2026-10-21/estimates.csv, and, when present, the HonestDiD outputs
(event_study.csv, honest_bounds.csv) in reports/adu-d025/honest-asrun-2026-10-21/ and
honest-corrected-2026-10-21/. Writes PNGs to reports/adu-d025/figures/.
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


HONEST = {
    "As-run main (2026-10-20)": ROOT / "honest-asrun-2026-10-21",
    "Corrected household growth (2026-10-21)": ROOT / "honest-corrected-2026-10-21",
}
BANDS_ORDER = ["beta_0_1", "beta_2_3", "beta_4p"]


def _axes(ax, ylabel: str | None = None) -> None:
    ax.set_facecolor(SURFACE)
    for sp in ("top", "right", "bottom"):
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.tick_params(colors=TEXT2, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    if ylabel:
        ax.set_ylabel(ylabel, color=TEXT2)


def _title(fig, text: str) -> None:
    fig.suptitle(text, x=0.01, ha="left", color=TEXT, fontsize=12, fontweight="bold")


def event_study() -> Path | None:
    """Leads (k = −3…−1) and bands from each main's pre-trend-leads refit, with 90% intervals."""
    tabs = {lab: d / "event_study.csv" for lab, d in HONEST.items() if (d / "event_study.csv").exists()}
    if not tabs:
        return None
    fig, ax = plt.subplots(figsize=(8.5, 4.4), facecolor=SURFACE)
    slots = ["lead_3", "lead_2", "lead_1", *BANDS_ORDER]
    labels = ["−3", "−2", "−1", "0–1", "2–3", "4+"]
    for j, (label, f) in enumerate(tabs.items()):
        d = pd.read_csv(f)
        x = [slots.index(t) + (-0.12 if j == 0 else 0.12) for t in d["term"]]
        ax.vlines(x, d["low"], d["high"], color=SERIES[label], linewidth=2)
        ax.plot(
            x,
            d["estimate"],
            "o",
            color=SERIES[label],
            markersize=8,
            markeredgecolor=SURFACE,
            markeredgewidth=2,
            label=label,
        )
        missing_lead_1 = "lead_1" not in set(d["term"])
    if missing_lead_1:  # 0 ADU permits the year before adoption: estimate at −∞, not estimable
        ax.text(
            2,
            0.15,
            "not estimable:\n0 permits in\n22 place-years",
            ha="center",
            va="bottom",
            fontsize=8,
            color=TEXT2,
        )
        ax.annotate("", (2, -2.2), (2, 0.05), arrowprops={"arrowstyle": "->", "color": TEXT2})
    ax.axhline(0, color=TEXT2, linewidth=1)
    ax.axvline(2.5, color=TEXT2, linewidth=1, linestyle=":")
    ax.set_xticks(range(len(slots)), labels, color=TEXT)
    _axes(ax, "Log difference vs 4+ years before / never treated")
    ax.set_xlabel("Years relative to the by-right ADU rule (leads, then bands)", color=TEXT2)
    _title(fig, "Before adoption, ADU permits spiked at −3 years, then fell to zero the year before")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=8, labelcolor=TEXT2)
    fig.tight_layout()
    path = OUT / "event_study.png"
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return path


def permits_by_event_time() -> Path | None:
    """Raw ADU permits per 1,000 eligible parcels by years since adoption, places adopting 2017+
    (permits_by_event_time.csv; descriptive, no model)."""
    f = ROOT / "honest-corrected-2026-10-21" / "permits_by_event_time.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    fig, ax = plt.subplots(figsize=(8.5, 4.2), facecolor=SURFACE)
    color = SERIES["As-run main (2026-10-20)"]
    ax.bar(d["k"], d["per_1000_parcels"], width=0.7, color=color, edgecolor=SURFACE, linewidth=2)
    for _, r in d.iterrows():
        ax.annotate(
            f"{int(r['adu_permits'])} / {int(r['place_years'])}",
            (r["k"], r["per_1000_parcels"]),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=TEXT2,
        )
    ax.axvline(-0.5, color=TEXT2, linewidth=1, linestyle=":")
    ax.text(-0.45, ax.get_ylim()[1] * 0.95, " rule takes effect", color=TEXT2, fontsize=8, va="top")
    ax.set_xticks(
        d["k"].astype(int), [f"{int(k):+d}".replace("-", "−") if k else "0" for k in d["k"]], color=TEXT
    )
    _axes(ax, "ADU permits per 1,000 eligible parcels a year")
    ax.set_xlabel("Years since the by-right ADU rule (labels: permits / place-years)", color=TEXT2)
    _title(fig, "Treated places issued no ADU permits the year before their rule took effect")
    fig.tight_layout()
    path = OUT / "permits_by_event_time.png"
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for p in (comparison(), event_study(), permits_by_event_time()):
        print(p or "skipped (input not computed yet)")


if __name__ == "__main__":
    main()
