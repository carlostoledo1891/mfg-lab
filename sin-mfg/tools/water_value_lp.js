/* water_value_lp.js — the deterministic bounded-reservoir dispatch LP, solved
   exactly and CERTIFIED. This is Theorem B1-det(b) of SIN_MFG_Model_Spec_v0.3
   §B made a finished theorem in discrete time: the spec's continuous-time
   version leans on state-constrained PMP with hypotheses "to verify"
   (constraint qualification, normality); the discrete-time problem the
   benchmark actually runs is a FINITE LP, where strong duality and KKT need
   no qualification at all. The proof is the certificate set below.

   Problem (hourly grid, the benchmark's own discretization):

     max Σ_t ϖ_t h_t   s.t.  R_t = R_{t−1} + I_t − h_t   (t = 1..T)
                             0 ≤ R_t ≤ R̄  (t < T),  R_T = R_end  (⇔ Σh = budget)
                             0 ≤ h_t ≤ h̄

   KKT (= LP optimality, necessary and sufficient, no CQ):
     · stationarity in h_t:  ϖ_t − w_t + μ_t − ν_t = 0  ⇒  the Hotelling
       trichotomy against w_t  (h=0 ⇒ ϖ≤w · interior ⇒ ϖ=w · h=h̄ ⇒ ϖ≥w);
     · stationarity in R_t:  w_{t+1} = w_t − α_t + β_t  with α⟂R_t, β⟂(R̄−R_t)
       ⇒  **w is piecewise constant, jumping only at stock-binding events:
       UP across a full-reservoir event (β>0 at R=R̄ — water cheap before,
       scarce after), DOWN across an empty event (α>0 at R=0)**;
     · zero duality gap:  Σϖ_t h_t = w_1R_0 − w_TR_end + Σw_tI_t
                          + Σ_{t<T} R̄·max(w_{t+1}−w_t, 0) + Σ_t h̄·max(ϖ_t−w_t, 0).

   Solver: the house flow→polish pattern (Wardrop polish, mfglab). An
   active-set (pinning) loop proposes which stock constraints bind; each
   unpinned segment is then exactly the INTERIOR problem of Theorem B1-det(a)
   (constant w = root of the segment budget map, greedy/KKT fill); pins are
   added at the worst stock violation and removed when their jump has the
   wrong dual sign. The loop is a heuristic; the CERTIFICATE is not — primal
   feasibility + trichotomy + jump signs + complementary slackness + zero gap
   PROVE optimality of the returned point regardless of how it was found.
   Battery: sin-mfg/tests/test-water-value.js (in `make check`). */
'use strict';

const TOL = 1e-9;

/* exact interior solve on one segment (Theorem B1-det(a)): hours `idx`,
   release budget E, cap hbar. Returns {h (per hour of idx), w, marginal}. */
function segmentSolve(prices, idx, E, hbar) {
  const S = idx.slice().sort((a, b) => prices[b] - prices[a]);
  const n = S.length;
  if (E < -TOL || E > n * hbar + TOL) return null;           // pin set infeasible
  const h = new Map(S.map(t => [t, 0]));
  const nFull = Math.min(n, Math.floor(E / hbar + 1e-12));
  for (let k = 0; k < nFull; k++) h.set(S[k], hbar);
  const rem = E - nFull * hbar;
  let w, marginal = -1;
  if (rem > TOL && nFull < n) {                              // generic: marginal hour
    marginal = S[nFull];
    h.set(marginal, rem);
    w = prices[marginal];
  } else if (nFull === 0) {                                  // all off: w above all prices
    w = prices[S[0]] + 1;
  } else if (nFull === n) {                                  // all full: w below all prices
    w = prices[S[n - 1]] - 1;
  } else {                                                   // exact multiple: KKT interval
    w = 0.5 * (prices[S[nFull]] + prices[S[nFull - 1]]);
  }
  return { h, w, marginal };
}

/* solve the bounded-reservoir LP. prices/inflows are arrays of length T
   (hour t = index+1 conceptually); returns primal, duals, pins and the full
   certificate set. */
function solveReservoirLP({ prices, inflows, R0, Rend, Rbar, hbar }) {
  const T = prices.length;
  /* pins: Map time t (1..T-1) -> 0 | Rbar. Endpoints are fixed pins. */
  const pins = new Map();
  let sol = null;
  for (let iter = 0; iter < 6 * T + 10; iter++) {
    /* segment boundaries: 0 and T plus pinned times, ascending */
    const cuts = [0, ...[...pins.keys()].sort((a, b) => a - b), T];
    const Rat = t => (t === 0 ? R0 : t === T ? Rend : pins.get(t));
    const h = new Float64Array(T + 1);                        // 1-indexed
    const wSeg = new Float64Array(T + 1);
    let infeasible = false;
    for (let s = 0; s < cuts.length - 1; s++) {
      const a = cuts[s], b = cuts[s + 1];
      const idx = []; let cumI = 0;
      for (let t = a + 1; t <= b; t++) { idx.push(t); cumI += inflows[t - 1]; }
      const E = Rat(a) - Rat(b) + cumI;
      const seg = segmentSolve(prices.map((p, i) => p), idx.map(t => t - 1), E, hbar);
      if (!seg) { infeasible = true; break; }
      for (const t of idx) h[t] = seg.h.get(t - 1);
      for (const t of idx) wSeg[t] = seg.w;
    }
    if (infeasible) return { ok: false, reason: 'pin set infeasible', pins: [...pins] };
    /* trajectory + violation scan */
    const R = new Float64Array(T + 1); R[0] = R0;
    for (let t = 1; t <= T; t++) R[t] = R[t - 1] + inflows[t - 1] - h[t];
    let worst = 0, wt = -1, wbound = 0;
    for (let t = 1; t < T; t++) {
      if (pins.has(t)) continue;
      if (-R[t] > worst + TOL) { worst = -R[t]; wt = t; wbound = 0; }
      if (R[t] - Rbar > worst + TOL) { worst = R[t] - Rbar; wt = t; wbound = Rbar; }
    }
    if (wt >= 0) { pins.set(wt, wbound); continue; }
    /* dual-sign scan: jump across pin t is w(seg after) − w(seg before);
       must be ≥0 at R̄-pins, ≤0 at 0-pins; else unpin (wrong active set) */
    let unpinned = false;
    for (const [t, bound] of [...pins]) {
      const jump = wSeg[t + 1] - wSeg[t];
      if ((bound === Rbar && jump < -TOL) || (bound === 0 && jump > TOL)) {
        pins.delete(t); unpinned = true; break;
      }
    }
    if (unpinned) continue;
    sol = { h, R, wSeg, cuts };
    break;
  }
  if (!sol) return { ok: false, reason: 'active-set loop did not settle', pins: [...pins] };

  /* ------- the certificate set (this is the proof; the loop was a guess) ------- */
  const { h, R, wSeg } = sol;
  let cert = {};
  /* primal feasibility */
  let dynErr = 0, boxErr = 0;
  for (let t = 1; t <= T; t++) {
    dynErr = Math.max(dynErr, Math.abs(R[t] - (R[t - 1] + inflows[t - 1] - h[t])));
    boxErr = Math.max(boxErr, -h[t], h[t] - hbar);
    if (t < T) boxErr = Math.max(boxErr, -R[t], R[t] - Rbar);
  }
  cert.dynErr = dynErr;
  cert.boxErr = Math.max(0, boxErr);
  cert.termErr = Math.abs(R[T] - Rend);
  /* trichotomy (strict sides) */
  let tri = 0;
  for (let t = 1; t <= T; t++) {
    if (prices[t - 1] > wSeg[t] + TOL && h[t] < hbar - TOL) tri++;
    if (prices[t - 1] < wSeg[t] - TOL && h[t] > TOL) tri++;
  }
  cert.trichotomyViolations = tri;
  /* dual feasibility + complementary slackness of the jumps */
  let jumpSignErr = 0, compSlack = 0;
  for (let t = 1; t < T; t++) {
    const jump = wSeg[t + 1] - wSeg[t];
    if (Math.abs(jump) > TOL) {
      const atTop = Math.abs(R[t] - Rbar) < TOL, atBot = Math.abs(R[t]) < TOL;
      if (!atTop && !atBot) compSlack = Math.max(compSlack, Math.abs(jump)); // jump w/o binding
      if (jump > 0 && !atTop) jumpSignErr = Math.max(jumpSignErr, jump);     // up needs R=R̄
      if (jump < 0 && !atBot) jumpSignErr = Math.max(jumpSignErr, -jump);    // down needs R=0
    }
  }
  cert.jumpSignErr = jumpSignErr;
  cert.compSlack = compSlack;
  /* zero duality gap */
  let rev = 0, D = wSeg[1] * R0 - wSeg[T] * Rend;
  for (let t = 1; t <= T; t++) {
    rev += prices[t - 1] * h[t];
    D += wSeg[t] * inflows[t - 1] + hbar * Math.max(prices[t - 1] - wSeg[t], 0);
    if (t < T) D += Rbar * Math.max(wSeg[t + 1] - wSeg[t], 0);
  }
  cert.revenue = rev;
  cert.dualityGap = Math.abs(rev - D);
  cert.gapRel = cert.dualityGap / Math.max(1, Math.abs(rev));
  /* structure receipts */
  cert.bindingEvents = [...pins].map(([t, b]) => ({ t, bound: b === 0 ? 'empty' : 'full' }));
  cert.wLevels = [...new Set([...wSeg.slice(1)].map(x => +x.toFixed(12)))].length;

  return { ok: true, h: [...h].slice(1), R: [...R], w: [...wSeg].slice(1), pins: [...pins], cert };
}

module.exports = { solveReservoirLP, segmentSolve, TOL };

if (require.main === module) {
  /* self-demo: an instance engineered to hit both barriers */
  const T = 24;
  const bump = (t, c, s) => Math.exp(-0.5 * ((t - c) / s) ** 2);
  const prices = Array.from({ length: T }, (_, i) => 0.6 + 0.8 * bump(i, 4, 1.6) + 0.9 * bump(i, 19, 2.0));
  const inflows = Array.from({ length: T }, (_, i) => 0.10 + 0.55 * bump(i, 11, 2.2));
  const r = solveReservoirLP({ prices, inflows, R0: 0.5, Rend: 0.4, Rbar: 1.0, hbar: 0.4 });
  console.log('water_value_lp self-demo:', r.ok ? 'solved' : r.reason);
  if (r.ok) {
    console.log('  binding events :', JSON.stringify(r.cert.bindingEvents));
    console.log('  w levels       :', r.cert.wLevels, ' (piecewise constant)');
    console.log('  duality gap    :', r.cert.gapRel.toExponential(2), '(zero ⇒ certified optimal)');
    console.log('  trichotomy     :', r.cert.trichotomyViolations, 'violations');
  }
  console.log('certificates live in tests/test-water-value.js — run that, not this.');
}
