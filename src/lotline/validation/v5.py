"""V5 Charlotte blind forward test (analysis plan D-071; validation plan V5).

Predicts new 2-4 unit buildings in Census BPS for Mecklenburg County (37119, where BPS files Charlotte's
permits) in 2023, 2024 and 2025, after Charlotte's UDO allowed duplexes and triplexes on every N1 lot from
2023-06-01, before any Charlotte or Mecklenburg outcome from that day is seen (holdout `V5-NC-CHARLOTTE`).

For year t and draw d (D-038/D-042, as V9's missing-middle part, D-051):

    buildings_dt = Poisson(B) + Poisson(θ_d u_d E_d gap F ramp(t − T + 0.5)),   T = 2023

- B: 37119's mean 2-4 unit buildings over 2020-2022, held flat (the growth index needs blind years).
- E_d = N1 lots × s_d, s_d ~ triangular(sf.low + vacant.low, sf.value + vacant.value, sf.high + vacant.high)
  from `config/params/v5_charlotte.yaml` (the six-town prior, option (b)).
- gap = dose of the UDO row on 1 July 2023 − dose on 1 July 2022 (`estimate_mm.rules_by_year`), coverage 1
  because E already counts only N1 lots.
- F = F(PCR)/F(1) from Charlotte's ACS rent ending <= 2022 and the 2022 cost index.
- θ_d, α_d lognormal from `mm_hazard.yaml`'s 90% intervals; u_d ~ Gamma(mean 1, variance α_d), one per draw.

Homes (secondary target a) are the baseline buildings × the 2020-2022 homes per building plus the added
buildings × `mm_units_per_project` (triangular). The added buildings alone are secondary target (b).

Inputs come only from holdout-filtered tables and `config/`; no annual input after 2022 is read.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

TEST_ID = "V5-NC-CHARLOTTE"
STATE = "NC"
CHARLOTTE = "3712000"
MECKLENBURG = "37119"
UDO_REFORM = "NC-3712000-missing_middle-2023"
T = 2023  # first event year: the UDO is in force on 1 July 2023 (effective 2023-06-01)
YEARS = (2023, 2024, 2025)
BASELINE_YEARS = (2020, 2021, 2022)
INPUT_LAST_YEAR = 2022  # no annual input touches the window (D-071)
FIT_STATES = ("MN", "NC", "OH", "TX")  # D-022 blank shares, as V9
CONFIG_FILES = (
    "config/params/mm_hazard.yaml",
    "config/params/mm.yaml",
    "config/params/proforma.yaml",
    "config/params/v5_charlotte.yaml",
    "config/params/adu.yaml",
    "config/reforms/mn.csv",
    "config/reforms/nc.csv",
    "config/reforms/oh.csv",
    "config/reforms/tx.csv",
    "config/states/nc.yaml",
    "config/crosswalks/nc_clt_udo_n1.csv",
)


@dataclass(frozen=True)
class Inputs:
    n1_lots: int
    share_low: float  # eligible share of N1 lots (house or vacant lot), triangular
    share_value: float
    share_high: float
    dose_pre: float
    dose_udo: float
    rent: float  # 2025 dollars, newest ACS 5-year ending <= 2022
    cost_index: float
    pcr: float
    f_ratio: float
    baseline_buildings: dict  # {year: buildings} 2020-2022
    baseline_homes: dict  # {year: homes} 2020-2022

    @property
    def gap(self) -> float:
        return max(self.dose_udo - self.dose_pre, 0.0)

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


def eligible_share(sf, vacant) -> tuple[float, float, float]:
    """(low, value, high) of the eligible share: the sum of the house and vacant-lot shares at each end.
    By hand, the YAML's values: (0.515 + 0.067, 0.732 + 0.119, 0.812 + 0.149) = (0.582, 0.851, 0.961)."""
    return (sf.low + vacant.low, sf.value + vacant.value, sf.high + vacant.high)


def baseline(bps: pd.DataFrame, geoid: str = MECKLENBURG, years=BASELINE_YEARS) -> tuple[dict, dict]:
    """({year: 2-4 unit buildings}, {year: homes in them}) for `geoid` over `years`, from BPS rows.
    Raises if a year is missing or any year is after INPUT_LAST_YEAR."""
    if max(years) > INPUT_LAST_YEAR:
        raise ValueError(f"baseline years must end by {INPUT_LAST_YEAR}")
    b = bps[(bps["geoid"] == geoid) & bps["year"].isin(years)]
    b = b.groupby("year")[["bldgs_2", "bldgs_3_4", "units_2", "units_3_4"]].sum()
    missing = set(years) - set(b.index.astype(int))
    if missing:
        raise ValueError(f"BPS {geoid} has no rows for {sorted(missing)}")
    bld = {int(y): float(r.bldgs_2 + r.bldgs_3_4) for y, r in b.iterrows()}
    hom = {int(y): float(r.units_2 + r.units_3_4) for y, r in b.iterrows()}
    return bld, hom


def ramp_shape(half: float, slope: float, years=YEARS, T: int = T) -> np.ndarray:
    """Share of the mature hazard in each year: ramp at age t − T + 0.5."""
    from lotline.model.hazard import ramp

    return ramp(np.asarray(years, float) - T + 0.5, half, slope)


def _lognormal(spec, n: int, rng) -> np.ndarray:
    """Median at the value, log-SD from the 90% interval (as V9 and D-030)."""
    sd = (math.log(spec.high) - math.log(spec.low)) / 3.29 if spec.low < spec.high else 0.0
    return np.exp(math.log(spec.value) + sd * rng.standard_normal(n))


def _triangular(rng, low, mode, high, n):
    return rng.triangular(low, mode, high, n) if low < high else np.full(n, mode)


def draws(inp: Inputs, n: int, seed: int, params: Mapping | None = None) -> dict[str, np.ndarray]:
    """Predictive draws, each (n, years): `baseline` and `added` buildings, their sum `buildings`, and
    `homes`. `params` (a load_params-like mapping) defaults to mm_hazard.yaml | mm.yaml."""
    from lotline.config import load_params

    sp = params if params is not None else load_params("mm_hazard") | load_params("mm")
    rng = np.random.default_rng(seed)
    theta = _lognormal(sp["mm_mature_hazard_ref"], n, rng)
    alpha = _lognormal(sp["mm_place_effect_variance"], n, rng)
    u = rng.gamma(1 / alpha, alpha)
    s = _triangular(rng, inp.share_low, inp.share_value, inp.share_high, n)
    upp = sp["mm_units_per_project"]
    units = _triangular(rng, upp.low, upp.value, upp.high, n)
    shape = ramp_shape(sp["mm_ramp_half_years"].value, sp["mm_ramp_slope_years"].value)
    mu = (theta * u * inp.n1_lots * s * inp.gap * inp.f_ratio)[:, None] * shape[None, :]
    added = rng.poisson(mu).astype(float)
    base = rng.poisson(inp.B, size=(n, len(YEARS))).astype(float)
    homes = base * inp.homes_per_baseline_building + added * units[:, None]
    return {"baseline": base, "added": added, "buildings": base + added, "homes": homes}


def expected_added(inp: Inputs, theta: float, half: float, slope: float, u: float = 1.0) -> np.ndarray:
    """Mean added buildings per year at fixed θ, u and the central eligible share."""
    return theta * u * inp.n1_lots * inp.share_value * inp.gap * inp.f_ratio * ramp_shape(half, slope)


def stats(a: np.ndarray) -> dict:
    p10, p50, p90 = np.percentile(a, [10, 50, 90])
    return {"p10": float(p10), "p50": float(p50), "p90": float(p90), "mean": float(np.mean(a))}


def summarize(d: Mapping[str, np.ndarray]) -> dict:
    """{measure: {year: stats, "2023-2025": stats}}; the total is summed draw by draw."""
    out = {}
    for k, a in d.items():
        per = {str(y): stats(a[:, j]) for j, y in enumerate(YEARS)}
        per[f"{YEARS[0]}-{YEARS[-1]}"] = stats(a.sum(axis=1))
        out[k] = per
    return out


# ---------------------------------------------------------------------------------------------------------
# Inputs from the store (holdout-filtered; read only before the window)
# ---------------------------------------------------------------------------------------------------------


def charlotte_dose(blanks=None) -> tuple[float, float]:
    """(dose on 1 July 2022, dose on 1 July 2023) of Charlotte's coded missing-middle rules, coverage 1."""
    from lotline.config import load_params
    from lotline.model import estimate_mm as mm
    from lotline.model import rule_tags
    from lotline.model.scenarios import adu

    if blanks is None:
        four = {st: rule_tags.apply(adu.load_reforms(st)) for st in FIT_STATES}
        every = pd.concat([r.assign(state=st) for st, r in four.items()], ignore_index=True)
        blanks = mm.blank_shares(every[every["status"] == "in_force"])
    rows = rule_tags.apply(adu.load_reforms(STATE))
    rows = rows[
        (rows["jurisdiction_geoid"] == CHARLOTTE)
        & (rows["theme"] == "missing_middle")
        & (rows["status"] == "in_force")
    ]
    if UDO_REFORM not in set(rows["reform_id"]):
        raise ValueError(f"{UDO_REFORM} is not coded in force")
    grade = load_params("mm")["mm_dose_grade_permit"].value
    (pre, _), (post, _) = mm.rules_by_year(rows, [T - 1, T], {}, blanks, grade)
    return float(pre), float(post)


def inputs(store) -> Inputs:
    from lotline.adapters.states.nc import clt_v5
    from lotline.config import load_params
    from lotline.model import estimate_mm as mm
    from lotline.model import hazard, money
    from lotline.model.calibrate_mm import feasibility_ratio
    from lotline.model.scenarios import adu
    from lotline.validation import holdout

    parcels = pd.read_parquet(store.processed(STATE, "parcels", "clt_udo_translation"))
    parcels = holdout.apply(
        parcels, STATE, geoid_col="jurisdiction_geoid", date_col="vintage_date", year_col="vintage",
        snapshot=True,
    )  # fmt: skip
    if pd.to_datetime(parcels["vintage_date"]).max() >= pd.Timestamp("2023-06-01"):
        raise ValueError("the N1 roll must predate the window")
    n1 = int(clt_v5.n1_lots(parcels)["lots"].sum())

    v5 = load_params("v5_charlotte")
    low, value, high = eligible_share(v5["n1_sf_share"], v5["n1_vacant_share"])
    pre, post = charlotte_dose()

    bps = holdout.apply(store.read(STATE, "bps_place_year"), STATE, geoid_col="geoid", year_col="year")
    bld, hom = baseline(bps)

    market = store.read(STATE, "market_geo_year")
    cpi = money.index_by_year(market, "cpi_u")
    cost = hazard.cost_index_by_year(market)
    acs = store.read(STATE, "acs_geo_year")
    acs = acs[acs["end_year"] <= INPUT_LAST_YEAR]
    v = adu.acs_values(acs, pd.Series([f"place:{CHARLOTTE}"]), INPUT_LAST_YEAR, cpi)
    rent = float(v.iloc[0]["rent"])
    ci = float(cost[INPUT_LAST_YEAR])
    pcr = float(mm.plex_price_to_cost(rent, cost_index=ci))
    margin = load_params("proforma")["developer_margin"].value
    sigma = load_params("mm_hazard")["mm_feasibility_dispersion"].value
    return Inputs(
        n1_lots=n1, share_low=low, share_value=value, share_high=high, dose_pre=pre, dose_udo=post,
        rent=rent, cost_index=ci, pcr=pcr, f_ratio=feasibility_ratio(pcr, margin, sigma),
        baseline_buildings=bld, baseline_homes=hom,
    )  # fmt: skip


# ---------------------------------------------------------------------------------------------------------
# The freeze file
# ---------------------------------------------------------------------------------------------------------


def file_hashes(paths, repo: Path) -> dict:
    """sha256 of each repo file (case-insensitive lookup is the filesystem's)."""
    return {p: hashlib.sha256((repo / p).read_bytes()).hexdigest() for p in paths}


def table_hashes(store) -> dict:
    out = {}
    for t in ("parcels", "bps_place_year", "acs_geo_year", "market_geo_year"):
        root = store.processed(STATE, t)
        h = hashlib.sha256()
        files = [root / "clt_udo_translation.parquet"] if t == "parcels" else sorted(root.glob("*.parquet"))
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
        for f in ("mm_hazard", "mm", "v5_charlotte")
    }
    ins = asdict(inp) | {
        "gap": inp.gap, "B": inp.B, "homes_per_baseline_building": inp.homes_per_baseline_building,
    }  # fmt: skip
    return {
        "test_id": TEST_ID,
        "method": "analysis plan D-071",
        "commit": commit,
        "draws": n,
        "seed": seed,
        "years": list(YEARS),
        "target": "BPS 37119 new 2-4 unit buildings (bldgs_2 + bldgs_3_4), sum of 2023-2025",
        "pass_rule": "observed 2023-2025 sum within P10-P90 of `prediction.buildings['2023-2025']`",
        "secondary": {
            "homes": "BPS 37119 homes in 2-4 unit buildings (units_2 + units_3_4), 2023-2025",
            "added": "added buildings on Charlotte's N1 lots alone (descriptive)",
        },
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


# ---------------------------------------------------------------------------------------------------------
# Scoring (D-071; only after the freeze is on main and the holdout is released)
# ---------------------------------------------------------------------------------------------------------


def verdict(ob: float, p10: float, p50: float, p90: float) -> str:
    """D-040: 'useful' if inside P10-P90 and P50 / 2 <= observed <= 2 P50; 'inside only'; else missed."""
    if not p10 <= ob <= p90:
        return "missed (over)" if ob < p10 else "missed (under)"
    ratio = ob / p50 if p50 > 0 else (1.0 if ob == 0 else np.inf)
    return "useful" if 0.5 <= ratio <= 2 else "inside only"


def score(draws_: np.ndarray, observed: float, bench: np.ndarray | None = None) -> dict:
    """Pass rule (observed within P10-P90 of the draws), D-040's verdict, randomized coverage (D-003), the
    observed value's predictive percentile, and CRPS against a benchmark's draws if given."""
    from lotline.model.baseline import crps_from_draws, randomized_coverage

    x = np.asarray(draws_, float)
    s = stats(x)
    out = s | {
        "observed": float(observed),
        "pass": bool(s["p10"] <= observed <= s["p90"]),
        "verdict": verdict(observed, s["p10"], s["p50"], s["p90"]),
        "obs_over_p50": float(observed / s["p50"]) if s["p50"] > 0 else None,
        "percentile": float(100 * ((x < observed).mean() + 0.5 * (x == observed).mean())),
        "coverage_rand": float(randomized_coverage(x[None, :], np.array([observed]), 0.1, 0.9)[0]),
        "crps_model": float(crps_from_draws(x[None, :], np.array([observed]))[0]),
    }
    if bench is not None:
        out["crps_no_reform"] = float(
            crps_from_draws(np.asarray(bench, float)[None, :], np.array([observed]))[0]
        )
    return out


def observed(bps: pd.DataFrame, geoid: str = MECKLENBURG, years=YEARS) -> tuple[dict, dict]:
    """({year: 2-4 unit buildings}, {year: homes}) observed in BPS for the window years (unblinded rows)."""
    b = bps[(bps["geoid"] == geoid) & bps["year"].isin(years)]
    b = b.groupby("year")[["bldgs_2", "bldgs_3_4", "units_2", "units_3_4"]].sum()
    missing = set(years) - set(b.index.astype(int))
    if missing:
        raise ValueError(f"BPS {geoid} has no rows for {sorted(missing)}: is the holdout still applied?")
    return (
        {int(y): float(r.bldgs_2 + r.bldgs_3_4) for y, r in b.iterrows()},
        {int(y): float(r.units_2 + r.units_3_4) for y, r in b.iterrows()},
    )
