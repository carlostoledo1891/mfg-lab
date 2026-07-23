/* test-byo.js — battery for "bring your own mean-field game" (lab/mfg-byo.js).
 *
 * BATTERY BEFORE PIXELS: this validates the certified solve BEFORE any UI wires
 * it, on load-bearing certificates rather than magnitude checks. The whole
 * point of the feature is that a USER-supplied cost still gets an HONEST
 * certificate, so the checks that matter are the ones that could go RED on a
 * wrong solve:
 *
 *   B1  DECOUPLED CASE, ANALYTICAL. With f(m)=0 the game decouples — the
 *       density affects no one's cost, so nobody can gain by deviating and the
 *       exploitability MUST be ~0. This is an exact analytic anchor, not a
 *       tolerance: if the solver or the certificate is wrong, this is where it
 *       shows. (ε small here proves the exploitability construction is sound.)
 *   B2  a MONOTONE (aversion) cost converges to a certified equilibrium.
 *   B3  the verdict GATE flips — proven on the pure verdictOf: settled+small-ε
 *       ⇒ EQUILIBRIUM, settled+large-ε ⇒ NOT_AN_EQUILIBRIUM, not-settled ⇒
 *       STALLED. A gate that cannot flip is decoration.
 *   B4  mass conservation and positivity — the scheme's structural certificates.
 *   B5  a user TERMINAL cost actually steers the density (the "bring your own"
 *       part is wired, not ignored).
 *   B6  a HARD/pathological cost is reported honestly (never silently called an
 *       equilibrium): its verdict is one of the non-EQUILIBRIUM outcomes OR, if
 *       it does settle, it settles with a small ε — i.e. the verdict always
 *       matches the certificate.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const K = require('../lab/mfg-byo.js');

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.error('   FAIL  ' + m); } };
const sha = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex').slice(0, 16);

console.log('== bring-your-own-MFG battery ==');
console.log('   mfg-lab/lab/mfg-byo.js  sha256:' + sha(path.join(__dirname, '..', 'lab', 'mfg-byo.js')));

/* Faster grid for the battery; the physics is identical, only cheaper. The
   default full grid (120x240) is what the page uses. */
const GRID = { NX: 80, NT: 120, maxIter: 400, sigma: 0.2 };

/* ---- B1 · decoupled: ε must be ~0 (analytical) ---- */
const dec = K.solve(Object.assign({ cost: m => 0, terminal: x => 4 * (x - 0.8) ** 2 }, GRID));
ok(Math.abs(dec.exploitability) < 1e-6,
   'B1 decoupled game (f=0): exploitability is ~0 — got ' + dec.exploitability.toExponential(3) +
   ' (analytic: no coupling ⇒ no incentive to deviate; this proves the ε construction)');
ok(dec.verdict === 'EQUILIBRIUM', 'B1b and it is certified an equilibrium — got ' + dec.verdict);
console.log('   B1  decoupled ε = ' + dec.exploitability.toExponential(3) + ' (~0, exact anchor)');

/* ---- B2 · monotone aversion cost converges & certifies ---- */
const av = K.solve(Object.assign({ cost: m => 0.6 * Math.pow(Math.max(m, 0), 1.5), terminal: x => 4 * (x - 0.8) ** 2 }, GRID));
ok(av.converged, 'B2 a monotone aversion cost converges — residual ' + av.residual.toExponential(2));
ok(Math.abs(av.exploitability) < 1e-3, 'B2b with a small ε-Nash gap — ' + av.exploitability.toExponential(3));
ok(av.verdict === 'EQUILIBRIUM', 'B2c verdict EQUILIBRIUM');
console.log('   B2  aversion  ε = ' + av.exploitability.toExponential(3) + ', ' + av.iters + ' iters, verdict ' + av.verdict);

/* ---- B3 · the verdict GATE can flip (the load-bearing honesty check) ---- */
ok(K.verdictOf(true, 1e-9).verdict === 'EQUILIBRIUM', 'B3a settled + tiny ε ⇒ EQUILIBRIUM');
ok(K.verdictOf(true, 0.5).verdict === 'NOT_AN_EQUILIBRIUM',
   'B3b SETTLED BUT EXPLOITABLE ⇒ NOT_AN_EQUILIBRIUM — the gate refuses a fixed point whose certificate is violated');
ok(K.verdictOf(true, 0.5).isEquilibrium === false, 'B3c and isEquilibrium is false there');
ok(K.verdictOf(false, 1e-9).verdict === 'STALLED', 'B3d not settled ⇒ STALLED even with a small ε');
ok(K.verdictOf(true, NaN).verdict === 'NOT_AN_EQUILIBRIUM', 'B3e a non-finite ε is never an equilibrium');

/* ---- B4 · structural certificates ---- */
ok(av.massDrift < 1e-9, 'B4 mass conserved along the whole trajectory — drift ' + av.massDrift.toExponential(2));
ok(av.minDensity > -1e-9, 'B4b density stays non-negative — min ' + av.minDensity.toExponential(2));

/* ---- B5 · a user TERMINAL steers the density ---- */
/* Two different targets must move where the mass ends up. Compare the density
   centroid at the final time under a left target vs a right target. */
function centroid(res) {
  const NX = res.NX, NT = res.NT, xs = res.xs, m = res.m;
  let num = 0, den = 0;
  for (let i = 0; i < NX; i++) { const w = m[NT * NX + i]; num += xs[i] * w; den += w; }
  return num / den;
}
const left = K.solve(Object.assign({ cost: m => 0.3 * m, terminal: x => 4 * (x - 0.2) ** 2 }, GRID));
const right = K.solve(Object.assign({ cost: m => 0.3 * m, terminal: x => 4 * (x - 0.9) ** 2 }, GRID));
const cL = centroid(left), cR = centroid(right);
ok(cR - cL > 0.15, 'B5 the user terminal steers the crowd: centroid moves right when the target does (' +
   cL.toFixed(3) + ' → ' + cR.toFixed(3) + ')');
console.log('   B5  target x*=0.2 → centroid ' + cL.toFixed(3) + '   ·   x*=0.9 → centroid ' + cR.toFixed(3));

/* ---- B6 · a hard cost is reported honestly ---- */
/* Strong attraction to the crowd (anti-monotone, herding) — the ill-posed
   regime. Whatever it does, the verdict must MATCH the certificate: it is
   never called an equilibrium unless ε is actually small. */
const herd = K.solve(Object.assign({ cost: m => -1.5 * Math.max(m, 0), terminal: x => 4 * (x - 0.5) ** 2, maxIter: 200 }, GRID));
ok(herd.isEquilibrium === (herd.converged && Math.abs(herd.exploitability) < K.EPS_NASH),
   'B6 the herding cost verdict matches its certificate exactly (never a free pass)');
ok(herd.verdict === 'EQUILIBRIUM' ? Math.abs(herd.exploitability) < K.EPS_NASH : true,
   'B6b if it claims EQUILIBRIUM the ε really is small');
console.log('   B6  herding  verdict ' + herd.verdict + ', ε = ' + herd.exploitability.toExponential(3) +
   ', converged=' + herd.converged);

console.log('   ' + pass + ' PASS, ' + fail + ' FAIL');
if (fail) { console.error('bring-your-own-MFG battery FAILED'); process.exit(1); }
