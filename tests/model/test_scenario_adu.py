"""Handbook ADU scenario (model/scenarios/adu.py): one place by hand end to end, levers off, one ADU per
parcel,
monotone in profit, increment over current rules, additionality. Synthetic inputs only."""

import math

import numpy as np
import pandas as pd
import pytest

from lotline.model.scenarios import adu

P = adu.central_params()
A4 = {
    "adu_mature_hazard_ref": 0.004,
    "adu_ref_cost_index": 1.0,
}  # the hand example's anchor (the configured one is estimated, D-019)


def _places(**cols):
    base = {
        "geoid": ["X"],
        "eligible_parcels": [2000.0],
        "rent": [1100.0],
        "home_value": [P["adu_ref_home_value_usd"] / 2],
        "mortgage_rate": [P["adu_ref_mortgage_rate"] + 2],
        "rule_class": ["none"],
        "rule_age": [np.nan],
        "observed_rate": [np.nan],
    }
    base.update({k: v if isinstance(v, list) else [v] for k, v in cols.items()})
    n = max(len(v) for v in base.values())
    return pd.DataFrame({k: v * n if len(v) == 1 else v for k, v in base.items()})


def test_one_jurisdiction_year_by_hand():
    """2,000 eligible parcels; rent $1,100, half the reference home value, rates +2 points; no ADU rule today.
    Mature hazard 0.0014219 (test_hazard: worked by hand). Year 1: ramp(1) = 1 / (1 + e^(4/3)) = 0.20861, so
    the
    Handbook hazard is 0.0014219 × 0.20861 = 0.00029662 and gross ADU permits = 2,000 × 0.00029662 = 0.5933.
    Current rules give none, so all 0.5933 are added. Homes = 0.5933 × 0.65 (net-new) × (1 − 0.10)
    (formalization) = 0.3470. Year 2: pool 2,000 − 0.5933; ramp(2) = 0.5; 1,999.407 × 0.0014219 × 0.5 =
    1.4215."""
    out = adu.central_path(_places(), params=A4)
    ramp1 = 1 / (1 + math.exp(4 / 3))
    year1 = 2000 * 0.0014219229 * ramp1
    assert out["mature_hazard"][0] == pytest.approx(0.0014219229, rel=1e-6)
    assert out["handbook"][0, 0] == pytest.approx(year1, rel=1e-6)
    assert out["current"][0, 0] == 0.0
    assert out["added"][0, 0] == pytest.approx(0.5933, abs=1e-4)
    assert out["homes"][0, 0] == pytest.approx(year1 * 0.65 * 0.9, rel=1e-6)
    assert out["homes"][0, 0] == pytest.approx(0.3470, abs=1e-4)
    assert out["added"][0, 1] == pytest.approx((2000 - year1) * 0.0014219229 * 0.5, rel=1e-6)
    assert out["added"][0, 1] == pytest.approx(1.4215, abs=1e-4)


def test_all_levers_off_equals_the_baseline():
    places = _places(rule_class=["none", "partial", "handbook"], rule_age=[np.nan, 6.0, 1.0])
    off = adu.central_path(places, enabled=False)
    assert np.all(off["added"] == 0) and np.all(off["homes"] == 0)
    np.testing.assert_array_equal(off["handbook"], off["current"])
    yearly, totals = adu.run(places, 2025, draws=50, enabled=False)
    for name in ("adu_permits_added", "additional_homes"):
        cols = [f"{name}_{s}" for s in ("mean", "p10", "p50", "p90")]
        assert (yearly[cols] == 0).all().all() and (totals[cols] == 0).all().all()


def test_at_most_one_adu_per_parcel():
    """Even with a 90% yearly hazard, cumulative ADUs never exceed the eligible parcels, under either rule."""
    paths = adu.pool_paths([100.0], [0.9], [np.nan], [0.0], [np.nan], 0.5, 0.5, 5)
    assert paths.handbook.sum() <= 100.0 + 1e-9
    assert paths.current.sum() <= 100.0 + 1e-9
    assert np.all(paths.handbook >= 0)
    hm = adu.pool_paths([100.0], [1.0], [np.nan], [0.0], [np.nan], 0.5, 0.5, 5)
    assert hm.handbook.sum() == pytest.approx(100.0, rel=1e-3)  # every parcel used once, never twice


def test_more_profit_never_lowers_uptake():
    rents = list(np.linspace(600, 3500, 60))
    out = adu.central_path(_places(rent=rents))
    total = out["added"].sum(axis=1)
    assert np.all(np.diff(total) >= 0)


def test_handbook_equivalent_rules_add_nothing():
    out = adu.central_path(_places(rule_class="handbook", rule_age=0.5))
    assert np.all(out["added"] == 0)
    assert out["current"].sum() > 0  # the recent reform still ramps up under current rules


def test_partial_rules_get_the_increment_only_by_hand():
    """A long-standing partial rule (age 50 years, ramp ≈ 1): current hazard = 0.3 × h_m. Handbook year 1:
    0.3 h_m + 0.7 h_m × ramp(1). Added in year 1 = 2,000 × 0.7 × h_m × 0.20861 (same pool in year 1)."""
    out = adu.central_path(_places(rule_class="partial", rule_age=50.0))
    hm = out["mature_hazard"][0]
    assert out["current"][0, 0] == pytest.approx(2000 * 0.3 * hm, rel=1e-6)
    assert out["added"][0, 0] == pytest.approx(2000 * 0.7 * hm / (1 + math.exp(4 / 3)), rel=1e-6)


def test_observed_adus_are_never_counted_as_added():
    """If a place already builds ADUs at or above the Handbook hazard, nothing is added (additionality)."""
    hm = adu.central_path(_places())["mature_hazard"][0]
    out = adu.central_path(_places(observed_rate=hm * 1.5))
    assert np.all(out["added"] == 0)
    half = adu.central_path(_places(observed_rate=hm / 2))
    assert 0 < half["added"].sum() < adu.central_path(_places())["added"].sum()


def test_run_ranges_are_ordered_and_flag_extrapolation():
    places = _places(rent=[1100.0, 1800.0], home_value=[260_000.0, 600_000.0], mortgage_rate=[5.0, 5.0])
    yearly, totals = adu.run(places, 2025, draws=200)
    for t in (yearly, totals):
        assert (t["additional_homes_p10"] <= t["additional_homes_p50"]).all()
        assert (t["additional_homes_p50"] <= t["additional_homes_p90"]).all()
    assert totals["outside_calibration"].tolist() == [True, False]
    assert len(yearly) == 2 * 5 and set(yearly["year"]) == set(range(2026, 2031))
    assert "eligible_parcels" in yearly  # denominator kept beside the units


def _reforms(rows):
    cols = [
        "reform_id",
        "jurisdiction_geoid",
        "theme",
        "status",
        "effective_date",
        "end_date",
        "supersedes",
        *adu.RUBRIC,
    ]
    df = pd.DataFrame([tuple(r) + (None,) * (len(cols) - len(r)) for r in rows], columns=cols)
    for c in ("effective_date", "end_date"):
        df[c] = pd.to_datetime(df[c])
    return df


def test_current_rules_classes_amendments_and_state_laws():
    reforms = _reforms(
        [
            # A: owner-occupancy rule, then an amendment that drops it (other fields inherited)
            (
                "A1",
                "100",
                "adu",
                "in_force",
                "2015-01-01",
                None,
                None,
                True,
                True,
                True,
                800,
                "no minimum",
                0,
            ),
            ("A2", "100", "adu", "in_force", "2021-01-01", None, "A1", None, False, None, None, None, None),
            # B: parking required
            (
                "B1",
                "200",
                "adu",
                "in_force",
                "2020-01-01",
                None,
                None,
                True,
                False,
                True,
                900,
                "one space",
                1,
            ),
            # C: nothing local, state law later than the date
            ("S1", "27", "adu", "in_force", "2030-01-01", None, None, True, False, True, 800, "none", 0),
        ]
    )
    out = adu.current_rules(reforms, ["100", "200", "300"], "27", pd.Timestamp("2025-12-31")).set_index(
        "geoid"
    )
    assert out.loc["100", "rule_class"] == "handbook" and out.loc["100", "rule_id"] == "A2"
    assert out.loc["100", "rule_age"] == pytest.approx(
        (pd.Timestamp("2025-12-31") - pd.Timestamp("2021-01-01")).days / 365.25
    )
    assert out.loc["200", "rule_class"] == "partial" and "parking required" in out.loc["200", "rule_note"]
    # D-022: no ADU row in force is unknown, not "none" (the scheduled state law is still noted)
    assert out.loc["300", "rule_class"] == "unknown" and "S1" in out.loc["300", "rule_note"]
    assert pd.isna(out.loc["300", "p_partial"])
    early = adu.current_rules(reforms, ["100"], "27", pd.Timestamp("2018-06-30")).set_index("geoid")
    assert early.loc["100", "rule_class"] == "partial"  # owner-occupancy rule in force then


def test_rule_restrictions_size_cap_and_unknowns():
    fails, unknown = adu.rule_restrictions({"by_right": True, "owner_occ": False, "adu_max_sqft": 500})
    assert fails == ["size cap under 600 sq ft"]
    assert set(unknown) == {"adu_detached_allowed", "parking"}


def test_observed_counts_take_the_larger_source_not_the_sum():
    permits = pd.DataFrame(
        {
            "jurisdiction_geoid": ["M"] * 5 + ["S"],
            "source": ["metc", "metc", "city", "city", "city", "metc"],
            "issue_year": [2020] * 6,
            "building_type_std": ["ADU", "ADU", "ADU", "ADU", "ADU", "SFD"],
            "adu_type": [None] * 6,
        }
    )
    out = adu.observed_adu_counts(permits, 2019, 2022).set_index("geoid")["adu_permits"]
    assert out["M"] == 3 and out["S"] == 0
    assert adu.adu_share_of_one_unit(permits, 2020, 2020) == (5, 6)


def test_forward_runs_use_the_central_rate_and_backtests_use_the_given_rate():
    """No rate given -> every draw uses the central mortgage_rate_forecast (market.yaml; its 2015-25 range is
    a sensitivity, D-030), so a forward run equals a run given the central rate, draw for draw; a given
    (historical) rate is used as is; a sensitivity at the range's low end changes the result."""
    no_rate = _places().drop(columns="mortgage_rate")
    forecast = _places(mortgage_rate=P["mortgage_rate_forecast"])
    assert adu.central_path(no_rate)["added"] == pytest.approx(adu.central_path(forecast)["added"])
    _, t_forward = adu.run(no_rate, 2025, draws=300)
    assert t_forward["mortgage_rate_central"].iloc[0] == P["mortgage_rate_forecast"]
    _, t_hist = adu.run(_places(mortgage_rate=3.0), 2018, draws=300)
    assert t_hist["mortgage_rate_central"].iloc[0] == 3.0
    _, t_fixed = adu.run(forecast, 2025, draws=300)
    assert t_forward["adu_permits_added_mean"].iloc[0] == pytest.approx(
        t_fixed["adu_permits_added_mean"].iloc[0]
    )
    low = adu.specs()["mortgage_rate_forecast"].low
    _, t_low = adu.run(no_rate, 2025, draws=300, params={"mortgage_rate_forecast": low})
    assert t_low["mortgage_rate_central"].iloc[0] == low
    assert t_low["adu_permits_added_mean"].iloc[0] != pytest.approx(
        t_forward["adu_permits_added_mean"].iloc[0]
    )


def _no_slopes(corr: float = 0.0) -> dict:
    """An adu_anchor.yaml with every slope 0: the anchor draws without the judgment-parameter shift."""
    out = {"adu_anchor_info_corr": corr}
    for k in adu.anchor_inputs():
        out[f"anchor_slope_theta__{k}"] = out[f"anchor_slope_alpha__{k}"] = 0.0
    return out


def test_log_sd_from_the_90_percent_interval_by_hand():
    """Anchor 90% interval 0.000453-0.003173: (ln 0.003173 − ln 0.000453) / (2 × 1.644854) = 0.5917."""
    s = adu.specs()["adu_mature_hazard_ref"]
    assert adu.log_sd(s) == pytest.approx((math.log(0.003173) - math.log(0.000453)) / 3.289708, rel=1e-6)
    assert adu.log_sd(s) == pytest.approx(0.5917, abs=1e-4)


def test_anchor_draws_have_their_median_at_the_estimate():
    """D-030: the fitted anchor and place-effect variance are lognormal with median at the estimate (before
    the judgment shift), not triangular(low, central, high), whose median for the anchor is ~1.47e-3, 41%
    above the estimate 1.038e-3."""
    spec = adu.specs()
    sets = adu.draw_params(20_000, 7, _no_slopes())
    theta = np.array([p["adu_mature_hazard_ref"] for p in sets])
    alpha = np.array([p["adu_place_effect_variance"] for p in sets])
    t, a = spec["adu_mature_hazard_ref"], spec["adu_place_effect_variance"]
    assert np.median(theta) == pytest.approx(t.value, rel=0.02)
    assert np.std(np.log(theta)) == pytest.approx(adu.log_sd(t), rel=0.03)
    assert np.median(alpha) == pytest.approx(a.value, rel=0.02)
    assert np.percentile(theta, 5) == pytest.approx(t.value * math.exp(-1.644854 * adu.log_sd(t)), rel=0.05)
    old = np.random.default_rng(7).triangular(t.low, t.value, t.high, 20_000)
    assert np.median(old) > 1.4 * t.value  # the bias D-030 removes


def test_anchor_shifts_with_the_judgment_parameters_it_was_fitted_at_by_hand():
    """With one slope g = −2 on adu_feasibility_dispersion (σ), log θ_d = (the no-slope draw) − 2 (σ_d − 0.5),
    draw for draw; so a draw with σ = 0.6 has θ e^−0.2 = 0.8187 times the no-slope draw. Every other parameter
    is drawn identically. Under the configured slopes the median anchor stays within 10% of the estimate."""
    base = adu.draw_params(500, 3, _no_slopes())
    anchor = _no_slopes() | {"anchor_slope_theta__adu_feasibility_dispersion": -2.0}
    shifted = adu.draw_params(500, 3, anchor)
    for b, s in zip(base, shifted, strict=True):
        sigma = s["adu_feasibility_dispersion"]
        assert sigma == b["adu_feasibility_dispersion"]
        assert s["adu_mature_hazard_ref"] == pytest.approx(
            b["adu_mature_hazard_ref"] * math.exp(-2.0 * (sigma - 0.5))
        )
        assert s["adu_place_effect_variance"] == pytest.approx(b["adu_place_effect_variance"])
    real = np.array([p["adu_mature_hazard_ref"] for p in adu.draw_params(5_000, 3)])
    assert np.median(real) == pytest.approx(adu.specs()["adu_mature_hazard_ref"].value, rel=0.10)


def test_stress_ranges_are_held_at_central_in_the_draws():
    """The mortgage-rate stress range and the shared extrapolation-noise share are sensitivities (D-030)."""
    sets = adu.draw_params(200, 1)
    for k in adu.SENSITIVITY:
        assert {p[k] for p in sets} == {adu.specs()[k].value}


def test_extrapolation_noise_keeps_each_place_standard_normal_and_shares_by_hand():
    """share 1: one z per draw (every place equal); share 0.5: correlation 0.5 between places; every column
    mean 0, SD 1, so `hazard.widen` keeps each place's mean and spread."""
    z1 = adu.extrapolation_noise(4, 3, 1.0, 0)
    assert np.all(z1 == z1[:, :1])
    z = adu.extrapolation_noise(40_000, 2, 0.5, 0)
    assert z.mean(axis=0) == pytest.approx([0, 0], abs=0.02)
    assert z.std(axis=0) == pytest.approx([1, 1], abs=0.02)
    assert np.corrcoef(z.T)[0, 1] == pytest.approx(0.5, abs=0.02)


def test_shared_extrapolation_noise_widens_state_intervals():
    """30 identical places far below the calibration range (rent $700), every other parameter held at its
    central value and place effects off, so only the extrapolation noise varies: with the noise
    shared (D-030) the state's P10-P90 of added permits is much wider than with independent noise per place,
    which averages out over the 30 places; the mean is unchanged (widening keeps the mean)."""
    places = _places(rent=[700.0] * 30, geoid=[f"P{i}" for i in range(30)]).assign(state="MN")
    out = {}
    for share in (0.0, 1.0):
        fixed = adu.central_params() | {
            "adu_extrapolation_shared_share": share,
            "adu_place_effect_variance": 0,
        }
        _, _, summ = adu.run(places, 2025, draws=600, summary_by="state", params=fixed)
        out[share] = summ[(summ["outcome"] == "adu_permits_added") & (summ["period"] == "2026-2030")].iloc[0]
    width = {k: v["p90"] - v["p10"] for k, v in out.items()}
    assert width[1.0] > 1.5 * width[0.0]
    assert out[1.0]["mean"] == pytest.approx(out[0.0]["mean"], rel=0.15)


def test_an_explicit_no_adu_row_is_none_and_a_state_law_still_wins():
    # "adus_per_lot = 0": the city's code allows no ADUs. It must read as "none", not as a partial rule.
    reforms = _reforms(
        [
            ("N1", "400", "adu", "in_force", "2010-01-01", None, None, True, False, True, 800, "none", 0, 0),
            ("S1", "27", "adu", "in_force", "2024-01-01", None, None, True, False, True, 800, "none", 0, 1),
        ]
    )
    before = adu.current_rules(reforms, ["400"], "27", pd.Timestamp("2020-06-30")).set_index("geoid")
    assert before.loc["400", "rule_class"] == "none" and before.loc["400", "rule_id"] == "N1"
    assert "no ADUs allowed" in before.loc["400", "rule_note"] and pd.isna(before.loc["400", "rule_age"])
    after = adu.current_rules(reforms, ["400"], "27", pd.Timestamp("2025-12-31")).set_index("geoid")
    assert after.loc["400", "rule_class"] == "handbook" and after.loc["400", "rule_id"] == "S1"


def test_scenario_units_never_share_a_parcel():
    """D-020 by hand: remainders C (1,000) and D (500); local-only place L (300, two thirds in C) and an
    ordinary BPS place P (400). Units become C 800, D 400, L 300, P 400: the statewide eligible total is the
    sum over non-overlapping units, 1,900, not 2,200."""
    places = pd.DataFrame(
        {
            "geoid": ["C", "D", "L", "P"],
            "kind": ["county_unincorporated", "county_unincorporated", "place", "place"],
            "county_geoid": ["C", "D", "C", "D"],
            "eligible_parcels": [1000.0, 500.0, 300.0, 400.0],
        }
    )
    juris = places[["geoid", "kind", "county_geoid"]].assign(in_bps=[True, True, False, True])
    shares = pd.DataFrame({"place_geoid": ["L", "L"], "county_geoid": ["C", "D"], "share": [2 / 3, 1 / 3]})
    out = adu.non_overlapping(places, juris, shares).set_index("geoid")
    assert out["eligible_parcels"].to_dict() == pytest.approx({"C": 800, "D": 400, "L": 300, "P": 400})
    assert out["eligible_parcels"].sum() == pytest.approx(1900)
    assert out["overlap_removed"].sum() == pytest.approx(300)
    # a remainder counted from a parcel roll holds no place's parcels: nothing is subtracted from it
    rolls = adu.non_overlapping(places.assign(denominator_source="parcels"), juris, shares)
    assert rolls["eligible_parcels"].sum() == pytest.approx(2200) and rolls["overlap_removed"].sum() == 0
    clipped = adu.non_overlapping(places.assign(eligible_parcels=[100.0, 500.0, 300.0, 400.0]), juris, shares)
    assert clipped.set_index("geoid").loc["C", "eligible_parcels"] == 0 and clipped["overlap_clipped"].any()


def test_uncoded_place_takes_its_band_prior_by_hand():
    """D-022: 5 coded places in a state's band, 2 with a restricted rule ('other') and 3 Handbook-equivalent
    -> an uncoded place in that band is restricted with probability 0.4, and about 40% of its draws are."""
    zeros = [0.0] * 5
    coded = pd.DataFrame(
        {
            "state": ["MN"] * 5,
            "population": [20_000] * 5,
            "p_none": zeros,
            "p_owner": zeros,
            "p_other": [1, 1, 0, 0, 0.0],
            "p_both": zeros,
            "p_handbook": [0, 0, 1, 1, 1.0],
        }
    )
    edges = (10_000, 50_000)
    priors = adu.rule_priors(coded, edges, min_count=5)
    mid = priors.set_index(["state", "band"]).loc[("MN", 1)]
    assert (mid["p_none"], mid["p_other"], mid["p_handbook"]) == pytest.approx((0, 0.4, 0.6))
    assert mid["source"] == "state and band" and mid["n_coded"] == 5
    small = priors.set_index(["state", "band"]).loc[("MN", 0)]
    assert small["source"] == "state, all bands" and small["p_other"] == pytest.approx(0.4)
    place = pd.DataFrame({"geoid": ["U"], "state": ["MN"], "population": [30_000], "rule_class": ["unknown"]})
    place = place.assign(**{c: np.nan for c in adu.P_COLS})
    filled = adu.apply_priors(place, priors, edges)
    assert filled.loc[0, "p_other"] == pytest.approx(0.4)
    many = pd.concat([filled] * 20_000, ignore_index=True)
    c, idx, sampled = adu.draw_rule_share(many, P, np.random.default_rng(0))
    assert (idx == adu.TYPES.index("other")).mean() == pytest.approx(0.4, abs=0.01) and sampled.all()
    assert set(np.unique(c)) == {P["adu_partial_rule_share"], 1.0}


def test_rule_types_and_graded_shares_by_hand():
    """Owner occupancy alone -> 'owner' (c = m_o); parking -> 'other' (m_x); both -> m_o × m_x.
    Owner known to fail and parking blank with P 0.25 -> owner 0.75, both 0.25."""
    assert adu.type_of({"owner_occ"}) == "owner" and adu.type_of({"parking"}) == "other"
    assert adu.type_of({"owner_occ", "by_right"}) == "both" and adu.type_of(set()) == "handbook"
    v = adu.type_distribution(["owner_occ"], ["parking"], {"parking": 0.25})
    assert dict(zip(adu.TYPES, v, strict=True)) == pytest.approx(
        {"none": 0, "owner": 0.75, "other": 0, "both": 0.25, "handbook": 0}
    )
    params = dict(P, adu_owner_occupancy_share=0.5, adu_partial_rule_share=0.3)
    assert adu.c_values(params) == pytest.approx([0, 0.5, 0.3, 0.15, 1])


def test_rule_coverage_by_hand():
    """D-021: 4 single-family parcels, zones R-1 (3) and R-2; lot minimum 6,000 met by 2 of the R-1 parcels ->
    covers 2 / 4. No zones or minimum: citywide 1, a limited area (overlay) the judgment share."""
    parcels = pd.DataFrame({"zoning_raw": ["R-1", "R1", "r-1", "R-2"], "lot_sqft": [7000, 6500, 5000, 9000]})
    params = adu.central_params()
    rule = {"coverage_zones": "R-1", "min_lot_sqft": 6000.0, "coverage": "R-1 only"}
    assert adu.rule_coverage(rule, parcels, params)[0] == pytest.approx(0.5)
    assert adu.rule_coverage({"coverage": "Citywide"}, None, params) == (1.0, "citywide")
    limited = adu.rule_coverage({"coverage": "Only inside an ADU overlay district"}, None, params)
    assert limited[0] == params["adu_rule_limited_coverage_share"]
    no_zoning = adu.rule_coverage({"coverage_zones": "SF-3"}, parcels.drop(columns="zoning_raw"), params)
    assert no_zoning[0] == params["adu_rule_zoned_coverage_share"]
    v = adu.apply_coverage(np.array([0, 0, 0, 0, 1.0]), 0.75)
    assert v == pytest.approx([0.25, 0, 0, 0, 0.75])


def test_a_blank_field_is_never_read_as_unrestrictive():
    """A row that passes every coded condition but leaves parking blank is Handbook only with probability
    1 − P(parking restricts). By hand, coded parking: 1 of 4 rules requires it -> P = 0.25 ->
    (0, 0.25, 0.75)."""
    reforms = _reforms(
        [
            ("R1", "500", "adu", "in_force", "2020-01-01", None, None, True, False, True, 800, None, None),
            (
                "K1",
                "601",
                "adu",
                "in_force",
                "2020-01-01",
                None,
                None,
                True,
                False,
                True,
                800,
                "one space required",
                None,
            ),
            ("K2", "602", "adu", "in_force", "2020-01-01", None, None, True, False, True, 800, "none", 0),
            ("K3", "603", "adu", "in_force", "2020-01-01", None, None, True, False, True, 800, "none", 0),
            ("K4", "604", "adu", "in_force", "2020-01-01", None, None, True, False, True, 800, "none", 0),
        ]
    ).assign(state="MN")
    as_of = pd.Timestamp("2025-12-31")
    counts = adu.field_restrict_counts(reforms, as_of)
    probs = adu.field_probabilities(counts, "MN", min_count=4)
    assert probs["parking"] == pytest.approx(0.25)
    out = adu.current_rules(reforms, ["500"], "27", as_of, probs).set_index("geoid")
    assert out.loc["500", "rule_class"] == "uncertain"
    assert out.loc["500", ["p_none", "p_partial", "p_handbook"]].tolist() == pytest.approx([0, 0.25, 0.75])
    assert out.loc["500", "p_other"] == pytest.approx(0.25)  # parking is an 'other' restriction
    assert "parking" in out.loc["500", "unknown_fields"]
    # unknown parking text is unknown too, never "not required"
    assert "parking" in adu.rule_restrictions({"parking": "see code", "by_right": True})[1]


def test_central_path_uses_the_expected_rule_share():
    """E[c] = Σ P(type) c(type): other 0.4, Handbook 0.6, m_x = 0.3 -> c = 0.72 (rule long in force)."""
    p = _places(rule_class="unknown", rule_age=50.0).assign(
        p_none=0.0, p_owner=0.0, p_other=0.4, p_both=0.0, p_handbook=0.6
    )
    mix = adu.central_path(p)
    hand = adu.central_path(_places(rule_class="handbook", rule_age=50.0))
    hm = mix["mature_hazard"][0]
    assert mix["current"][0, 0] == pytest.approx(2000 * 0.72 * hm, rel=1e-6)
    assert mix["added"][0, 0] == pytest.approx(2000 * 0.28 * hm / (1 + math.exp(4 / 3)), rel=1e-6)
    assert hand["added"].sum() == 0


def test_state_summary_sums_draws_over_places():
    """Means add up: the state's mean equals the sum of its places' means, per year and over five years; the
    state's P10-P90 comes from summed draws, so it is not the sum of the places' P10s and P90s."""
    places = _places(rent=[1100.0, 1500.0, 1900.0], eligible_parcels=[2000.0, 5000.0, 800.0]).assign(
        state="MN"
    )
    yearly, totals, summary = adu.run(places, 2025, draws=300, summary_by="state")
    five = summary[(summary["outcome"] == "additional_homes") & (summary["period"] == "2026-2030")].iloc[0]
    assert five["mean"] == pytest.approx(totals["additional_homes_mean"].sum())
    y1 = summary[(summary["outcome"] == "additional_homes") & (summary["period"] == "2026")].iloc[0]
    assert y1["mean"] == pytest.approx(yearly.loc[yearly["year"] == 2026, "additional_homes_mean"].sum())
    assert five["p10"] <= five["p50"] <= five["p90"]
    # percentiles of the summed draws, not sums of the places' percentiles (either can be larger)
    assert five["p90"] != pytest.approx(totals["additional_homes_p90"].sum())
