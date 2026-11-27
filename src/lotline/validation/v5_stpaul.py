"""V5 St. Paul blind forward test with C4 (analysis plan D-098; Charlotte's D-071 is the template).

Predicts new 2-4 unit buildings in Census BPS for St. Paul (2758000) in 2024, 2025 and 2026, after St. Paul's
1-4 unit reform (H1/H2 districts, effective 2023-11-26), before any St. Paul outcome from 2024 is seen
(holdout `V5-MN-STPAUL`). The pass rule uses 2024-2025.

For year t and draw d (C4, as the fit, `mm_hazard.yaml`):

    buildings_dt ~ NB(mean B + θ_d u_d E gap F ramp(t − T + 0.5), size φ),   T = 2024

drawn as Poisson(B g) + Poisson(A g) with one g ~ Gamma(mean 1, variance 1/φ) per draw and year, so the
baseline and the added part can be reported apart and their sum is the negative binomial above.

- B: St. Paul's mean 2-4 unit buildings over 2021-2023, held flat (the growth index needs blind years).
- E: eligible H1/H2 lots (rule 1.1) on the 2023 roll (`adapters.states.mn.stpaul_v5`).
- gap: dose of the coded rule on 1 July 2024 minus 1 July 2023.
- F: F(PCR)/F(1) from St. Paul's ACS rent ending <= 2023 and the 2023 cost index.
- θ_d, α_d lognormal from their 90% intervals; u_d ~ Gamma(mean 1, variance α_d), one per draw.

Inputs come only from holdout-filtered tables and `config/`; no annual input after 2023 is read.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.validation.v5 import _lognormal, _triangular, file_hashes, score, stats, verdict  # noqa: F401

TEST_ID = "V5-MN-STPAUL"
STATE = "MN"
ST_PAUL = "2758000"
REFORM = "MN-2758000-missing_middle-2023"
T = 2024  # first event year: the rule is in force on 1 July 2024 (effective 2023-11-26)
YEARS = (2024, 2025, 2026)
PASS_YEARS = (2024, 2025)  # scorable before 16 December 2026; 2026 waits for BPS 2026
BASELINE_YEARS = (2021, 2022, 2023)
INPUT_LAST_YEAR = 2023
FIT_STATES = ("MN", "NC", "OH", "TX")  # D-022 blank shares, as V5 Charlotte and V9
CONFIG_FILES = (
    "config/params/mm_hazard.yaml",
    "config/params/mm.yaml",
    "config/params/proforma.yaml",
    "config/params/adu.yaml",
    "config/reforms/mn.csv",
    "config/reforms/nc.csv",
    "config/reforms/oh.csv",
    "config/reforms/tx.csv",
    "config/states/mn.yaml",
)


@dataclass(frozen=True)
class Inputs:
    eligible: int  # eligible H1/H2 lots
    dose_pre: float
    dose_post: float
    rent: float  # 2025 dollars, newest ACS 5-year ending <= 2023
    cost_index: float
    pcr: float
    f_ratio: float
    baseline_buildings: dict  # {year: buildings} 2021-2023
    baseline_homes: dict

    @property
    def gap(self) -> float:
        return max(self.dose_post - self.dose_pre, 0.0)

    @property
    def B(self) -> float:
        return float(np.mean(list(self.baseline_buildings.values())))

    @property
    def homes_per_baseline_building(self) -> float:
        b = sum(self.baseline_buildings.values())
        return float(sum(self.baseline_homes.values()) / b) if b > 0 else float("nan")


# ---------------------------------------------------------------------------------------------------------
# Pure pieces (tested by hand)
# ---------------------------------------------------------------------------------------------------------


def baseline(bps: pd.DataFrame, geoid: str = ST_PAUL, years=BASELINE_YEARS) -> tuple[dict, dict]:
    """({year: 2-4 unit buildings}, {year: homes}) for `geoid` over `years`. Raises if a year is missing or
    after INPUT_LAST_YEAR."""
    if max(years) > INPUT_LAST_YEAR:
        raise ValueError(f"baseline years must end by {INPUT_LAST_YEAR}")
    b = bps[(bps["geoid"] == geoid) & bps["year"].isin(years)]
    b = b.groupby("year")[["bldgs_2", "bldgs_3_4", "units_2", "units_3_4"]].sum()
    missing = set(years) - set(b.index.astype(int))
    if missing:
        raise ValueError(f"BPS {geoid} has no rows for {sorted(missing)}")
    return (
        {int(y): float(r.bldgs_2 + r.bldgs_3_4) for y, r in b.iterrows()},
        {int(y): float(r.units_2 + r.units_3_4) for y, r in b.iterrows()},
    )


def scorable_years(bps: pd.DataFrame, geoid: str = ST_PAUL, years=YEARS) -> tuple[int, ...]:
    """The window years BPS already has a row for (2026 waits for its publication).

    By hand: rows for 2023, 2024 and 2025 -> (2024, 2025)."""
    have = set(bps.loc[bps["geoid"] == geoid, "year"].astype(int))
    return tuple(y for y in years if y in have)


def ramp_shape(half: float, slope: float, years=YEARS, T: int = T) -> np.ndarray:
    """Share of the mature hazard in each year: ramp at age t − T + 0.5."""
    from lotline.model.hazard import ramp

    return ramp(np.asarray(years, float) - T + 0.5, half, slope)


def draws(inp: Inputs, n: int, seed: int, params: Mapping | None = None) -> dict[str, np.ndarray]:
    """Predictive draws, each (n, years): `baseline`, `added`, their sum `buildings`, and `homes`."""
    from lotline.config import load_params

    sp = params if params is not None else load_params("mm_hazard") | load_params("mm")
    rng = np.random.default_rng(seed)
    theta = _lognormal(sp["mm_mature_hazard_ref"], n, rng)
    alpha = _lognormal(sp["mm_place_effect_variance"], n, rng)
    u = rng.gamma(1 / alpha, alpha)
    upp = sp["mm_units_per_project"]
    units = _triangular(rng, upp.low, upp.value, upp.high, n)
    phi = float(sp["mm_year_spread_phi"].value)
    shape = ramp_shape(sp["mm_ramp_half_years"].value, sp["mm_ramp_slope_years"].value)
    A = (theta * u * inp.eligible * inp.gap * inp.f_ratio)[:, None] * shape[None, :]
    g = rng.gamma(phi, 1.0 / phi, size=A.shape)
    base = rng.poisson(inp.B * g).astype(float)
    added = rng.poisson(A * g).astype(float)
    homes = base * inp.homes_per_baseline_building + added * units[:, None]
    return {"baseline": base, "added": added, "buildings": base + added, "homes": homes}


def summarize(d: Mapping[str, np.ndarray], years=YEARS) -> dict:
    """{measure: {year: stats, "2024-2025": stats, "2024-2026": stats}}; sums are draw by draw."""
    out = {}
    for k, a in d.items():
        per = {str(y): stats(a[:, j]) for j, y in enumerate(years)}
        per[f"{PASS_YEARS[0]}-{PASS_YEARS[-1]}"] = stats(a[:, : len(PASS_YEARS)].sum(axis=1))
        per[f"{years[0]}-{years[-1]}"] = stats(a.sum(axis=1))
        out[k] = per
    return out


# ---------------------------------------------------------------------------------------------------------
# Inputs from the store (holdout-filtered; read only before the window)
# ---------------------------------------------------------------------------------------------------------


def stpaul_dose() -> tuple[float, float]:
    """(dose on 1 July 2023, dose on 1 July 2024) of St. Paul's coded missing-middle rules, coverage 1
    (E already counts only H1/H2 lots)."""
    from lotline.calibrate.mm import estimate_mm as mm
    from lotline.config import load_params
    from lotline.model import rule_tags
    from lotline.model.scenarios import adu

    four = {st: rule_tags.apply(adu.load_reforms(st)) for st in FIT_STATES}
    every = pd.concat([r.assign(state=st) for st, r in four.items()], ignore_index=True)
    blanks = mm.blank_shares(every[every["status"] == "in_force"])
    rows = four[STATE]
    rows = rows[
        (rows["jurisdiction_geoid"] == ST_PAUL)
        & (rows["theme"] == "missing_middle")
        & (rows["status"] == "in_force")
    ]
    if REFORM not in set(rows["reform_id"]):
        raise ValueError(f"{REFORM} is not coded in force")
    grade = load_params("mm")["mm_dose_grade_permit"].value
    (pre, _), (post, _) = mm.rules_by_year(rows, [T - 1, T], {}, blanks, grade)
    return float(pre), float(post)


def inputs(store) -> Inputs:
    from lotline.adapters.states.mn import stpaul_v5
    from lotline.calibrate.mm import estimate_mm as mm
    from lotline.calibrate.mm.calibrate_mm import feasibility_ratio
    from lotline.config import load_params
    from lotline.model import hazard, money
    from lotline.model.scenarios import adu
    from lotline.validation import holdout

    eligible = int(stpaul_v5.load(store)["h_lots"]["eligible"].sum())
    pre, post = stpaul_dose()
    bps = holdout.apply(store.read(STATE, "bps_place_year"), STATE, geoid_col="geoid", year_col="year")
    # The baseline reads 2021-2023 only (`baseline` refuses later years). Rows after 2023 are dropped here
    # too, so the inputs match before and after the holdout is released (scoring regenerates the freeze).
    bld, hom = baseline(bps[bps["year"] <= INPUT_LAST_YEAR])
    market = store.read(STATE, "market_geo_year")
    cpi = money.index_by_year(market, "cpi_u")
    cost = hazard.cost_index_by_year(market)
    acs = store.read(STATE, "acs_geo_year")
    acs = acs[acs["end_year"] <= INPUT_LAST_YEAR]
    v = adu.acs_values(acs, pd.Series([f"place:{ST_PAUL}"]), INPUT_LAST_YEAR, cpi)
    rent = float(v.iloc[0]["rent"])
    ci = float(cost[INPUT_LAST_YEAR])
    pcr = float(mm.plex_price_to_cost(rent, cost_index=ci))
    margin = load_params("proforma")["developer_margin"].value
    sigma = load_params("mm_hazard")["mm_feasibility_dispersion"].value
    return Inputs(
        eligible=eligible, dose_pre=pre, dose_post=post, rent=rent, cost_index=ci, pcr=pcr,
        f_ratio=feasibility_ratio(pcr, margin, sigma), baseline_buildings=bld, baseline_homes=hom,
    )  # fmt: skip


# ---------------------------------------------------------------------------------------------------------
# The freeze file
# ---------------------------------------------------------------------------------------------------------


def table_hashes(store) -> dict:
    import hashlib

    out = {}
    for t in ("parcels", "bps_place_year", "acs_geo_year", "market_geo_year"):
        root = store.processed(STATE, t)
        h = hashlib.sha256()
        files = [root / "metc_parcels.parquet"] if t == "parcels" else sorted(root.glob("*.parquet"))
        for f in files:
            h.update(f.name.encode())
            h.update(f.read_bytes())
        out[t] = h.hexdigest()
    return out


def freeze_payload(inp: Inputs, d: Mapping[str, np.ndarray], n: int, seed: int, store, repo: Path) -> dict:
    from lotline.config import load_params

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    params = {
        f: {k: {"value": v.value, "low": v.low, "high": v.high} for k, v in load_params(f).items()}
        for f in ("mm_hazard", "mm")
    }
    ins = asdict(inp) | {
        "gap": inp.gap, "B": inp.B, "homes_per_baseline_building": inp.homes_per_baseline_building,
    }  # fmt: skip
    return {
        "test_id": TEST_ID,
        "method": "analysis plan D-098 (template D-071); model C4 (D-092 run 10)",
        "commit": commit,
        "draws": n,
        "seed": seed,
        "years": list(YEARS),
        "target": "BPS 2758000 new 2-4 unit buildings (bldgs_2 + bldgs_3_4), sum of 2024-2025",
        "pass_rule": "observed 2024-2025 sum within P10-P90 of `prediction.buildings['2024-2025']`",
        "secondary": {
            "homes": "BPS 2758000 homes in 2-4 unit buildings (units_2 + units_3_4)",
            "added": "added buildings on H1/H2 lots alone (descriptive, against Met Council DTQ permits)",
            "later": "2026 and 2024-2026, scored when BPS 2026 is published",
        },
        "exposure": "D-013: post-reform St. Paul figures appeared in a research document during scouting; "
        "not reread and not used",
        "inputs": ins,
        "params": params,
        "input_table_sha256": table_hashes(store),
        "config_sha256": file_hashes(CONFIG_FILES, repo),
        "prediction": summarize(d),
    }


def write_freeze(payload: dict, repo: Path) -> Path:
    """Write the freeze file; refuses to overwrite (a freeze is made once)."""
    from lotline.validation.holdout import frozen_path

    path = frozen_path(TEST_ID, repo)
    if path.exists():
        raise FileExistsError(f"{path} exists: a frozen prediction is never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    return path
