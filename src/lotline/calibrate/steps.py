"""Every calibration step: which fitted values in config/params/ it produces, from what, and how (phase 1).

Each `Step` names the parameters it writes (`produces`: params file -> keys, or "*" for every entry of a file
the step generates whole), the steps it needs first (`after`), the analysis-plan decision it implements, the
script or library function that computes it today, and how its result reaches config today (`how`):

- "code": the script writes config itself;
- "hand": the script prints or reports a value and a person copied it into config.

Phase 1 runs nothing: it records the map, so every fitted number traces to one named step, and
`lotline calibrate --check` keeps config, this registry and `config/calibration.lock.json` in step. Later
phases give each step a `run` function that recomputes its outputs (calibration design, phases 2-4).
`status` marks a step whose fit predates the current model form ("stale"), so a reader sees it plainly.

The map was drawn on 2026-11-25 from each parameter's `source` text and the scripts it names.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Step:
    name: str
    decision: str
    produces: dict[str, tuple[str, ...]]  # params file (config/params/<file>.yaml) -> keys, or ("*",)
    script: str  # where the value is computed today
    how: str  # "code" (writes config) or "hand" (copied from a printout or report)
    reads: tuple[str, ...] = ()  # processed tables or outside series it reads
    after: tuple[str, ...] = ()  # steps whose outputs it needs
    tables: tuple[str, ...] = ()  # other files under config/params/ it writes whole (e.g. a .csv grid)
    seed: int | None = None
    draws: int | None = None
    status: str = "current"  # "current", "stale" (fit on an older model form) or "frozen" (validation only)
    notes: str = ""
    extra: dict = field(default_factory=dict)
    # "module:function" that recomputes the step (phases 2-4); None until it is ported. The function takes a
    # `RunContext` and returns {params file: {key: value}} for the keys the step produces.
    runner: str | None = None


STEPS: tuple[Step, ...] = (
    # ---- data-only statistics (no model fit) ------------------------------------------------------
    Step(
        "completion_factors",
        "protocol §5.10",
        {
            "aggregate": (
                "completion_factor_single_family",
                "completion_factor_multifamily",
                "completion_factor_all",
            )
        },
        "scripts/dev/completion_factors.py (model/completion.py)",
        "hand",
        reads=("FRED new residential construction",),
    ),
    Step(
        "baseline_adu_share",
        "MS-10",
        {"aggregate": ("baseline_adu_share_of_one_unit",)},
        "scripts/dev/adu_baseline_share.py",
        "hand",
        reads=("permits (Met Council, Austin) 2019-22",),
    ),
    Step(
        "eligible_proxy",
        "D-056",
        {"eligible_proxy": ("eligible_proxy_scale", "eligible_proxy_sd")},
        "scripts/dev/eligible_proxy_test.py (model/eligible_proxy.py)",
        "hand",
        reads=("parcels", "acs_housing"),
    ),
    Step(
        "adu_reference_values",
        "D-060",
        {"hazard": ("adu_ref_rent_usd", "adu_ref_home_value_usd", "adu_ref_mortgage_rate")},
        "scripts/dev/adu_reference.py",
        "hand",
        reads=("ACS 2015-19 (Portland)", "FRED MORTGAGE30US", "CPI"),
    ),
    Step(
        "mortgage_rate_forecast",
        "market",
        {"market": ("mortgage_rate_forecast",)},
        "FRED MORTGAGE30US 2025 annual mean (market_geo_year)",
        "hand",
        reads=("FRED MORTGAGE30US",),
    ),
    Step(
        "adu_undercount_k",
        "D-074, D-075, D-078, D-081",
        {"adu": ("adu_flag_undercount",)},
        "scripts/dev/nc_wake_roll_adu_diff.py, tx_adu_coverage.py, tx_austin_adu_k.py, or_adu_coverage.py, "
        "or_portland_adu_k.py, mn_adu_coverage.py, oh_adu_coverage.py, parser_phrase_check.py",
        "hand",
        reads=("parcel roll diffs", "permit ADU flags", "hand checks"),
        notes="One row per report; the prior over the rows is recomputed at run time (undercount.prior).",
    ),
    Step(
        "adu_survey_report_rate",
        "D-041",
        {"adu_counts": ("adu_survey_report_rate",)},
        "D-041 count (scripts/dev/calibrate_adu.py area)",
        "hand",
        reads=("permits (Met Council, Minneapolis)",),
        notes="111 of 194 Minneapolis ADUs recorded by Met Council; the exact command is not recorded.",
    ),
    Step(
        "adu_covariate_centres",
        "D-083, D-084, D-087",
        {
            "adu_owner": ("adu_owner_share_center", "adu_owner_share_scale"),
            "adu_age": ("adu_age_share_center", "adu_age_share_scale"),
        },
        "scripts/dev/adu_covariate_screen.py",
        "hand",
        reads=("ACS 2011-15, 57 fit places",),
        notes="Read only by the development scripts, not by the engine.",
    ),
    # ---- ADU --------------------------------------------------------------------------------------
    Step(
        "adu_ramp_share",
        "D-048",
        {"hazard": ("adu_ramp_share",)},
        "scripts/dev/calibrate_adu.py (D-041 with the ramp)",
        "hand",
        after=("adu_undercount_k",),
        status="stale",
        notes="Fitted on the D-041 form before the D-088 place types and D-096 rule rows.",
    ),
    Step(
        "adu_joint",
        "D-096",
        {
            "hazard": ("adu_mature_hazard_ref", "adu_place_effect_variance"),
            "adu": ("adu_partial_rule_share", "adu_owner_occupancy_share"),
            "adu_place_types": ("adu_types_core_log_multiplier",),
        },
        "scripts/dev/adu_refit_fixed_rows.py adu_config_fit.py (model/adu_types.fit3_types); fit set from "
        "scripts/dev/adu_joint_refit.py",
        "hand",
        reads=("permits", "parcels", "reforms", "acs_housing", "bps"),
        after=("adu_undercount_k", "adu_survey_report_rate"),
        seed=20261111,
        draws=20_000,
        notes="Copied from reports/adu-final-config/fit.json.",
    ),
    Step(
        "adu_partial_share_grid",
        "D-097",
        {},
        "scripts/dev/adu_mx_grid.py --config-out",
        "code",
        after=("adu_joint",),
        tables=("adu_partial_share_grid.csv",),
        notes="Its row at the partial share in adu.yaml must equal hazard.yaml's theta and alpha.",
    ),
    Step(
        "adu_anchor_slopes",
        "D-088, D-030",
        {"adu_anchor": ("*",)},
        "scripts/dev/adu_types_slopes.py --out (calibrate_adu.information_se)",
        "code",
        after=("adu_joint",),
    ),
    Step(
        "adu_calibration_range",
        "D-060",
        {
            "hazard": (
                "adu_calibration_rent_low_usd",
                "adu_calibration_rent_high_usd",
                "adu_calibration_value_low_usd",
                "adu_calibration_value_high_usd",
                "adu_calibration_rate_low",
                "adu_calibration_rate_high",
            )
        },
        "scripts/dev/adu_reference.py --fit-set --write (calibrate_adu.fit_set_range)",
        "code",
        after=("adu_joint",),
    ),
    Step(
        "adu_town_prior_sd",
        "D-089",
        {"adu_place_types": ("adu_types_town_prior_sd",)},
        "arithmetic: |core multiplier| / 1.645",
        "hand",
        after=("adu_joint",),
    ),
    Step(
        "adu_new_rule",
        "D-099",
        {"adu": ("adu_new_rule_share",)},
        "scripts/dev/adu_new_rule.py (model/adu_new_rule.py)",
        "hand",
        after=("adu_joint",),
        notes="The held-out check rejected the fit, so the share stays 1.",
    ),
    Step(
        "adu_state_effect",
        "D-043, D-044, D-053",
        {"adu_state_effect": ("*",)},
        "scripts/dev/calibrate_adu.py --tau-draws, then --state-effect-config",
        "code",
        after=("adu_undercount_k",),
        seed=20261020,
        draws=20_000,
        status="stale",
        notes="Fitted on the D-053 form, before the D-088 place types and D-096 rule rows.",
    ),
    Step(
        "adu_drift",
        "D-090, D-091",
        {"adu": ("adu_drift_sigma",)},
        "scripts/dev/adu_drift.py (reads scripts/dev/adu_time_split.py)",
        "hand",
        after=("adu_undercount_k",),
        draws=500,
        status="stale",
        notes="From the D-090 forecast fits, not re-derived on the D-096 form.",
    ),
    # ---- missing middle ---------------------------------------------------------------------------
    Step(
        "mm_year_spread",
        "D-092 (run 9)",
        {"mm_hazard": ("mm_year_spread_phi",)},
        "scripts/dev/mm_kappa_d092.py --form year (model/calibrate_mm.fit_noise)",
        "hand",
        reads=("bps", "parcels", "reforms"),
        notes="Also passed to later scripts as --phi 13.63.",
    ),
    Step(
        "mm_c4",
        "D-092 (run 10, C4)",
        {"mm_hazard": ("mm_mature_hazard_ref", "mm_place_effect_variance", "mm_ramp_half_years")},
        "scripts/dev/calibrate_mm_d092.py --phi 13.63 (model/calibrate_mm.fit, with_phi)",
        "hand",
        reads=("bps", "parcels", "reforms", "acs_housing"),
        after=("mm_year_spread",),
        seed=20261106,
        draws=20_000,
    ),
    Step(
        "mm_fast_ramp",
        "D-100",
        {"mm_hazard": ("mm_ramp_half_years_fast",)},
        "scripts/dev/mm_ramp_d100.py (model/mm_routes.fit_routes)",
        "hand",
        after=("mm_c4",),
    ),
    Step(
        "mm_units_per_project",
        "D-038",
        {"mm_hazard": ("mm_units_per_project",)},
        "scripts/dev/calibrate_mm.py",
        "hand",
        reads=("bps",),
    ),
    # ---- frozen validation inputs -----------------------------------------------------------------
    Step(
        "v5_charlotte_prior",
        "V5",
        {"v5_charlotte": ("n1_sf_share", "n1_vacant_share")},
        "adapters/states/nc/clt_v5.town_prior",
        "hand",
        reads=("NC OneMap parcels",),
        status="frozen",
        notes="Used only by the frozen V5 Charlotte test.",
    ),
)
