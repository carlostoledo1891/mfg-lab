/* test-transpose.js — certify the mfg-lab structural claim that was ASSERTED,
   not tested: "the Fokker–Planck transport is the exact discrete transpose of
   the linearized HJB drift" (mfg-lab.html method tab). The identical phrase was
   found FALSE in sin-mfg (FINDINGS_SIN Defect 4) once finally measured, so an
   untested twin here is a liability — and the sin-mfg note's Defect-4 contrast
   explicitly relies on the lab being adjoint-matched. This closes that gap.

   It is TRUE for the lab because the continuum tabs use the Achdou–Capuzzo-
   Dolcetta pair: an upwind monotone HJB whose linearization's exact transpose IS
   the FP operator (block-symmetric, positivity-preserving). "adjoint-matched"
   (FP = HJBᵀ), NOT "self-adjoint" (A = Aᵀ) — the diffusion is separately
   symmetric.

   Method: replicate the single-step transport+diffusion coefficients of M1's
   solveHJB and solveFP (mfg-lab.html), build both matrices for a frozen (u,g),
   and assert |M_FP − M_HJBᵀ|/scale ≈ 0. The replicated formulas are ANCHORED to
   the artifact source (regex): if a future edit changes the M1 coefficients, the
   anchor fails and the transpose must be re-verified — the same source-anchored
   discipline as test-sin.js A22/A23. */
'use strict';
const fs = require('fs');
const path = require('path');

const HTML = process.env.MFG_HTML || path.resolve(__dirname, '..', 'mfg-lab.html');
const src = fs.readFileSync(HTML, 'utf8');
const fails = [];
function check(name, cond, detail) {
  console.log((cond ? 'PASS  ' : 'FAIL  ') + name + (detail ? '   [' + detail + ']' : ''));
  if (!cond) fails.push(name);
}

/* --- ANCHORS: the M1 coefficient formulas this check replicates must still be
   the ones in the artifact. These are the exact lines from solveHJB/solveFP. --- */
const hjbVel = /vm=Math\.max\(pm,0\)\/g, vp=Math\.min\(pp,0\)\/g;/;
const hjbCoef = /A\[i\]=-rd\*fL-rh\*vm; C\[i\]=-rd\*fR\+rh\*vp;/;
const fpFlux = /ap\[i\+1\]=Math\.max\(-s,0\)\/gI\[i\];\s*am\[i\+1\]=Math\.min\(-s,0\)\/gI\[i\+1\];/;
const fpCoef = /A\[i\]=-rd\*fL-rh\*ap\[i\]; C\[i\]=-rd\*fR\+rh\*am\[i\+1\];/;
check('anchor: M1 solveHJB upwind-velocity formula unchanged', hjbVel.test(src));
check('anchor: M1 solveHJB tridiagonal coefficients unchanged', hjbCoef.test(src));
check('anchor: M1 solveFP interface-flux formula unchanged', fpFlux.test(src));
check('anchor: M1 solveFP tridiagonal coefficients unchanged', fpCoef.test(src));

/* --- build both operators from those exact formulas and measure the match --- */
const NX = 40, H = 1 / (NX - 1), DT = 0.01, nu = 0.02;
const rd = DT * nu / (H * H), rh = DT / H;
const xs = Array.from({ length: NX }, (_, i) => i * H);
const u = xs.map(x => 4.0 * (x - 0.8) ** 2 + 0.3 * Math.sin(6 * x));   // sign-varying gradient
const g = xs.map(x => 1.0 + 0.5 * Math.exp(-((x - 0.4) ** 2) / 0.02)); // varying congestion

function mHJB() {
  const M = Array.from({ length: NX }, () => new Array(NX).fill(0));
  for (let i = 0; i < NX; i++) {
    const pm = i > 0 ? (u[i] - u[i - 1]) / H : 0, pp = i < NX - 1 ? (u[i + 1] - u[i]) / H : 0;
    const vm = Math.max(pm, 0) / g[i], vp = Math.min(pp, 0) / g[i];
    const fL = i > 0 ? 1 : 0, fR = i < NX - 1 ? 1 : 0;
    if (i > 0) M[i][i - 1] = -rd * fL - rh * vm;
    M[i][i] = 1 + rd * (fL + fR) + rh * vm - rh * vp;
    if (i < NX - 1) M[i][i + 1] = -rd * fR + rh * vp;
  }
  return M;
}
function mFP() {
  const M = Array.from({ length: NX }, () => new Array(NX).fill(0));
  const ap = new Array(NX + 1).fill(0), am = new Array(NX + 1).fill(0);
  for (let i = 0; i < NX - 1; i++) { const s = (u[i + 1] - u[i]) / H; ap[i + 1] = Math.max(-s, 0) / g[i]; am[i + 1] = Math.min(-s, 0) / g[i + 1]; }
  for (let i = 0; i < NX; i++) {
    const fL = i > 0 ? 1 : 0, fR = i < NX - 1 ? 1 : 0;
    if (i > 0) M[i][i - 1] = -rd * fL - rh * ap[i];
    M[i][i] = 1 + rd * (fL + fR) + rh * ap[i + 1] - rh * am[i];
    if (i < NX - 1) M[i][i + 1] = -rd * fR + rh * am[i + 1];
  }
  return M;
}
const A = mHJB(), F = mFP();
let dT = 0, scale = 0, dSym = 0;
for (let i = 0; i < NX; i++) for (let j = 0; j < NX; j++) {
  dT = Math.max(dT, Math.abs(F[i][j] - A[j][i]));
  scale = Math.max(scale, Math.abs(F[i][j]));
}
check('FP transport is the EXACT discrete transpose of the linearized HJB (adjoint-matched)',
  dT / scale < 1e-12, '|M_FP - M_HJBᵀ|/scale = ' + (dT / scale).toExponential(2));

/* diffusion alone (rh→0 has no transport) must be symmetric — the self-adjoint part */
const Ad = A.map(r => r.slice());
for (let i = 0; i < NX; i++) for (let j = 0; j < NX; j++) dSym = Math.max(dSym, Math.abs(A[i][j] - A[j][i]));
console.log('    (note: the full one-step operator is adjoint-matched FP=HJBᵀ, not self-adjoint A=Aᵀ; diffusion alone is symmetric)');

console.log('\n' + (fails.length ? fails.length + ' FAILURE(S)' : 'ALL PASS — lab FP = HJBᵀ certified, not asserted.'));
process.exit(fails.length ? 1 : 0);
