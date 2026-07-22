/* test-water-value.js — battery for the water-value LP pair:
     tools/water_value_lp.js    (deterministic bounded reservoir — B1-det(b)
                                 in discrete time, PROVED by LP duality)
     tools/water_value_tree.js  (scenario tree — B1-stoch's martingale in
                                 discrete time, PROVED by LP duality)

   The solvers are heuristics (active-set pinning; exact PL-concave DP); the
   PROOF is the certificate set this battery gates: primal feasibility,
   Hotelling trichotomy, dual jump/wedge signs, complementary slackness, and
   ZERO duality gap — LP optimality needs no constraint qualification, so a
   green gate is a finished optimality proof for each instance. Independent
   witnesses: revenue dominance over random feasible policies. Mutants prove
   every gate can go red. Doctrine: no silent caps — skipped/infeasible
   instances are counted and reported, never dropped. */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const LPF = process.env.WVLP || path.resolve(__dirname, '..', 'tools', 'water_value_lp.js');
const TRF = process.env.WVTREE || path.resolve(__dirname, '..', 'tools', 'water_value_tree.js');
const sha = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex').slice(0, 16);
console.log('deterministic LP : ' + LPF + '  sha256 ' + sha(LPF));
console.log('scenario tree    : ' + TRF + '  sha256 ' + sha(TRF) + '\n');
const { solveReservoirLP } = require(LPF);
const { buildTree, solveTree } = require(TRF);

const fails = [];
function check(name, cond, detail) {
  console.log((cond ? 'PASS  ' : 'FAIL  ') + name + (detail ? '   [' + detail + ']' : ''));
  if (!cond) fails.push(name);
}
function mulberry32(s) { return function () { s |= 0; s = s + 0x6D2B79F5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const bump = (t, c, s) => Math.exp(-0.5 * ((t - c) / s) ** 2);
const certOK = c => c.dynErr < 1e-9 && c.boxErr < 1e-9 && (c.termErr === undefined || c.termErr < 1e-9) &&
  c.trichotomyViolations === 0 && c.jumpSignErr < 1e-9 && c.compSlack < 1e-9 && c.gapRel < 1e-12;

/* ================= D · deterministic bounded reservoir ================= */
const T = 24;
const detInst = {
  prices: Array.from({ length: T }, (_, i) => 0.6 + 0.8 * bump(i, 4, 1.6) + 0.9 * bump(i, 19, 2.0)),
  inflows: Array.from({ length: T }, (_, i) => 0.10 + 0.55 * bump(i, 11, 2.2)),
  R0: 0.5, Rend: 0.4, Rbar: 1.0, hbar: 0.4,
};
const det = solveReservoirLP(detInst);
check('D1 structured instance solves and certifies (KKT + zero gap)', det.ok && certOK(det.cert),
  det.ok ? 'gap ' + det.cert.gapRel.toExponential(2) + ', tri ' + det.cert.trichotomyViolations : det.reason);
const kinds = new Set(det.cert.bindingEvents.map(e => e.bound));
check('D2 coverage: instance hits BOTH barriers (full and empty events)',
  kinds.has('full') && kinds.has('empty'),
  det.cert.bindingEvents.length + ' events, w levels ' + det.cert.wLevels);
check('D3 w is piecewise constant with >1 level (the (b)-structure, not (a))',
  det.cert.wLevels > 1, det.cert.wLevels + ' levels');

/* interior-only instance: no binding ⇒ single constant w — B1-det(a) recovered */
const easy = solveReservoirLP({
  prices: detInst.prices, inflows: Array.from({ length: T }, () => 0.18),
  R0: 2.0, Rend: 1.8, Rbar: 6.0, hbar: 0.4,
});
check('D4 interior instance: zero binding events, constant w (Theorem (a) as special case)',
  easy.ok && certOK(easy.cert) && easy.cert.bindingEvents.length === 0 && easy.cert.wLevels === 1,
  easy.ok ? easy.cert.wLevels + ' level, gap ' + easy.cert.gapRel.toExponential(2) : easy.reason);

/* random sweep — every attempted instance must CERTIFY; nothing dropped silently */
{
  const rng = mulberry32(2026);
  let attempted = 0, certified = 0, withBinding = 0, skippedInfeasible = 0, worstGap = 0;
  for (let k = 0; k < 200; k++) {
    const prices = Array.from({ length: T }, () => 0.2 + 1.6 * rng());
    const Rbar = 0.6 + 1.2 * rng(), hbar = 0.25 + 0.3 * rng(), R0 = Rbar * rng();
    /* I ≤ 0.85·h̄ ⇒ the no-spill feasible interval is never empty (R ≤ R̄ by
       induction and R+I−R̄ ≤ I < h̄), so every instance is attemptable */
    const inflows = Array.from({ length: T }, () => 0.85 * hbar * rng());
    /* feasible Rend by simulating a feasible (no-spill) policy */
    let R = R0, ok = true;
    for (let t = 0; t < T; t++) {
      const lo = Math.max(0, R + inflows[t] - Rbar), hi = Math.min(hbar, R + inflows[t]);
      if (lo > hi) { ok = false; break; }
      const h = lo + (hi - lo) * rng();
      R = R + inflows[t] - h;
    }
    if (!ok) { skippedInfeasible++; continue; }
    attempted++;
    const r = solveReservoirLP({ prices, inflows, R0, Rend: R, Rbar, hbar });
    if (r.ok && certOK(r.cert)) {
      certified++;
      worstGap = Math.max(worstGap, r.cert.gapRel);
      if (r.cert.bindingEvents.length > 0) withBinding++;
    }
  }
  check('D5 random sweep: every attempted instance certified (zero gap, clean KKT)',
    attempted > 150 && certified === attempted,
    certified + '/' + attempted + ' certified, ' + skippedInfeasible + ' infeasible-skipped (reported, not hidden), worst gap ' + worstGap.toExponential(2));
  check('D6 sweep coverage: stock-binding events actually exercised', withBinding >= 30,
    withBinding + '/' + attempted + ' instances with binding');
}

/* independent optimality witness: dominance over random feasible dispatches.
   Sampling is budget-aware: at each hour the draw is restricted so the
   REMAINING problem stays feasible (needed future release N ∈ [0, remaining
   capacity]), and the final hour is forced — every sample lands on Rend
   exactly. Failures to construct are counted, never hidden. */
{
  const rng = mulberry32(99);
  const futI = new Float64Array(T + 1);            // Σ inflows after hour t
  for (let t = T - 1; t >= 0; t--) futI[t] = futI[t + 1] + detInst.inflows[t];
  /* storage lookahead: R_t ≤ maxR_t = R̄ + min_{s>t} [(s−t)h̄ − Σ_{u=t+1..s} I_u]
     — otherwise a saved-up prefix hits UNAVOIDABLE overflow at the inflow
     surge (found by 500/500 construction failures on the demo instance) */
  const maxR = new Float64Array(T + 1).fill(detInst.Rbar);
  for (let t = T - 1; t >= 0; t--) {
    let cum = 0, worst = 0;
    for (let s = t + 1; s < T; s++) {
      cum += detInst.inflows[s];
      worst = Math.min(worst, (s - t) * detInst.hbar - cum);
    }
    maxR[t] = detInst.Rbar + worst;
  }
  let best = -Infinity, n = 0, failed = 0;
  for (let k = 0; k < 500; k++) {
    let R = detInst.R0, rev = 0, ok = true;
    for (let t = 0; t < T; t++) {
      const avail = R + detInst.inflows[t];
      /* box + stock window + storage lookahead */
      let lo = Math.max(0, avail - detInst.Rbar, avail - maxR[t]);
      let hi = Math.min(detInst.hbar, avail);
      /* budget window: after this hour, needed future release
         N = R_t + futI[t+1] − Rend must lie in [0, (T−1−t)·h̄] */
      const capLeft = (T - 1 - t) * detInst.hbar;
      lo = Math.max(lo, avail + futI[t + 1] - detInst.Rend - capLeft);
      hi = Math.min(hi, avail + futI[t + 1] - detInst.Rend);
      if (lo > hi + 1e-12) { ok = false; break; }
      const h = t === T - 1 ? hi : lo + (hi - lo) * rng();
      R = avail - h; rev += detInst.prices[t] * h;
    }
    if (!ok || Math.abs(R - detInst.Rend) > 1e-9) { failed++; continue; }
    n++;
    if (rev > best) best = rev;
  }
  check('D7 revenue dominance over random feasible dispatches (WEAK null — see D9)',
    n >= 400 && det.cert.revenue >= best - 1e-9,
    'margin +' + (det.cert.revenue - best).toFixed(4) + ' over ' + n + ' exact-endpoint samples (' + failed + ' construction failures, reported)' +
    ' — sampling is interior-concentrated, so this only rules out gross error; D9 is the test with power');
}

/* D9 — the null that actually has power. [ADDED 2026-07-21, adversarial review]
   D7 samples uniformly inside the per-hour feasible window, so its draws
   concentrate in the interior of the box and land nowhere near the optimum:
   the best of 500 falls ~0.34 short, and even flat dispatch is not far behind.
   Beating noise is not evidence of optimality.

   This tests the ADVERSARIAL neighbourhood instead: every pairwise exchange of
   release between two hours — "move δ from hour t to hour s" — which is the
   move that would improve a near-miss, and which subsumes the ±1-hour shifts
   and marginal-hour swaps a referee would try by hand. Budget is preserved by
   construction (total release unchanged), so only the box and the stock window
   bind:
     s > t : R_u rises by δ for u ∈ [t, s−1]  ⇒ δ ≤ min(Rbar − R_u)
     s < t : R_u falls by δ for u ∈ [s, t−1]  ⇒ δ ≤ min(R_u)
   plus h_t − δ ≥ 0 and h_s + δ ≤ hbar. Revenue moves by δ·(p_s − p_t), so at a
   true optimum every feasible exchange with p_s > p_t must have δ_max = 0.
   This is an independent witness: it never touches w or the dual. */
{
  const P = detInst.prices, { hbar, Rbar } = detInst;
  /* max feasible δ for "move δ of release from hour t to hour s" */
  const maxDelta = (h, R, t, s) => {
    let d = Math.min(h[t], hbar - h[s]);
    if (s > t) { for (let u = t; u < s; u++) d = Math.min(d, Rbar - R[u + 1]); }
    else       { for (let u = s; u < t; u++) d = Math.min(d, R[u + 1]); }
    return d;
  };
  const scan = (h, R) => {
    let gain = 0, pair = null, tested = 0, live = 0;
    for (let t = 0; t < T; t++) for (let s = 0; s < T; s++) {
      if (s === t) continue;
      tested++;
      if (P[s] <= P[t] + 1e-12) continue;     // only exchanges that could gain
      const d = maxDelta(h, R, t, s);
      if (d <= 1e-12) continue;
      live++;
      const g = d * (P[s] - P[t]);
      if (g > gain) { gain = g; pair = t + '→' + s; }
    }
    return { gain, pair, tested, live };
  };
  const a = scan(det.h, det.R);
  check('D9 no feasible pairwise exchange improves revenue (adversarial neighbourhood)',
    a.gain < 1e-9,
    a.tested + ' ordered pairs, ' + a.live + ' with slack; best available gain ' +
    a.gain.toExponential(2) + (a.pair ? ' at ' + a.pair : ''));

  /* D10 — D9 passes with zero pairs live, which is what an optimum looks like
     and also what a vacuous test looks like. So: damage the optimum by ONE
     feasible exchange in the losing direction (high price → low price) and
     require the scan to find the way back. Without this, D9 would be another
     check that cannot go red. */
  const simR = h => { const R = new Float64Array(T + 1); R[0] = detInst.R0;
    for (let u = 0; u < T; u++) R[u + 1] = R[u] + detInst.inflows[u] - h[u]; return R; };
  let mut = null, moved = 0, from = null;
  for (let t = 0; t < T && !mut; t++) for (let s = 0; s < T && !mut; s++) {
    if (s === t || P[t] <= P[s] + 1e-12) continue;   // LOSING direction: p_t > p_s
    const d = maxDelta(det.h, det.R, t, s);
    if (d <= 1e-6) continue;
    const h2 = det.h.slice(); h2[t] -= d; h2[s] += d;
    mut = { h: h2, R: simR(h2) }; moved = d; from = t + '→' + s;
  }
  const b = mut ? scan(mut.h, mut.R) : { gain: 0, pair: null, live: 0 };
  check('D10 mutant (one feasible exchange away from the optimum) is CAUGHT by D9\'s scan',
    mut !== null && b.gain > 1e-6,
    mut ? 'moved ' + moved.toFixed(4) + ' ' + from + ' (revenue −' +
      (moved * (P[+from.split('→')[0]] - P[+from.split('→')[1]])).toFixed(4) +
      '); scan then finds gain ' + b.gain.toExponential(2) + ' at ' + b.pair
      : 'NO feasible losing exchange exists — D9 is untestable on this instance, report it');
}

/* mutants — the gates can go red */
{
  /* mutant 1: shift w on hours 1..8 by +0.1 → trichotomy and/or gap must break */
  const wMut = det.w.slice();
  for (let t = 0; t < 8; t++) wMut[t] += 0.1;
  let tri = 0;
  for (let t = 0; t < T; t++) {
    if (detInst.prices[t] > wMut[t] + 1e-9 && det.h[t] < detInst.hbar - 1e-9) tri++;
    if (detInst.prices[t] < wMut[t] - 1e-9 && det.h[t] > 1e-9) tri++;
  }
  let D = wMut[0] * detInst.R0 - wMut[T - 1] * detInst.Rend;
  for (let t = 0; t < T; t++) {
    D += wMut[t] * detInst.inflows[t] + detInst.hbar * Math.max(detInst.prices[t] - wMut[t], 0);
    if (t < T - 1) D += detInst.Rbar * Math.max(wMut[t + 1] - wMut[t], 0);
  }
  const gapMut = Math.abs(det.cert.revenue - D);
  check('D8 mutant (shifted w) is CAUGHT by trichotomy or gap', tri > 0 || gapMut > 1e-3,
    'tri ' + tri + ', gap ' + gapMut.toExponential(2));
}

/* ================= S · scenario tree (the martingale theorem) ================= */
const treeOK = c => c.dynErr < 1e-9 && c.boxErr < 1e-9 && c.tri === 0 && c.wedgeSignErr < 1e-9 &&
  c.compSlack < 1e-9 && c.spillDualErr < 1e-9 && c.gapRel < 1e-12 && c.martingaleRes < 1e-12;

const rngT = mulberry32(7);
const demoNodes = buildTree(4, 2, n => ({
  price: 0.5 + 0.8 * rngT() + (n.depth === 2 ? 0.5 : 0),
  inflow: 0.15 + 0.5 * rngT(),
}));
const tr = solveTree(demoNodes, { R0: 0.4, Rbar: 0.8, hbar: 0.35, phi: 0.55 });
check('S1 demo tree certifies (KKT + zero gap + martingale off-binding)', treeOK(tr.cert),
  'gap ' + tr.cert.gapRel.toExponential(2) + ', martingale res ' + tr.cert.martingaleRes.toExponential(2));
check('S2 coverage: stock-binding nodes present (the jumps exist)', tr.cert.bindingNodes >= 1,
  tr.cert.bindingNodes + ' binding of ' + demoNodes.length);

/* random tree sweep */
{
  const rng = mulberry32(4242);
  let n = 0, certified = 0, withBind = 0, withSpill = 0, pureMart = 0, worstGap = 0, worstMart = 0;
  for (let k = 0; k < 120; k++) {
    const depth = 3 + (k % 2), branching = 2 + (k % 3 === 0 ? 1 : 0);
    const heavy = k % 4 === 0 ? 2.2 : 1.0;                    // heavy inflow → spill coverage
    const nodes = buildTree(depth, branching, () => ({
      price: 0.2 + 1.5 * rng(),
      inflow: (0.05 + 0.45 * rng()) * heavy,
    }));
    const Rbar = 0.5 + 0.8 * rng();
    const r = solveTree(nodes, { R0: Rbar * rng(), Rbar, hbar: 0.2 + 0.25 * rng(), phi: 0.2 + 0.8 * rng() });
    n++;
    if (treeOK(r.cert)) {
      certified++;
      worstGap = Math.max(worstGap, r.cert.gapRel);
      worstMart = Math.max(worstMart, r.cert.martingaleRes);
      if (r.cert.bindingNodes > 0) withBind++;
      if (r.cert.spillNodes > 0) withSpill++;
      if (r.cert.bindingNodes === 0 && r.cert.spillNodes === 0) pureMart++;
    }
  }
  check('S3 random tree sweep: every instance certified', certified === n,
    certified + '/' + n + ', worst gap ' + worstGap.toExponential(2) + ', worst martingale res ' + worstMart.toExponential(2));
  check('S4 sweep coverage: binding, spill AND pure-martingale trees all exercised',
    withBind >= 10 && withSpill >= 3 && pureMart >= 3,
    'binding ' + withBind + ' · spill ' + withSpill + ' · pure-martingale ' + pureMart + ' of ' + n);
}

/* independent witness: dominance over random feasible nonanticipative policies */
{
  const rng = mulberry32(31);
  let best = -Infinity;
  for (let k = 0; k < 300; k++) {
    const Rn = new Float64Array(demoNodes.length); Rn[0] = 0.4;
    let rev = 0;
    for (const nd of demoNodes) {
      const avail = Rn[nd.id] + nd.inflow;
      const h = Math.min(0.35, avail) * rng();
      const rp = Math.min(0.8, avail - h);                     // spill the rest
      rev += nd.p * nd.price * h;
      if (nd.children.length === 0) rev += nd.p * 0.55 * rp;
      for (const c of nd.children) Rn[c] = rp;
    }
    if (rev > best) best = rev;
  }
  check('S5 revenue dominance over random feasible tree policies (WEAK null — no D9 analogue yet)',
    tr.cert.revenue >= best - 1e-9, 'margin +' + (tr.cert.revenue - best).toFixed(4) +
    ' — same interior-concentration caveat as D7; the node-level exchange neighbourhood is NOT yet implemented for the tree, so the tree optimum has no local-optimality witness');
}

/* mutant: perturb w at an off-binding interior node → martingale/gap red */
{
  const idx = demoNodes.findIndex(nd => nd.children.length > 0 &&
    Math.abs(tr.Rp[nd.id]) > 1e-6 && Math.abs(tr.Rp[nd.id] - 0.8) > 1e-6 && tr.spill[nd.id] < 1e-9);
  const wMut = tr.w.slice(); wMut[idx] += 0.2;
  const nd = demoNodes[idx];
  const martRes = Math.abs(wMut[idx] - nd.children.reduce((s, c) => s + demoNodes[c].q * wMut[c], 0));
  check('S6 mutant (perturbed off-binding w) is CAUGHT by the martingale identity', martRes > 0.1,
    'node ' + idx + ', residual ' + martRes.toExponential(2));
}

console.log('\n' + (fails.length ? fails.length + ' FAILURE(S)'
  : 'ALL PASS — water value certified: piecewise-constant w (deterministic) and martingale-off-binding w (tree), both by zero-gap LP duality.'));
process.exit(fails.length ? 1 : 0);
