"""Legal lots, step 1: how close each place's coded ADU rule in force is to the Handbook (c, `current_rules`),
from the rubric of protocol §5.4. Part of `scenarios.adu`; the method is in that module's docstring.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.model.scenarios.adu_params import _adu_value

RUBRIC = (
    "by_right",
    "owner_occ",
    "adu_detached_allowed",
    "adu_max_sqft",
    "parking",
    "parking_min_per_unit",
    "adus_per_lot",
)


def _resolved(rows: pd.DataFrame, rid: str) -> dict:
    """A reform's rubric with fields it leaves blank taken from the reform it supersedes (amendments)."""
    by_id = rows.set_index("reform_id")
    out: dict = {}
    while isinstance(rid, str) and rid in by_id.index:
        row = by_id.loc[rid]
        for f in RUBRIC:
            if f not in out and f in row and pd.notna(row[f]):
                out[f] = row[f]
        rid = row.get("supersedes")
    return out


TYPES = ("none", "owner", "other", "both", "handbook")
P_COLS = tuple(f"p_{t}" for t in TYPES)
FIELDS = ("by_right", "owner_occ", "adu_detached_allowed", "adu_max_sqft", "parking")
OWNER = "owner_occ"
LABELS = {
    "by_right": lambda m: "not by right",
    "owner_occ": lambda m: "owner must live on site",
    "adu_detached_allowed": lambda m: "no detached ADUs",
    "adu_max_sqft": lambda m: f"size cap under {m:g} sq ft",
    "parking": lambda m: "parking required",
}


def restriction_fields(rubric: Mapping, min_sqft: float = 600) -> tuple[list[str], list[str]]:
    """(fields whose coded value fails a Handbook condition, fields left blank) for one ADU rule (D-022).

    A blank field is unknown, never "no restriction". Parking is known when `parking_min_per_unit` is coded,
    or the text says "no …" (none required) or names a requirement ("required", "space"); other text, or none,
    is unknown. `min_sqft` is the Handbook minimum (adu.yaml `adu_handbook_min_sqft`).
    """
    failed, unknown = [], []
    checks = {
        "by_right": lambda v: v is False or str(v).lower() == "false",
        "owner_occ": lambda v: v is True or str(v).lower() == "true",
        "adu_detached_allowed": lambda v: v is False or str(v).lower() == "false",
        "adu_max_sqft": lambda v: float(v) < min_sqft,
    }
    for field, fails_if in checks.items():
        if field not in rubric or pd.isna(rubric[field]):
            unknown.append(field)
        elif fails_if(rubric[field]):
            failed.append(field)
    minimum = rubric.get("parking_min_per_unit")
    text = str(rubric.get("parking", "") if pd.notna(rubric.get("parking", None)) else "").strip().lower()
    if minimum is not None and pd.notna(minimum):
        if float(minimum) > 0:
            failed.append("parking")
    elif text.startswith("no"):
        pass
    elif "requir" in text or "space" in text:
        failed.append("parking")
    else:
        unknown.append("parking")
    return failed, unknown


def rule_restrictions(rubric: Mapping, min_sqft: float = 600) -> tuple[list[str], list[str]]:
    """(labels of the Handbook conditions a rule fails, blank fields): `restriction_fields`, labelled."""
    failed, unknown = restriction_fields(rubric, min_sqft)
    return [LABELS[f](min_sqft) for f in failed], unknown


def type_of(failed) -> str:
    """Rule type from the conditions it fails: 'handbook' (none), 'owner' (owner occupancy only), 'other'
    (parking, permit by conditional use, attached only or a cap under 600 sq ft), 'both'."""
    failed = set(failed)
    owner, other = OWNER in failed, bool(failed - {OWNER})
    return "both" if owner and other else "owner" if owner else "other" if other else "handbook"


def type_distribution(failed, unknown, field_probs: Mapping[str, float]) -> np.ndarray:
    """P(rule type) over TYPES when blank fields restrict independently with `field_probs` (D-022).

    By hand: owner occupancy known to fail, parking blank with P = 0.25 -> owner 0.75, both 0.25.
    """
    v = np.zeros(len(TYPES))
    for bits in itertools.product((False, True), repeat=len(unknown)):
        pairs = list(zip(unknown, bits, strict=True))
        prob = float(np.prod([field_probs[f] if b else 1 - field_probs[f] for f, b in pairs]))
        restricted = set(failed) | {f for f, b in pairs if b}
        v[TYPES.index(type_of(restricted))] += prob
    return v


def c_values(params: Mapping[str, float]) -> np.ndarray:
    """c for each type: none 0, owner m_o, other m_x, both m_o × m_x, handbook 1 (graded partial share, D-019
    fit 3): m_o = `adu_owner_occupancy_share`, m_x = `adu_partial_rule_share`."""
    mo, mx = params["adu_owner_occupancy_share"], params["adu_partial_rule_share"]
    return np.array([0.0, mo, mx, mo * mx, 1.0])


def _combine_max(vectors: list[np.ndarray], cvals: np.ndarray) -> np.ndarray:
    """Distribution of the most permissive type (highest c) over independent rules in force together."""
    order = np.argsort(cvals, kind="stable")
    cdf = np.prod([np.cumsum(np.asarray(v)[order]) for v in vectors], axis=0)
    out = np.zeros(len(cvals))
    out[order] = np.diff(np.r_[0.0, cdf])
    return out


def _live(reforms: pd.DataFrame, as_of: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(ADU rows in force on as_of and not superseded by one in force, all in-force ADU rows)."""
    adu = reforms[(reforms["theme"] == "adu") & (reforms["status"] == "in_force")]
    live = adu[(adu["effective_date"] <= as_of) & (adu["end_date"].isna() | (adu["end_date"] > as_of))]
    return live[~live["reform_id"].isin(set(live["supersedes"].dropna()))], adu


def parking_waived(reforms: pd.DataFrame, geoid: str, date: pd.Timestamp) -> bool:
    """True if a citywide 'parking' reform with a zero minimum is in force for `geoid` on `date` (D-022).

    Such a row settles a blank ADU parking field: no parking can be required for an ADU there.
    """
    r = reforms[(reforms["theme"] == "parking") & (reforms["status"] == "in_force")]
    r = r[(r["jurisdiction_geoid"] == geoid) & (r["effective_date"] <= date)]
    r = r[r["end_date"].isna() | (r["end_date"] > date)]
    zero = pd.to_numeric(r.get("parking_min_per_unit"), errors="coerce") == 0
    citywide = r["coverage"].fillna("").str.lower().str.contains("citywide") if "coverage" in r else False
    return bool((zero & citywide).any())


def with_parking(rubric: Mapping, reforms: pd.DataFrame, geoid: str, date: pd.Timestamp) -> dict:
    """The ADU rubric with a blank parking field filled from a citywide zero-minimum parking reform."""
    out = dict(rubric)
    blank = pd.isna(out.get("parking_min_per_unit", np.nan)) and pd.isna(out.get("parking", np.nan))
    if blank and parking_waived(reforms, geoid, date):
        out["parking_min_per_unit"] = 0.0
    return out


def _no_adus(rubric: Mapping) -> bool:
    v = rubric.get("adus_per_lot")
    return v is not None and pd.notna(v) and float(v) == 0


def field_restrict_counts(reforms: pd.DataFrame, as_of: pd.Timestamp, min_sqft: float = 600) -> pd.DataFrame:
    """Per field: how many coded rules in force state it (known) and how many of those restrict (D-022).

    The probability that a blank field restricts is restricting / known among coded rules (by state, with the
    pooled count as fallback: `field_probabilities`). Explicit 'no ADUs' rows are not counted.
    """
    live, adu = _live(reforms, as_of)
    rows = []
    for r in live.itertuples():
        rubric = with_parking(_resolved(adu, r.reform_id), reforms, r.jurisdiction_geoid, as_of)
        if _no_adus(rubric):
            continue
        fails, unknown = rule_restrictions(rubric, min_sqft)
        for f in FIELDS:
            if f not in unknown:
                rows.append({"state": r.state, "field": f, "restricts": LABELS[f](min_sqft) in fails})
    df = pd.DataFrame(rows, columns=["state", "field", "restricts"])
    return df.groupby(["state", "field"])["restricts"].agg(known="count", restricting="sum").reset_index()


def field_probabilities(counts: pd.DataFrame, state: str, min_count: int) -> dict[str, float]:
    """P(blank field restricts) for one state: its own coded share if it has min_count known values,
    else the pooled share over all states (D-022). A field nobody has coded gets
    `adu_blank_field_restrict_prob` (0.5, no information)."""
    blank = _adu_value("adu_blank_field_restrict_prob")
    out = {}
    for f in FIELDS:
        own = counts[(counts["state"] == state) & (counts["field"] == f)]
        pooled = counts[counts["field"] == f]
        use = own if len(own) and own["known"].sum() >= min_count else pooled
        known = use["known"].sum()
        out[f] = float(use["restricting"].sum() / known) if known else blank
    return out


LIMITED_SCOPE = re.compile(
    r"\bonly (inside|within|in)\b|^within\b|\bnew subdivisions?\b|half[- ]mile|1/2 mile", re.IGNORECASE
)


def _norm_zone(z) -> str:
    return re.sub(r"[\s\-_.()]", "", str(z)).upper()


def _zone_keys(z) -> set[str]:
    """A parcel's zoning as codes to compare: normalized as written, and the acronym of a written-out name
    ('Urban Neighborhood 1' -> 'UN1')."""
    text = str(z)
    words = re.findall(r"[A-Za-z]+|\d+", text)
    acronym = "".join(w[0] if w.isalpha() else w for w in words).upper()
    return {_norm_zone(text), acronym}


def rule_coverage(
    rule: Mapping, parcels: pd.DataFrame | None, params: Mapping[str, float]
) -> tuple[float, str]:
    """Share of a place's ADU-eligible parcels a coded ADU rule covers (D-021), and how it was found.

    - zones (`coverage_zones`) and the lot minimum (`min_lot_sqft`) are measured on the place's single-family
      detached parcels (latest roll) among those whose zoning / lot size is known, where at least
      `adu_rule_parcel_known_min_share` (half) of them have it;
      a zone list matching no parcel's zoning (as written or as an acronym) counts as unavailable;
    - otherwise each limit takes `adu_rule_zoned_coverage_share` (judgment);
    - with no zones or lot minimum: 1, unless the coverage text names a limited area explicitly ("only
      inside/within/in", "within …", new subdivisions, a half-mile corridor):
      `adu_rule_limited_coverage_share`.
    By hand: zones R-1 on 3 of 4 parcels; lot minimum 6,000 met by 2 of the 4 (both R-1) -> 2 / 4.
    """
    zones = [z for z in str(rule.get("coverage_zones") or "").split(";") if z.strip() and z != "nan"]
    min_lot = rule.get("min_lot_sqft")
    min_lot = float(min_lot) if min_lot is not None and pd.notna(min_lot) and float(min_lot) > 0 else None
    if not zones and min_lot is None:
        text = str(rule.get("coverage") or "")
        if LIMITED_SCOPE.search(text):
            return float(params["adu_rule_limited_coverage_share"]), "limited area (judgment)"
        return 1.0, "citywide"
    sf = parcels if parcels is not None else pd.DataFrame(columns=["zoning_raw", "lot_sqft"])
    measured = pd.Series(True, index=sf.index)  # parcels on which every measured limit is known
    covered = pd.Series(True, index=sf.index)
    share, notes = 1.0, []
    min_known = _adu_value("adu_rule_parcel_known_min_share")
    if zones:
        zoning = sf["zoning_raw"] if "zoning_raw" in sf else pd.Series(np.nan, index=sf.index)
        wanted = {_norm_zone(z) for z in zones}
        match = zoning.map(lambda z: bool(_zone_keys(z) & wanted) if pd.notna(z) else False)
        if len(sf) and zoning.notna().mean() >= min_known and match.any():
            measured &= zoning.notna()
            covered &= match
            notes.append("zones from parcels")
        else:
            share *= float(params["adu_rule_zoned_coverage_share"])
            notes.append("zones (judgment)")
    if min_lot is not None:
        lot = sf["lot_sqft"] if "lot_sqft" in sf else pd.Series(np.nan, index=sf.index)
        if len(sf) and lot.notna().mean() >= min_known:
            measured &= lot.notna()
            covered &= lot.fillna(0) >= min_lot
            notes.append("lot minimum from parcels")
        else:
            share *= float(params["adu_rule_zoned_coverage_share"])
            notes.append("lot minimum (judgment)")
    if any("from parcels" in n for n in notes) and measured.any():
        share *= float(covered[measured].mean())
    return float(share), "; ".join(notes)


def apply_coverage(vector: np.ndarray, coverage: float) -> np.ndarray:
    """Parcels a rule does not cover have no ADU rule: the uncovered share of each type moves to 'none'."""
    out = coverage * np.asarray(vector, dtype=float)
    out[0] += 1 - coverage
    return out


def _class(p: np.ndarray) -> str:
    if p[0] == 1:
        return "none"
    if p[-1] == 1:
        return "handbook"
    if p[1:4].sum() == 1 and np.count_nonzero(p) == 1:
        return "partial"
    return "uncertain"


def current_rules(
    reforms: pd.DataFrame,
    geoids,
    state_fips: str,
    as_of: pd.Timestamp,
    field_probs: Mapping | None = None,
    coverage: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Per jurisdiction: P(current ADU rule type) over TYPES, the rule, its date and a note (D-021, D-022).

    - **No ADU row** (local or statewide): `rule_class` 'unknown', p_* missing (filled by `apply_priors`).
    - **A coded row:** known failed conditions fix part of the type; each blank field restricts with
      `field_probs[field]` (default `adu_blank_field_restrict_prob`), independently (`type_distribution`).
    - **Explicit 'no ADUs' row** (`adus_per_lot` = 0, #164): 'none'.
    - **Coverage** (D-021): `coverage[reform_id]` (else judged from the rule's text) moves the uncovered share
      of eligible lots to 'none'.
    Several rows in force (local and state law): the most permissive type (highest c at central values)
    counts. `rule_class` describes the rules' own conditions, before coverage: 'none', 'partial', 'handbook',
    'uncertain' (blank fields) or 'unknown'; the p_* include coverage; `p_partial` = owner + other + both.
    """
    live, adu = _live(reforms, as_of)
    scheduled = adu[adu["effective_date"] > as_of]
    central = {k: v.value for k, v in load_params("adu").items()}
    min_sqft = central["adu_handbook_min_sqft"]
    cvals = c_values(central)
    fp = {f: central["adu_blank_field_restrict_prob"] for f in FIELDS} | dict(field_probs or {})

    def assess(geoid: str) -> dict:
        rows = live[live["jurisdiction_geoid"].isin([geoid, state_fips])]
        if rows.empty:
            out = {
                "rule_class": "unknown",
                "rule_id": None,
                "effective": pd.NaT,
                "note": "no ADU rule coded",
                "unknown_fields": "",
                "coverage": np.nan,
            }
            out |= {c: np.nan for c in P_COLS}
        else:
            vectors, raw, best = [], [], None
            for _, row in rows.iterrows():
                rubric = with_parking(_resolved(adu, row["reform_id"]), reforms, geoid, as_of)
                cov = 1.0
                if _no_adus(rubric):
                    v, note, unknown = np.eye(len(TYPES))[0], f"no ADUs allowed ({row['reform_id']})", []
                    v_raw = v
                else:
                    failed, unknown = restriction_fields(rubric, min_sqft)
                    v = type_distribution(failed, unknown, fp)
                    v_raw = v.copy()
                    labels = [LABELS[f](min_sqft) for f in failed]
                    note = ("partial: " + "; ".join(labels)) if failed else "Handbook-equivalent"
                    if unknown:
                        note += " (not coded: " + ", ".join(unknown) + ")"
                    cov = (coverage or {}).get(row["reform_id"])
                    if cov is None:
                        cov = rule_coverage(row, None, central)[0]
                    if cov < 1:
                        v = apply_coverage(v, cov)
                        note += f"; covers {cov:.0%} of eligible lots"
                raw.append(v_raw)
                vectors.append(v)
                rank = float(v @ cvals)
                if best is None or rank > best[0]:
                    best = (rank, row, unknown, note, cov)
            p = _combine_max(vectors, cvals)
            _, row, unknown, note, cov = best
            cls = _class(_combine_max(raw, cvals))  # the rules' own conditions; coverage is reported apart
            out = {
                "rule_class": cls,
                "rule_id": row["reform_id"],
                "effective": pd.NaT if cls == "none" else row["effective_date"],
                "note": note,
                "unknown_fields": ";".join(unknown),
                "coverage": cov,
            }
            out |= dict(zip(P_COLS, p, strict=True))
        later = scheduled[scheduled["jurisdiction_geoid"].isin([geoid, state_fips])]["reform_id"].tolist()
        if later:
            out["note"] += "; scheduled after the rules date: " + ", ".join(later)
        return out

    cols = ["geoid", "rule_class", "rule_id", "effective", "note", "unknown_fields", "coverage", *P_COLS]
    out = pd.DataFrame([{"geoid": g, **assess(g)} for g in geoids], columns=cols)
    out["effective"] = pd.to_datetime(out["effective"])
    out = out.rename(columns={"effective": "rule_effective", "note": "rule_note"})
    out["p_partial"] = out[["p_owner", "p_other", "p_both"]].sum(axis=1, min_count=1)
    age = (as_of - out["rule_effective"]).dt.days / 365.25
    return out.assign(rule_age=age.where(out["rule_class"] != "none"))
