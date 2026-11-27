"""Reconciled findings -> `reforms` rows (theme `missing_middle`), validated against `lotline.schemas`.

Conventions match the hand-built rows in `config/reforms/<st>.csv`:

- `reform_id` = `<ST>-<geoid>-missing_middle-<effective year>`, with `-b`, `-c` ... when a place has two
  rules taking effect in the same year.
- `source_url`: every distinct evidence URL, ";"-separated, in evidence order (the first is the main one).
  `source_section` / `source_quote`: from the evidence for `unit_cap` (else the first evidence entry).
- `coding_notes`: the date-basis tags first (`[predates]`, `[earliest-known]`, `DATE UNCONFIRMED`,
  `[standards]`), then the coder's notes, then a "Sources:" list giving every evidence entry as
  `field: "quote" (url, section, retrieved date)`. So nothing the coder cited is lost in the 300-character
  `source_quote`.
- `supersedes`: the reform_id of the same place's rule effective on `supersedes_effective`.
- `verified_by` / `verified_date`: the verifier agent and date, set only when every quote was re-found in its
  snapshot.

The output is a candidate table for Ben to merge into `config/reforms/<st>.csv`; agents never write config.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

import pandas as pd

from lotline import schemas
from lotline.rule_agents.common.dates import tags_for
from lotline.rule_agents.mm import THEME
from lotline.rule_agents.mm.findings import PlaceFinding, RuleFinding


def _ids(f: PlaceFinding) -> list[str]:
    count: dict[int, int] = defaultdict(int)
    out = []
    for r in f.rules:
        y = r.effective_date.year
        suffix = "" if count[y] == 0 else "-" + "bcdefgh"[count[y] - 1]
        count[y] += 1
        out.append(f"{f.state}-{f.jurisdiction_geoid}-{THEME}-{y}{suffix}")
    return out


def _sources(r: RuleFinding) -> str:
    """Every evidence entry, one per distinct (quote, url, section), with the fields it backs."""
    groups: dict[tuple, list[str]] = {}
    for e in r.evidence:
        groups.setdefault((e.quote, e.url, e.section or "", e.retrieved.isoformat()), []).append(e.field)
    parts = []
    for (quote, url, section, when), fields in groups.items():
        bits = ", ".join(x for x in (url, section, when) if x)
        parts.append(f'{", ".join(fields)}: "{quote}" ({bits})')
    return "Sources: " + " | ".join(parts)


def rule_row(
    f: PlaceFinding,
    r: RuleFinding,
    reform_id: str,
    *,
    supersedes: str | None,
    coder_2: str | None,
    agreement: str,
    verified_by: str | None = None,
    verified_date: date | None = None,
    adjudication: str = "",
) -> dict:
    main = next((e for e in r.evidence if e.field == "unit_cap"), r.evidence[0] if r.evidence else None)
    urls = list(dict.fromkeys(e.url for e in r.evidence))
    notes = " ".join(tags_for(r.date_basis, standards_only=r.standards_only))
    prior = f"Prior cap (code just before): {r.prior_cap}." if r.prior_cap else ""
    mirror = any(e.source_kind == "mirror" for e in r.evidence if e.field == "unit_cap") and not any(
        e.source_kind not in ("mirror", None) for e in r.evidence if e.field == "unit_cap"
    )
    flag = "FLAG for second coder: unit_cap read on a mirror only." if mirror else ""
    conf = f"Confidence: {r.confidence}."
    for part in (r.notes, prior, flag, conf, adjudication and f"Reconciled: {adjudication}", _sources(r)):
        if part:
            notes = f"{notes} {part}".strip()
    return {
        "reform_id": reform_id,
        "state": f.state,
        "jurisdiction_geoid": f.jurisdiction_geoid,
        "theme": THEME,
        "component": r.component,
        "status": r.status,
        "announced_date": r.announced_date,
        "adoption_date": r.adoption_date,
        "effective_date": r.effective_date,
        "end_date": r.end_date,
        "supersedes": supersedes,
        "by_right": r.by_right,
        "owner_occ": r.owner_occ,
        "unit_cap": r.unit_cap,
        "far_cap": r.far_cap,
        "max_stories": r.max_stories,
        "min_lot_sqft": r.min_lot_sqft,
        "lot_split": r.lot_split,
        "parking": r.parking,
        "parking_min_per_unit": r.parking_min_per_unit,
        "coverage": r.coverage,
        "coverage_zones": ";".join(r.coverage_zones) or None,
        "source_url": ";".join(urls),
        "source_section": main.section if main else None,
        "source_quote": main.quote if main else None,
        "verified_by": verified_by,
        "verified_date": verified_date,
        "coder": f.coder,
        "coder_2": coder_2,
        "coder_agreement": agreement,
        "coding_notes": notes,
    }


def place_rows(
    f: PlaceFinding,
    *,
    coder_2: str | None,
    agreement: str,
    verified_by: str | None = None,
    verified_date: date | None = None,
    adjudication: str = "",
) -> list[dict]:
    """All rows for one reconciled finding (rules ordered by effective date)."""
    f = f.model_copy(update={"rules": sorted(f.rules, key=lambda r: r.effective_date)})
    ids = _ids(f)
    by_eff = {r.effective_date: i for i, r in zip(ids, f.rules, strict=True)}
    return [
        rule_row(
            f,
            r,
            rid,
            supersedes=by_eff.get(r.supersedes_effective) if r.supersedes_effective else None,
            coder_2=coder_2,
            agreement=agreement,
            verified_by=verified_by,
            verified_date=verified_date,
            adjudication=adjudication,
        )
        for rid, r in zip(ids, f.rules, strict=True)
    ]


def table(rows: list[dict]) -> pd.DataFrame:
    """Rows -> a `reforms` DataFrame in canonical column order, coerced and validated (raises
    pandera SchemaErrors listing every failure)."""
    cols = schemas.columns("reforms")
    df = pd.DataFrame(rows, columns=cols)
    for c in ("announced_date", "adoption_date", "effective_date", "end_date", "verified_date"):
        df[c] = pd.to_datetime(df[c])
    for c in ("by_right", "owner_occ", "lot_split", "adu_detached_allowed"):
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
    obj = [c for c in cols if df[c].dtype == object]
    df[obj] = df[obj].astype(object).where(df[obj].notna(), None)
    return schemas.validate(df, "reforms")


def write_csv(df: pd.DataFrame, path) -> None:
    """CSV in the same layout as config/reforms/<st>.csv (dates as YYYY-MM-DD)."""
    out = df.copy()
    for c in ("announced_date", "adoption_date", "effective_date", "end_date", "verified_date"):
        out[c] = out[c].dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False)
