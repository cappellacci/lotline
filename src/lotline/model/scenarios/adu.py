"""Handbook ADU scenario: one ADU allowed on every eligible single-family parcel, at least 600 sq ft, by
right,
with no parking requirement (Handbook benchmark; BUILD_PLAN §5; judging finding MS-01).

For each jurisdiction and each of the five years after the origin, t = 1 … 5:

    current rules   h_cur(t) = max(c × h_m × ramp(a + t), observed ADU rate)
    Handbook rules  h_hb(t)  = max(c × h_m × ramp(a + t) + (1 − c) × h_m × ramp(t), observed ADU rate)

- **h_m**, the place's mature ADU hazard (`model.hazard.adu_mature_hazard`), with each simulation draw widened
  where the place lies outside the calibration range (`hazard.widen`).
- **c, how close current local rules already are to the Handbook** (`current_rules`): 1 when the coded ADU
  rule in force at the origin allows a detached ADU of 600+ sq ft by right with no owner-occupancy or parking
  requirement; `adu_partial_rule_share` when ADUs are allowed with any of those restrictions; 0 when no ADU
  rule is coded. a = years since that rule took effect, so a recent reform is still ramping up under current
  rules. Unknown (uncoded) rubric fields count as not restrictive and are listed, so a coding gap never
  creates a Handbook gain.
- **Observed ADU rate**: where local permits flag ADUs, ADU permits per eligible parcel per year over
  `adu_observed_first_year`–`adu_observed_last_year`. It is a floor on the current-rules hazard: ADUs a place
  already builds are in its baseline and are never counted as added (additionality, MS-10).

Each year the pool of parcels without an ADU shrinks, separately under each set of rules:
gross ADUs(t) = R(t − 1) × h(t), R(t) = R(t − 1) − gross ADUs(t), R(0) = eligible parcels. So a parcel gets at
most one ADU, and cumulative ADUs never exceed eligible parcels.

    ADU permits added (t) = Handbook gross ADUs(t) − current-rules gross ADUs(t)
    additional homes (t)  = ADU permits added (t) × adu_net_new_share × (1 − adu_formalization_share)

Every result is a range: P10/P50/P90 and the mean over `adu_simulation_draws` draws of every uncertain
parameter (pro forma, hazard, net-new and formalization shares, partial-rule share). Numerator (units) and
denominator (eligible parcels) stay in separate columns. Nothing is fitted here: the hazard's anchor comes
from
the evidence band (D-018) and observed local ADUs enter only as the additionality floor.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lotline.config import CONFIG_DIR, load_params
from lotline.model import hazard, proforma

PARAM_FILES = ("proforma", "hazard", "adu", "market")
AGGREGATE_KEYS = ("adu_net_new_share", "adu_formalization_share")
FIXED = proforma.NOT_SAMPLED | {"adu_simulation_draws", "adu_simulation_seed"}
RUBRIC = (
    "by_right",
    "owner_occ",
    "adu_detached_allowed",
    "adu_max_sqft",
    "parking",
    "parking_min_per_unit",
    "adus_per_lot",
)


def specs() -> dict:
    """Every parameter the scenario uses: pro forma, hazard, adu.yaml and the two ADU shares in
    aggregate.yaml."""
    out = {}
    for name in PARAM_FILES:
        out |= load_params(name)
    agg = load_params("aggregate")
    return out | {k: agg[k] for k in AGGREGATE_KEYS}


def central_params() -> dict[str, float]:
    return {k: s.value for k, s in specs().items()}


def draw_params(n: int, seed: int) -> list[dict[str, float]]:
    """n parameter sets: each uncertain parameter triangular(low, central, high); fixed ones held."""
    rng = np.random.default_rng(seed)
    cols = {
        k: np.full(n, s.value) if k in FIXED or s.low == s.high else rng.triangular(s.low, s.value, s.high, n)
        for k, s in specs().items()
    }
    return [{k: float(v[i]) for k, v in cols.items()} for i in range(n)]


# ---------------------------------------------------------------------------------------------------------
# Current local rules (config/reforms/<st>.csv, rubric of protocol §5.4)
# ---------------------------------------------------------------------------------------------------------


def load_reforms(state: str) -> pd.DataFrame:
    """The state's coded reforms (config/reforms/<st>.csv) with dates parsed."""
    df = pd.read_csv(CONFIG_DIR / "reforms" / f"{state.lower()}.csv", dtype={"jurisdiction_geoid": str})
    for col in ("announced_date", "adoption_date", "effective_date", "end_date"):
        if col in df:
            df[col] = pd.to_datetime(df[col])
    return df


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
    else the pooled share over all states (D-022). A field nobody has coded gets 0.5 (no information)."""
    out = {}
    for f in FIELDS:
        own = counts[(counts["state"] == state) & (counts["field"] == f)]
        pooled = counts[counts["field"] == f]
        use = own if len(own) and own["known"].sum() >= min_count else pooled
        known = use["known"].sum()
        out[f] = float(use["restricting"].sum() / known) if known else 0.5
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
      detached parcels (latest roll) among those whose zoning / lot size is known, where at least half of them
      have it; a zone list matching no parcel's zoning (as written or as an acronym) counts as unavailable;
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
    if zones:
        zoning = sf["zoning_raw"] if "zoning_raw" in sf else pd.Series(np.nan, index=sf.index)
        wanted = {_norm_zone(z) for z in zones}
        match = zoning.map(lambda z: bool(_zone_keys(z) & wanted) if pd.notna(z) else False)
        if len(sf) and zoning.notna().mean() >= 0.5 and match.any():
            measured &= zoning.notna()
            covered &= match
            notes.append("zones from parcels")
        else:
            share *= float(params["adu_rule_zoned_coverage_share"])
            notes.append("zones (judgment)")
    if min_lot is not None:
        lot = sf["lot_sqft"] if "lot_sqft" in sf else pd.Series(np.nan, index=sf.index)
        if len(sf) and lot.notna().mean() >= 0.5:
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
      `field_probs[field]` (default 0.5), independently (`type_distribution`).
    - **Explicit 'no ADUs' row** (`adus_per_lot` = 0, #164): 'none'.
    - **Coverage** (D-021): `coverage[reform_id]` (else judged from the rule's text) moves the uncovered share
      of eligible lots to 'none'.
    Several rows in force (local and state law): the most permissive type (highest c at central values)
    counts. `rule_class` is 'none', 'partial', 'handbook', 'uncertain' (mixed) or 'unknown'; `p_partial` is
    the owner + other + both share.
    """
    live, adu = _live(reforms, as_of)
    scheduled = adu[adu["effective_date"] > as_of]
    central = {k: v.value for k, v in load_params("adu").items()}
    min_sqft = central["adu_handbook_min_sqft"]
    cvals = c_values(central)
    fp = {f: 0.5 for f in FIELDS} | dict(field_probs or {})

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
            vectors, best = [], None
            for _, row in rows.iterrows():
                rubric = with_parking(_resolved(adu, row["reform_id"]), reforms, geoid, as_of)
                cov = 1.0
                if _no_adus(rubric):
                    v, note, unknown = np.eye(len(TYPES))[0], f"no ADUs allowed ({row['reform_id']})", []
                else:
                    failed, unknown = restriction_fields(rubric, min_sqft)
                    v = type_distribution(failed, unknown, fp)
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
                vectors.append(v)
                rank = float(v @ cvals)
                if best is None or rank > best[0]:
                    best = (rank, row, unknown, note, cov)
            p = _combine_max(vectors, cvals)
            _, row, unknown, note, cov = best
            cls = _class(p)
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
            out["note"] += "; scheduled after origin: " + ", ".join(later)
        return out

    cols = ["geoid", "rule_class", "rule_id", "effective", "note", "unknown_fields", "coverage", *P_COLS]
    out = pd.DataFrame([{"geoid": g, **assess(g)} for g in geoids], columns=cols)
    out["effective"] = pd.to_datetime(out["effective"])
    out = out.rename(columns={"effective": "rule_effective", "note": "rule_note"})
    out["p_partial"] = out[["p_owner", "p_other", "p_both"]].sum(axis=1, min_count=1)
    age = (as_of - out["rule_effective"]).dt.days / 365.25
    return out.assign(rule_age=age.where(out["rule_class"] != "none"))


def size_band(population, edges) -> np.ndarray:
    """Place-size band 0, 1, 2 … from 2020 population and band edges (e.g. 10,000 and 50,000)."""
    return np.searchsorted(np.asarray(edges, dtype=float), np.asarray(population, dtype=float), side="right")


def rule_priors(coded: pd.DataFrame, edges, min_count: int) -> pd.DataFrame:
    """Type probabilities for places with no ADU row, from the coded places themselves (D-022).

    `coded`: state, population and p_* (over TYPES) for every place with a coded rule (fractional where blanks
    or coverage leave the type uncertain). For each state and size band: the mean of the coded places'
    probabilities if at least `min_count` places are coded there; else the state's pooled mean; else the mean
    over every state. Returns state, band, n_coded, source and p_* (and p_partial).
    By hand: 5 coded places in a band, 2 'other' and 3 Handbook-equivalent -> p_other 0.4, p_handbook 0.6.
    """
    c = coded.assign(band=size_band(coded["population"], edges))
    rows = []
    for state in sorted(c["state"].unique()):
        for band in range(len(edges) + 1):
            own = c[(c["state"] == state) & (c["band"] == band)]
            whole = c[c["state"] == state]
            if len(own) >= min_count:
                use, src = own, "state and band"
            elif len(whole) >= min_count:
                use, src = whole, "state, all bands"
            else:
                use, src = c, "all states"
            rows.append(
                {
                    "state": state,
                    "band": band,
                    "n_coded": len(own),
                    "source": src,
                    **use[list(P_COLS)].mean().to_dict(),
                }
            )
    out = pd.DataFrame(rows)
    return out.assign(p_partial=out[["p_owner", "p_other", "p_both"]].sum(axis=1))


def apply_priors(places: pd.DataFrame, priors: pd.DataFrame, edges) -> pd.DataFrame:
    """Fill p_* for 'unknown' places from `rule_priors` by state and size band; adds `prior_source`."""
    out = places.assign(band=size_band(places["population"].fillna(0), edges))
    pr = priors.set_index(["state", "band"])
    pooled = priors[list(P_COLS)].mean()
    src = pd.Series("coded", index=out.index, dtype=object)
    for i in out.index[out["rule_class"] == "unknown"]:
        key = (out.at[i, "state"], out.at[i, "band"])
        row = pr.loc[key] if key in pr.index else None
        for col in P_COLS:
            out.at[i, col] = row[col] if row is not None else pooled[col]
        src[i] = row["source"] if row is not None else "all states"
    out["p_partial"] = out[["p_owner", "p_other", "p_both"]].sum(axis=1)
    return out.assign(prior_source=src)


def type_probs(places: pd.DataFrame) -> np.ndarray:
    """(places × TYPES) probabilities. Tables from before D-022 with only p_none/p_partial/p_handbook (or only
    `rule_class`) read 'partial' as 'other'."""
    if all(c in places for c in P_COLS) and places[list(P_COLS)].notna().all(axis=None):
        return places[list(P_COLS)].to_numpy(dtype=float)
    cls = places["rule_class"]
    get = lambda col, fallback: places[col] if col in places else fallback  # noqa: E731
    none = get("p_none", (cls == "none").astype(float)).fillna((cls == "none").astype(float))
    part = get("p_partial", (cls == "partial").astype(float)).fillna((cls == "partial").astype(float))
    hb = get("p_handbook", (cls == "handbook").astype(float)).fillna((cls == "handbook").astype(float))
    zero = np.zeros(len(places))
    return np.column_stack([none, zero, part, zero, hb]).astype(float)


def expected_rule_share(places: pd.DataFrame, params: Mapping[str, float]) -> np.ndarray:
    """E[c] = Σ P(type) × c(type): the central-path value of c (D-022)."""
    return type_probs(places) @ c_values(params)


def draw_rule_share(places: pd.DataFrame, params: Mapping[str, float], rng: np.random.Generator):
    """One draw of each place's rule type -> (c, drawn type index, sampled mask)."""
    p = type_probs(places)
    u = rng.random(len(p))[:, None]
    idx = (u > np.cumsum(p, axis=1)).sum(axis=1).clip(max=len(TYPES) - 1)
    return c_values(params)[idx], idx, p.max(axis=1) < 1


def rule_share(rule_class: pd.Series, partial_share: float) -> np.ndarray:
    """c for a known class (before D-022): 0 none, `partial_share` partial, 1 Handbook-equivalent."""
    return rule_class.map({"none": 0.0, "partial": partial_share, "handbook": 1.0}).to_numpy(dtype=float)


# ---------------------------------------------------------------------------------------------------------
# Observed ADUs (additionality)
# ---------------------------------------------------------------------------------------------------------


def _is_adu(permits: pd.DataFrame) -> pd.Series:
    return (permits["building_type_std"] == "ADU") | permits["adu_type"].notna()


def adu_share_of_one_unit(permits: pd.DataFrame, first: int, last: int) -> tuple[int, int]:
    """(ADU permits, ADU + detached single-family permits) issued in [first, last]."""
    w = permits[(permits["issue_year"] >= first) & (permits["issue_year"] <= last)]
    adu = int(_is_adu(w).sum())
    return adu, adu + int((w["building_type_std"] == "SFD").sum())


def observed_adu_counts(permits: pd.DataFrame, first: int, last: int) -> pd.DataFrame:
    """ADU permits per jurisdiction and year in [first, last], from sources that flag ADUs at all.

    Where two sources cover one jurisdiction (Met Council and Minneapolis's own permits), the larger count
    each year is kept, never the sum. Jurisdictions in a flagging source with no ADU get 0, not missing.
    """
    flagging = permits.loc[_is_adu(permits), "source"].unique()
    p = permits[permits["source"].isin(flagging) & permits["jurisdiction_geoid"].notna()]
    p = p[(p["issue_year"] >= first) & (p["issue_year"] <= last)].assign(adu=_is_adu)
    by = p.groupby(["jurisdiction_geoid", "source", "issue_year"])["adu"].sum().reset_index()
    out = by.groupby(["jurisdiction_geoid", "issue_year"])["adu"].max().reset_index()
    return out.rename(columns={"jurisdiction_geoid": "geoid", "issue_year": "year", "adu": "adu_permits"})


# ---------------------------------------------------------------------------------------------------------
# The scenario
# ---------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Paths:
    """Gross ADU permits per place (rows) and year (columns) under each set of rules, for one parameter
    set."""

    handbook: np.ndarray
    current: np.ndarray

    @property
    def added(self) -> np.ndarray:
        return self.handbook - self.current


def pool_paths(
    eligible, h_mature, h_floor, rule_share, rule_age, ramp_half, ramp_slope, horizon, enabled=True
):
    """Gross ADUs per year under current and Handbook rules, depleting the pool of parcels without an ADU.

    `rule_age` is the current rule's age in years at the origin (NaN: no rule). With `enabled=False` the
    Handbook path equals the current-rules path, so nothing is added.
    """
    e = np.asarray(eligible, dtype=float)
    hm = np.asarray(h_mature, dtype=float)
    floor = np.nan_to_num(np.asarray(h_floor, dtype=float), nan=0.0)
    c = np.asarray(rule_share, dtype=float)
    age = np.nan_to_num(np.asarray(rule_age, dtype=float), nan=0.0)
    r_hb, r_cur = e.copy(), e.copy()
    hb, cur = np.zeros((len(e), horizon)), np.zeros((len(e), horizon))
    for i, t in enumerate(range(1, horizon + 1)):
        h_rule = c * hm * hazard.ramp(age + t, ramp_half, ramp_slope)
        h_cur = np.minimum(np.maximum(h_rule, floor), 1.0)
        if enabled:
            h_new = h_rule + (1.0 - c) * hm * hazard.ramp(t, ramp_half, ramp_slope)
            h_hb = np.minimum(np.maximum(h_new, floor), 1.0)
        else:
            h_hb = h_cur
        hb[:, i], cur[:, i] = r_hb * h_hb, r_cur * h_cur
        r_hb, r_cur = r_hb - hb[:, i], r_cur - cur[:, i]
    return Paths(hb, cur)


def with_rule_probs(places: pd.DataFrame, params: Mapping[str, float]) -> pd.DataFrame:
    """Type probabilities for every place (`type_probs`), and a rule age of `adu_unknown_rule_age_years` where
    the type is drawn and no rule date is known (D-022)."""
    out = places.copy()
    probs = type_probs(out)
    for k, col in enumerate(P_COLS):
        out[col] = probs[:, k]
    out["p_partial"] = probs[:, 1:4].sum(axis=1)
    sampled = probs.max(axis=1) < 1
    age = out["rule_age"] if "rule_age" in out else pd.Series(np.nan, index=out.index)
    out["rule_age"] = age.where(~(sampled & age.isna()), params["adu_unknown_rule_age_years"])
    return out


def central_path(
    places: pd.DataFrame, horizon: int | None = None, enabled: bool = True, params: dict | None = None
) -> dict[str, np.ndarray]:
    """The scenario at central parameter values, no widening: arrays (places × years) for each outcome.

    For hand checks and the worked example; `run` gives the ranges. `params` overrides central values.
    """
    p = central_params() | (params or {})
    places = with_rule_probs(places, p)
    horizon = horizon or int(load_params("baseline")["forecast_horizon_years"].value)
    given = places["mortgage_rate"] if "mortgage_rate" in places else pd.Series(np.nan, index=places.index)
    rate = given.fillna(p["mortgage_rate_forecast"]).to_numpy(dtype=float)
    hm = hazard.adu_mature_hazard(places["rent"], places["home_value"], rate, p)
    c = expected_rule_share(places, p)  # E[c] over the rule types (D-022)
    paths = pool_paths(
        places["eligible_parcels"],
        hm,
        places["observed_rate"],
        c,
        places["rule_age"],
        p["adu_ramp_half_years"],
        p["adu_ramp_slope_years"],
        horizon,
        enabled,
    )
    homes = paths.added * p["adu_net_new_share"] * (1 - p["adu_formalization_share"])
    return {
        "mature_hazard": hm,
        "handbook": paths.handbook,
        "current": paths.current,
        "added": paths.added,
        "homes": homes,
    }


def run(
    places: pd.DataFrame, origin: int, *, draws: int | None = None, enabled: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The scenario for every place: (per-year table, five-year totals), each with P10/P50/P90 and mean.

    `places` columns: geoid, eligible_parcels, rent (median gross rent, 2025 dollars), home_value (2025
    dollars), optional mortgage_rate (a backtest passes the year's actual rate; where it is missing, each draw
    uses `mortgage_rate_forecast` from market.yaml, flat over the horizon), rule_class ('none', 'partial',
    'handbook'), rule_age (years, NaN without a rule), observed_rate (ADU permits per parcel a year; NaN
    where not observed). Extra columns are carried through.
    Totals are percentiles of each draw's five-year sum, not sums of percentiles.
    """
    central = central_params()
    places = with_rule_probs(places, central)
    n = int(draws or central["adu_simulation_draws"])
    seed = int(central["adu_simulation_seed"])
    sets = draw_params(n, seed)
    rule_rng = np.random.default_rng(seed + 2)
    drawn = np.zeros((n, len(places)))
    horizon = int(load_params("baseline")["forecast_horizon_years"].value)
    z = np.random.default_rng(seed + 1).standard_normal((n, len(places)))
    e = places["eligible_parcels"].to_numpy(dtype=float)
    keys = {
        "handbook": "handbook_adus",
        "current": "current_rules_adus",
        "added": "adu_permits_added",
        "homes": "additional_homes",
    }
    out = {k: np.zeros((n, len(places), horizon)) for k in keys}
    given = places["mortgage_rate"] if "mortgage_rate" in places else pd.Series(np.nan, index=places.index)

    def rates(
        p,
    ):  # a forward run draws the rate path (market.yaml); a backtest passes each year's actual rate
        return given.fillna(p["mortgage_rate_forecast"]).to_numpy(dtype=float)

    for d, p in enumerate(sets):
        args = (places["rent"], places["home_value"], rates(p))
        hm = hazard.adu_mature_hazard(*args, p)
        hm = hazard.widen(hm, hazard.calibration_distance(*args, p)["total"], z[d], p)
        c, idx, sampled = draw_rule_share(places, p, rule_rng)
        drawn[d] = idx
        paths = pool_paths(
            e,
            hm,
            places["observed_rate"],
            c,
            places["rule_age"],
            p["adu_ramp_half_years"],
            p["adu_ramp_slope_years"],
            horizon,
            enabled,
        )
        out["handbook"][d], out["current"][d], out["added"][d] = paths.handbook, paths.current, paths.added
        out["homes"][d] = paths.added * p["adu_net_new_share"] * (1 - p["adu_formalization_share"])

    args = (places["rent"], places["home_value"], rates(central))
    dist = hazard.calibration_distance(*args, central)
    info = places.assign(
        mortgage_rate_central=args[2],
        mature_hazard_central=hazard.adu_mature_hazard(*args, central),
        price_to_cost_central=hazard.adu_price_to_cost(places["rent"], params=central),
        calibration_distance=dist["total"],
        outside_calibration=dist["total"] > 0,
        draws_from_unknown_rule=np.where(sampled, 1.0, 0.0) if n else 0.0,
        drawn_none=(drawn == 0).mean(axis=0),
        drawn_partial=((drawn >= 1) & (drawn <= 3)).mean(axis=0),
        drawn_handbook=(drawn == 4).mean(axis=0),
    ).reset_index(drop=True)
    yearly = info.loc[info.index.repeat(horizon)].reset_index(drop=True)
    yearly["horizon"] = np.tile(np.arange(1, horizon + 1), len(places))
    yearly["year"] = origin + yearly["horizon"]
    totals = info.copy()
    for key, name in keys.items():
        for table, a in ((yearly, out[key].reshape(n, -1)), (totals, out[key].sum(axis=2))):
            table[f"{name}_mean"] = a.mean(axis=0)
            for q in (10, 50, 90):
                table[f"{name}_p{q}"] = np.percentile(a, q, axis=0)
    return yearly, totals


# ---------------------------------------------------------------------------------------------------------
# Inputs from a state's processed tables
# ---------------------------------------------------------------------------------------------------------

ACS_PREFIX = {"place": "place", "township": "cousub", "county_unincorporated": "county"}
ACS_VARS = {"rent": "B25064_001", "home_value": "B25077_001"}


def acs_values(acs: pd.DataFrame, geos: pd.Series, year: int, cpi: pd.Series) -> pd.DataFrame:
    """Median gross rent and home value per ACS geo from the newest 5-year vintage ending <= year, 2025
    dollars."""
    from lotline.model import money

    a = acs[acs["variable"].isin(ACS_VARS.values()) & acs["geo"].isin(geos) & (acs["end_year"] <= year)]
    a = a[a["estimate"].notna()].sort_values("end_year").groupby(["geo", "variable"]).last().reset_index()
    to_year = money.base_year()
    a["real"] = money.deflate(a["estimate"], a["end_year"], cpi, to_year).astype(float).to_numpy()
    wide = a.pivot(index="geo", columns="variable", values="real").rename(
        columns={v: k for k, v in ACS_VARS.items()}
    )
    vintage = a.groupby("geo")["end_year"].max().rename("acs_end_year")
    return wide.join(vintage)


def non_overlapping(places: pd.DataFrame, jurisdictions: pd.DataFrame, county_shares: pd.DataFrame):
    """Make scenario units that never share a parcel (D-020).

    County remainders ("rest of county") keep the homes of local-only places and townships (`in_bps` False:
    BPS files their permits in the county row), so a scenario that models both counts those parcels twice.
    This happens only where the remainder's denominator is the ACS fallback (`eligible.allocate_homes`); a
    remainder counted from a parcel roll never overlaps, since every parcel belongs to one jurisdiction.
    Each local-only place stays its own unit (it carries its own rules); its eligible parcels are subtracted
    from the ACS-fallback remainder of every county it sits in, by `county_shares` (place_geoid,
    county_geoid, share; a place without shares sits wholly in its `county_geoid`). Negative results are set
    to 0 and flagged.

    Adds `eligible_parcels_reported` (before) and `overlap_removed`; `eligible_parcels` becomes the
    non-overlapping count. By hand: county C remainder 1,000 and D remainder 500; local-only L has 300
    parcels, two thirds in C -> C 800, D 400, L 300; total 1,500 instead of 1,800.
    """
    out = places.copy()
    out["eligible_parcels_reported"] = out["eligible_parcels"].astype(float)
    j = jurisdictions.set_index("geoid")
    in_bps = j["in_bps"].astype("boolean").fillna(True).astype(bool)
    local_only = [g for g in out["geoid"] if g in j.index and not in_bps[g]]
    # Only ACS-fallback remainders overlap: `eligible.allocate_homes` keeps local-only homes in them. A
    # remainder counted from a parcel roll holds only parcels assigned to the county row, never a place's.
    source = out["denominator_source"] if "denominator_source" in out else pd.Series("acs", index=out.index)
    remainder = {
        r.county_geoid: i
        for i, r in out.iterrows()
        if r.get("kind") == "county_unincorporated" and source[i] != "parcels"
    }
    removed = pd.Series(0.0, index=out.index)
    parcels = out.set_index("geoid")["eligible_parcels_reported"]
    for g in local_only:
        shares = county_shares[county_shares["place_geoid"] == g]
        if shares.empty:
            shares = pd.DataFrame({"county_geoid": [j.at[g, "county_geoid"]], "share": [1.0]})
        for c, sh in zip(shares["county_geoid"], shares["share"], strict=True):
            if c in remainder:
                removed[remainder[c]] += float(parcels[g]) * float(sh)
    net = out["eligible_parcels_reported"] - removed
    out["overlap_clipped"] = net < 0
    out["eligible_parcels"] = net.clip(lower=0.0)
    out["overlap_removed"] = out["eligible_parcels_reported"] - out["eligible_parcels"]
    return out


def _county_shares(state: str, store, places: pd.DataFrame) -> pd.DataFrame:
    """Census 2020 county shares of the local-only places (cached Census files via the IO layer)."""
    from lotline.adapters.national import geoparts
    from lotline.config import load_state

    local = places.loc[~places["in_bps"].fillna(True).astype(bool) & (places["kind"] == "place"), "geoid"]
    if local.empty:
        return pd.DataFrame(columns=["place_geoid", "county_geoid", "share"])
    return geoparts.county_shares(load_state(state).fips, sorted(local), store)


REFORM_STATES = ("MN", "NC", "OH", "TX")


_PARCEL_CACHE: dict[str, pd.DataFrame] = {}


def _sf_parcels(state: str, store) -> pd.DataFrame:
    """Single-family detached parcels of each jurisdiction's latest roll (zoning and lot size), cached."""
    if state not in _PARCEL_CACHE:
        cols = ["jurisdiction_geoid", "vintage", "land_use_std", "lot_sqft", "zoning_raw"]
        p = store.read(state, "parcels")
        p = p[[c for c in cols if c in p]]
        p = p[p["land_use_std"] == "SF_DETACHED"]
        latest = p.groupby("jurisdiction_geoid")["vintage"].transform("max")
        _PARCEL_CACHE[state] = p[p["vintage"] == latest]
    return _PARCEL_CACHE[state]


def coverage_map(state: str, store, reforms: pd.DataFrame, params: Mapping[str, float]) -> pd.DataFrame:
    """D-021: coverage share of every coded ADU rule in a state, measured on parcels where possible.

    Returns reform_id, geoid, coverage, how. Rules with no zone list or lot minimum need no parcels.
    """
    adu = reforms[reforms["theme"] == "adu"]
    needs = adu["coverage_zones"].notna() | (pd.to_numeric(adu["min_lot_sqft"], errors="coerce") > 0)
    parcels = _sf_parcels(state, store) if needs.any() else None
    rows = []
    for r in adu.itertuples():
        mine = parcels[parcels["jurisdiction_geoid"] == r.jurisdiction_geoid] if parcels is not None else None
        cov, how = rule_coverage(r._asdict(), mine, params)
        rows.append({"reform_id": r.reform_id, "geoid": r.jurisdiction_geoid, "coverage": cov, "how": how})
    return pd.DataFrame(rows, columns=["reform_id", "geoid", "coverage", "how"])


def rule_inputs(state: str, store, geoids, as_of: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    """Rule-type probabilities for `geoids` in `state` (D-021, D-022), and the counts behind them.

    Field probabilities come from every state's coded rules in force (`field_restrict_counts`); coverage from
    each rule's zones and lot minimum on the place's parcels (`coverage_map`); priors for places with no ADU
    row from the coded places of every state, by state and size band (`rule_priors`). Reads
    config/reforms/*.csv at run time, so newly coded rules shrink the unknowns with no code change.
    Returns (table: geoid, rule_class, p_* over TYPES, coverage, rule_age, …, prior_source; info dict).
    """
    from lotline.config import load_state

    p = load_params("adu")
    central = {k: v.value for k, v in p.items()}
    min_count = int(central["adu_rule_min_coded"])
    edges = (central["adu_rule_band_small_max_pop"], central["adu_rule_band_mid_max_pop"])
    reforms = {st: load_reforms(st).assign(state=st) for st in REFORM_STATES}
    counts = field_restrict_counts(pd.concat(reforms.values(), ignore_index=True), as_of)
    coded, covs = [], {}
    for st, r in reforms.items():
        cm = coverage_map(st, store, r, central)
        covs[st] = cm
        local = sorted(g for g in r.loc[r["theme"] == "adu", "jurisdiction_geoid"].unique() if len(g) > 2)
        if not local:
            continue
        fp = field_probabilities(counts, st, min_count)
        cr = current_rules(
            r, local, load_state(st).fips, as_of, fp, dict(zip(cm.reform_id, cm.coverage, strict=True))
        )
        cr = cr[cr["rule_class"] != "unknown"]
        pop = store.read(st, "jurisdictions").set_index("geoid")["pop_2020"]
        coded.append(cr.assign(state=st, population=cr["geoid"].map(pop).astype(float)))
    coded = pd.concat(coded, ignore_index=True)
    priors = rule_priors(coded.dropna(subset=["population"]), edges, min_count)
    fp = field_probabilities(counts, state, min_count)
    cm = covs[state]
    rules = current_rules(
        reforms[state],
        geoids,
        load_state(state).fips,
        as_of,
        fp,
        dict(zip(cm.reform_id, cm.coverage, strict=True)),
    )
    pop = store.read(state, "jurisdictions").set_index("geoid")["pop_2020"]
    rules = rules.assign(state=state, population=rules["geoid"].map(pop).astype(float))
    rules = apply_priors(rules, priors, edges).drop(columns=["state", "band"])
    info = {"field_counts": counts, "field_probs": fp, "priors": priors, "coded": coded, "coverage": covs}
    return rules, info


def county_mix(places: pd.DataFrame, state: str, store, origin: int, coded: pd.DataFrame) -> pd.DataFrame:
    """D-021: blend the rules of coded places that BPS files under a county row (no jurisdiction of their own,
    e.g. Wilmington) into that row, weighted by their share of the row's eligible parcels.

    Share = the place's ACS one-unit detached homes in the county (newest vintage <= origin; Census county
    shares for places spanning counties) / the row's eligible parcels, capped at 1. Row p_* becomes
    (1 − w)·p_row + w·p_place. The mean c is right; a draw still picks one type for the whole row.
    """
    from lotline.adapters.national import geoparts
    from lotline.config import load_state

    juris = set(store.read(state, "jurisdictions")["geoid"])
    orphans = coded[(coded["state"] == state) & ~coded["geoid"].isin(juris) & (coded["geoid"].str.len() == 7)]
    if orphans.empty:
        return places
    shares = geoparts.county_shares(load_state(state).fips, sorted(orphans["geoid"]), store)
    acs = store.read(state, "acs_geo_year")
    acs = acs[(acs["variable"] == "B25024_002") & (acs["end_year"] <= origin) & acs["estimate"].notna()]
    homes = acs.sort_values("end_year").groupby("geo")["estimate"].last()
    out = places.copy()
    rows = out.index[out["kind"] == "county_unincorporated"]
    for o in orphans.itertuples():
        h = float(homes.get(f"place:{o.geoid}", np.nan))
        for sh in shares[shares["place_geoid"] == o.geoid].itertuples():
            target = [i for i in rows if out.at[i, "county_geoid"] == sh.county_geoid]
            if not target or np.isnan(h):
                continue
            i = target[0]
            w = min(1.0, h * sh.share / max(float(out.at[i, "eligible_parcels"]), 1.0))
            for col in P_COLS:
                out.at[i, col] = (1 - w) * out.at[i, col] + w * getattr(o, col)
            out.at[i, "rule_note"] = f"{out.at[i, 'rule_note']}; mixes {o.geoid}'s rule on {w:.0%} of lots"
    out["p_partial"] = out[["p_owner", "p_other", "p_both"]].sum(axis=1)
    return out


def places_from_store(state: str, store, origin: int) -> pd.DataFrame:
    """One row per jurisdiction with ADU-eligible parcels: every input `run` needs, from processed tables.

    Eligible parcels (theme 'adu', current rule version) from the newest year <= origin (else the earliest
    later roll, flagged `parcels_after_origin`); ACS rent and value from the newest vintage <= origin; no
    mortgage rate (forward runs draw `mortgage_rate_forecast`); coded ADU rules in force on 31 December of the
    origin year; observed ADU permits per parcel where local permits flag ADUs.
    Reads only holdout-filtered tables (DataStore); no outcome after the origin is used.
    """
    from lotline.build import eligible as eligible_rule
    from lotline.model import money

    elig = store.read(state, "eligible_parcels")
    elig = elig[(elig["theme"] == "adu") & (elig["rule_version"] == eligible_rule.RULE_VERSION)]
    # newest roll <= origin; where a place has only later rolls (e.g. Austin's 2026 TCAD roll), the earliest
    # of those, flagged: a parcel count is a denominator, not an outcome, so no holdout is touched
    elig = elig.assign(after=elig["year"] > origin, gap=(elig["year"] - origin).abs())
    elig = elig.sort_values(["after", "gap"]).groupby("jurisdiction_geoid").first().reset_index()
    elig = elig.rename(
        columns={"jurisdiction_geoid": "geoid", "year": "parcels_year", "after": "parcels_after_origin"}
    )
    elig = elig.drop(columns="gap")
    juris = store.read(state, "jurisdictions")[["geoid", "name", "kind", "county_geoid", "in_bps"]]
    places = elig.merge(juris, on="geoid", how="left")
    places = places[places["eligible_parcels"].fillna(0) > 0].reset_index(drop=True)
    places = non_overlapping(places, store.read(state, "jurisdictions"), _county_shares(state, store, places))

    market = store.read(state, "market_geo_year")
    cpi = money.index_by_year(market, "cpi_u")
    places["acs_geo"] = places["kind"].map(ACS_PREFIX) + ":" + places["geoid"]
    acs = acs_values(store.read(state, "acs_geo_year"), places["acs_geo"], origin, cpi)
    places = places.merge(acs, left_on="acs_geo", right_index=True, how="left")
    places["mortgage_rate"] = np.nan  # forward run: the rate path is a drawn parameter (market.yaml)

    as_of = pd.Timestamp(f"{origin}-12-31")
    rules, info = rule_inputs(state, store, places["geoid"], as_of)
    places = places.merge(rules, on="geoid", how="left")
    places = county_mix(places, state, store, origin, info["coded"])

    p = load_params("adu")
    first, last = int(p["adu_observed_first_year"].value), int(p["adu_observed_last_year"].value)
    last = min(last, origin)
    counts = observed_adu_counts(store.read(state, "permits"), first, last)
    per_year = counts.groupby("geoid")["adu_permits"].sum() / (last - first + 1)
    places["observed_adu_per_year"] = places["geoid"].map(per_year)
    places["observed_rate"] = places["observed_adu_per_year"] / places["eligible_parcels"]
    return places
