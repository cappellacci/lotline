"""Final (reconciled) codings -> `reforms` rows, validated against the schema; and a field-level comparison
with rows already in config/reforms/<st>.csv (the dry-run check).

Conventions carried over from earlier coding (lessons register §3):
- `reform_id` = `<ST>-<geoid>-adu-<effective year>` (a letter suffix when one place has two eras in a year).
- Each later era `supersedes` the one before; the earlier era's `end_date` is the successor's effective date.
- A "no ADUs" era (`adus_per_lot = 0`) gets `by_right = False` and the `NO ADU RULE` notes prefix.
- `source_quote` is the quote behind the most decisive field (adus_per_lot, then by_right, …), <= 300 chars.
- `coding_notes` carries the date rule that fired, tags, and every field's source (so nothing is lost).
Rows are proposals: they are written to the run folder, never straight into config/ (a dated script applies
accepted rows, as before).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from lotline.rule_agents.adu import dates as D
from lotline.rule_agents.adu.coding import RUBRIC_FIELDS, Era, PlaceCoding
from lotline.schemas import columns, validate

KEY_ORDER = (
    "adus_per_lot",
    "by_right",
    "adu_detached_allowed",
    "owner_occ",
    "adu_max_sqft",
    "parking_min_per_unit",
    "min_lot_sqft",
    "coverage_zones",
)
BOOL_COLS = ["by_right", "owner_occ", "adu_detached_allowed", "lot_split"]
CODER, CODER_2, VERIFIER = "claude-rules-adu", "claude-rules-adu-blind", "claude-rules-adu-verifier"


def _key_evidence(era: Era):
    for f in KEY_ORDER:
        fv = era.fields.get(f)
        if fv and fv.value is not None and fv.evidence:
            return fv.evidence[0]
    d = era.dates[0]
    return d.evidence[0]


def _notes(era: Era, resolved: D.ResolvedDates, agreement_note: str) -> str:
    parts = []
    if era.value("adus_per_lot") == 0:
        parts.append("NO ADU RULE (adus_per_lot = 0).")
    tags = sorted(set(era.tags) | set(resolved.tags))
    if tags:
        parts.append(" ".join(tags) + ".")
    parts.append(f"Dates: {resolved.rule}.")
    if resolved.conflict:
        parts.append(f"CONFLICT: {resolved.conflict}.")
    for f in RUBRIC_FIELDS:
        fv = era.fields.get(f)
        if fv is None:
            continue
        if fv.value is None:
            if fv.note:
                parts.append(f"{f} blank: {fv.note}.")
            continue
        srcs = "; ".join(
            f"{e.url}" + (f" {e.section}" if e.section else "") + f" [{e.kind}]" for e in fv.evidence
        )
        parts.append(
            f"{f}={fv.value} ({fv.confidence}) <- {srcs}" + (f" ({fv.note})" if fv.note else "") + "."
        )
    parts.append(agreement_note)
    return " ".join(parts)


def build(coding: PlaceCoding, agreement: str, verified_on: dt.date | None = None) -> list[dict]:
    """Rows for one place (oldest era first). `agreement` is the schema CODER_AGREEMENT value."""
    eras = sorted(coding.eras, key=lambda e: D.resolve(e.dates).effective)
    rows: list[dict] = []
    ids: set[str] = set()
    for _i, era in enumerate(eras):
        r = D.resolve(era.dates)
        rid = f"{coding.state}-{coding.geoid}-adu-{r.effective.year}"
        suffix = iter("bcdefgh")
        while rid in ids:
            rid = f"{coding.state}-{coding.geoid}-adu-{r.effective.year}{next(suffix)}"
        ids.add(rid)
        ev = _key_evidence(era)
        urls = []
        for e in [x for fv in era.fields.values() for x in fv.evidence] + [
            x for d in era.dates for x in d.evidence
        ]:
            if e.url not in urls:
                urls.append(e.url)
        row = {c: None for c in columns("reforms")}
        row.update(
            reform_id=rid,
            state=coding.state,
            jurisdiction_geoid=coding.geoid,
            theme="adu",
            component=era.component,
            status=era.status,
            announced_date=r.announced,
            adoption_date=r.adoption,
            effective_date=r.effective,
            end_date=era.end_date,
            supersedes=rows[-1]["reform_id"] if rows else None,
            source_url=";".join(urls),
            source_section=ev.section,
            source_quote=ev.quote[:300],
            verified_by=VERIFIER if verified_on else None,
            verified_date=verified_on,
            coder=CODER,
            coder_2=CODER_2 if agreement != "single_coder" else None,
            coder_agreement=agreement,
        )
        for f in RUBRIC_FIELDS:
            row[f] = era.value(f)
        if era.value("adus_per_lot") == 0:
            row["by_right"] = False
        if not row["coverage"]:
            row["coverage"] = "Not stated in the coded sources"
        note = f"Coded by the ADU rule agent swarm ({coding.coder}); coder agreement: {agreement}."
        row["coding_notes"] = _notes(era, r, note)
        if rows and rows[-1]["end_date"] is None:
            rows[-1]["end_date"] = r.effective
        rows.append(row)
    return rows


def to_frame(rows: list[dict]) -> pd.DataFrame:
    """Rows as a `reforms` table, validated (raises pandera SchemaErrors listing every problem)."""
    df = pd.DataFrame(rows, columns=columns("reforms"))
    for c in ("announced_date", "adoption_date", "effective_date", "end_date", "verified_date"):
        df[c] = pd.to_datetime(df[c])
    for c in BOOL_COLS:
        df[c] = df[c].astype("boolean")
    for c in ("unit_cap", "adus_per_lot", "dollar_year"):
        df[c] = pd.to_numeric(df[c]).astype("Int64")
    for c in (
        "far_cap",
        "max_stories",
        "min_lot_sqft",
        "adu_max_sqft",
        "parking_min_per_unit",
        "fee_change_usd",
    ):
        df[c] = pd.to_numeric(df[c]).astype(float)
    obj = [c for c in df.columns if df[c].dtype == object]
    df[obj] = df[obj].astype(object).where(df[obj].notna(), None)
    return validate(df, "reforms")


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    out = df.copy()
    for c in ("announced_date", "adoption_date", "effective_date", "end_date", "verified_date"):
        out[c] = out[c].dt.strftime("%Y-%m-%d")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)


# ---- comparison with coded rows ---------------------------------------------------------------------------

COMPARE_FIELDS = (
    "effective_date",
    "adoption_date",
    "adus_per_lot",
    "by_right",
    "owner_occ",
    "adu_detached_allowed",
    "adu_max_sqft",
    "parking_min_per_unit",
    "min_lot_sqft",
)


def read_config(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False).replace("", pd.NA)
    return raw[raw["theme"] == "adu"]


def _cmp_val(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    s = str(v).strip()
    if s in ("True", "False"):
        return s == "True"
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        return s[:10]


def compare_with_config(proposed: pd.DataFrame, existing: pd.DataFrame, geoids) -> pd.DataFrame:
    """One row per (place, matched era, field): proposed vs existing, and whether they match.

    Eras are matched by effective year; local rows only (state-law rows `-SL` are compared separately)."""
    out = []
    ex = existing[~existing["reform_id"].str.contains("-SL", regex=False)]
    for g in geoids:
        p = proposed[proposed["jurisdiction_geoid"] == g].copy()
        e = ex[ex["jurisdiction_geoid"] == g].copy()
        p_years = {pd.Timestamp(r["effective_date"]).year: r for _, r in p.iterrows()}
        e_years = {int(str(r["effective_date"])[:4]): r for _, r in e.iterrows()}
        for y in sorted(set(p_years) | set(e_years)):
            pr, er = p_years.get(y), e_years.get(y)
            if pr is None or er is None:
                out.append(
                    dict(
                        geoid=g,
                        year=y,
                        field="era",
                        proposed=None if pr is None else pr["reform_id"],
                        existing=None if er is None else er["reform_id"],
                        match="era missing",
                    )
                )
                continue
            for f in COMPARE_FIELDS:
                pv = pr[f]
                pv = pv.date().isoformat() if isinstance(pv, pd.Timestamp) else pv
                a, b = _cmp_val(pv), _cmp_val(er[f])
                m = (
                    "match"
                    if a == b
                    else ("proposed blank" if a is None else "existing blank" if b is None else "differs")
                )
                out.append(dict(geoid=g, year=y, field=f, proposed=a, existing=b, match=m))
    return pd.DataFrame(out)
