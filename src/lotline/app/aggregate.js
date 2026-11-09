// SPDX-License-Identifier: Apache-2.0
// The only model arithmetic in the browser (WS-APP brief; HANDOFF 2026-11-06): re-multiply the engine's
// exported draws and take percentiles. It mirrors lotline.model.aggregate.homes_from_draws line for line;
// tests/app/test_aggregate_parity.py runs this file under node against that function on the same fixture.
//
//   eligible = Σ tiers; pencils = eligible × pencil_out_share; permits = pencils × theta × (1 − overlap);
//   homes in place = permits × completion_factor × net_new_share;
//   net statewide = homes in place × (1 − displacement_share). A null overlap_share counts as 0.
//
// PROVISIONAL (Ben, 2026-11-06): how a slider moves an assumption is a working choice, to be revisited after
// feedback on the app; the parity test holds whatever rule is here to model/aggregate.py.
// A slider "shifts" one factor to a point q in its own range: every draw's value is multiplied by
// P_q / P50 of that factor across the draws, then kept within [0, 1] (every factor is a share or a five-year
// probability). Scaling, rather than setting every draw to one value, keeps the engine's joint structure:
// θ is back-solved per draw, so it moves against pencil-out, and pinning it alone would widen the range
// artificially. At q = 50 (the slider's centre) the result is exactly the engine's draws.
// By hand: draws with theta 0.02 and 0.04 (all else as in aggregate.py's example: 1,000 eligible, pencil-out
// 0.5, completion 1.0, net-new 0.6, displacement 0.25): P50 = 0.03, P100 = 0.04, so theta shifted to q = 100
// scales by 4/3 -> 0.02667 and 0.05333 -> 13.33 and 26.67 permits, 8 and 16 homes in place.
(function (root) {
  "use strict";
  const TIERS = ["eligible_tier1", "eligible_tier2", "eligible_tier3"];
  const FACTORS = ["theta", "pencil_out_share", "completion_factor", "net_new_share", "displacement_share"];

  // numpy.percentile's default ("linear"): position (n − 1)·q/100 between the sorted neighbours.
  function percentile(values, q) {
    const a = Float64Array.from(values).sort();
    if (!a.length) return NaN;
    const pos = ((a.length - 1) * q) / 100;
    const lo = Math.floor(pos), hi = Math.ceil(pos);
    return a[lo] + (a[hi] - a[lo]) * (pos - lo);
  }

  const num = (v) => (v === null || v === undefined ? NaN : Number(v));

  // The multiplier a shift to q applies to one factor: P_q / P50 across the draws (1 when P50 is 0).
  function shiftScale(draws, col, q) {
    const vals = draws.map((d) => num(d[col]));
    const mid = percentile(vals, 50);
    return mid > 0 ? percentile(vals, q) / mid : 1;
  }

  // shifts: {column: q} for columns in FACTORS. Returns per-draw arrays like homes_from_draws.
  function homesFromDraws(draws, shifts) {
    shifts = shifts || {};
    const scale = {};
    for (const [col, q] of Object.entries(shifts)) {
      if (!FACTORS.includes(col)) throw new Error(`cannot shift ${col}`);
      scale[col] = shiftScale(draws, col, q);
    }
    const get = (d, col) => (col in scale ? Math.min(1, Math.max(0, num(d[col]) * scale[col])) : num(d[col]));
    const out = { legal: [], pencils: [], permits_added: [], homes_in_place: [], homes_net_statewide: [] };
    for (const d of draws) {
      const eligible = TIERS.reduce((s, c) => s + num(d[c]), 0);
      const pencils = eligible * get(d, "pencil_out_share");
      const ov = num(d.overlap_share);
      const permits = pencils * get(d, "theta") * (1 - (Number.isNaN(ov) ? 0 : ov));
      const inPlace = permits * get(d, "completion_factor") * get(d, "net_new_share");
      const net = inPlace * (1 - get(d, "displacement_share"));
      out.legal.push(eligible);
      out.pencils.push(pencils);
      out.permits_added.push(permits);
      out.homes_in_place.push(inPlace);
      out.homes_net_statewide.push(net);
    }
    return out;
  }

  const range = (a) => ({ p10: percentile(a, 10), p50: percentile(a, 50), p90: percentile(a, 90) });

  // P10/P50/P90 of every outcome for one scenario's draws (sorted by draw), with optional shifts.
  function summarize(draws, shifts) {
    const sorted = [...draws].sort((x, y) => x.draw - y.draw);
    const h = homesFromDraws(sorted, shifts);
    const out = {};
    for (const [k, v] of Object.entries(h)) out[k] = range(v);
    return out;
  }

  // Share of housing need, as aggregate.share_of_need: the net statewide range over the central denominator,
  // and the median over the denominator's high and low (a `results_need` row gives the denominators).
  function shareOfNeed(net, need) {
    return {
      share_p10: net.p10 / need.denominator,
      share_p50: net.p50 / need.denominator,
      share_p90: net.p90 / need.denominator,
      share_p50_at_need_high: net.p50 / need.denominator_high,
      share_p50_at_need_low: net.p50 / need.denominator_low,
    };
  }

  // Tornado (section 3): the outcome's P50 with each factor shifted to its own low (q = 10) and high (q = 90)
  // while the others stay at the engine, sorted by the size of the swing. Only `summarize` is used.
  function tornado(draws, outcome, factors, lo, hi) {
    lo = lo === undefined ? 10 : lo;
    hi = hi === undefined ? 90 : hi;
    const base = summarize(draws)[outcome].p50;
    const rows = (factors || FACTORS).map((f) => ({
      factor: f,
      low: summarize(draws, { [f]: lo })[outcome].p50,
      high: summarize(draws, { [f]: hi })[outcome].p50,
    }));
    rows.sort((a, b) => Math.abs(b.high - b.low) - Math.abs(a.high - a.low));
    return { base, rows };
  }

  // The five-year window's label, read from the bundle rather than worked out from meta (D-061): the
  // projection starts after a baseline-only lead year, so origin 2025 gives 2027-2031, not 2026-2030, and
  // `totals` already carries that window as its multi-year `period` ("2027-2031"). Returns "2027–2031"
  // (en dash), or null when no multi-year row is present, so the page never prints a window it cannot see.
  function windowLabel(bundle) {
    const row = ((bundle && bundle.totals) || []).find((r) => /^\d{4}-\d{4}$/.test(String(r.period)));
    return row ? String(row.period).replace("-", "\u2013") : null;
  }

  const api = { TIERS, FACTORS, percentile, shiftScale, homesFromDraws, summarize, shareOfNeed, tornado, windowLabel };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.LotlineAggregate = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
