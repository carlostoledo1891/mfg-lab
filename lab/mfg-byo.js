/* mfg-byo.js — bring your own mean-field game.
 *
 * The gap a reader assumes the Lab already fills: not "bring your own solver"
 * (that is the order-study / failure-map instruments), but "bring your own
 * PROBLEM" — supply the cost of a mean-field game and get the certified solve.
 *
 * This is that solver, for the one class where the certificate MEANS something:
 * a 1D crowd on [0,1] with a quadratic Hamiltonian,
 *
 *     -∂_t u - ν ∂_xx u + ½|∂_x u|² = f(m)        (HJB, backward)
 *      ∂_t m - ν ∂_xx m - ∂_x(m ∂_x u) = 0        (Fokker–Planck, forward)
 *      u(·,T) = V(x)   (terminal cost)   m(·,0) = m₀
 *
 * solved by fictitious play, exactly the FD-monotone scheme validated in the
 * lab's Module 1 — only the coupling f(m) and the terminal cost V(x) are yours
 * instead of a fixed power law.
 *
 * WHY THE CERTIFICATE STAYS HONEST FOR AN ARBITRARY COST. The certificate is
 * EXPLOITABILITY (the ε-Nash gap): freeze the population, solve the individual's
 * best response, measure how much a player gains by deviating. That gap is a
 * pre-update residual and it is valid for ANY f and V — it does not assume the
 * problem is monotone. So a well-posed monotone cost converges to ε≈0 (a
 * certified equilibrium), and a pathological cost simply reports a large ε: the
 * fixed point it reached is NOT an equilibrium, and the lab says so rather than
 * pretending. Nothing about "bring your own cost" weakens the guarantee — that
 * is the whole point of certifying by exploitability instead of by step size.
 *
 * A cost that is NOT monotone can admit several equilibria; the certificate
 * still tells the truth about the one the flow reached (ε small ⟺ it is one).
 *
 * MIT licensed. Part of the MFG Lab.  Runs in Node and in the browser.
 */
'use strict';

/* Thomas algorithm for a tridiagonal solve — the one linear-algebra primitive
   the scheme needs. Mirrors the lab's makeTri. */
function makeTri(n) {
  const cp = new Float64Array(n), dp = new Float64Array(n);
  return function tri(a, b, c, d, x) {
    cp[0] = c[0] / b[0]; dp[0] = d[0] / b[0];
    for (let i = 1; i < n; i++) {
      const den = b[i] - a[i] * cp[i - 1];
      cp[i] = c[i] / den;
      dp[i] = (d[i] - a[i] * dp[i - 1]) / den;
    }
    x[n - 1] = dp[n - 1];
    for (let i = n - 2; i >= 0; i--) x[i] = dp[i] - cp[i] * x[i + 1];
  };
}

const DEFAULTS = {
  NX: 120, NT: 240, T: 1.0,
  tol: 1e-6, maxIter: 500,
  beta: 0.67,          // fictitious-play averaging exponent θ_k = (k+2)^-β
  sigma: 0.18,         // ν = ½σ²
  m0: null,            // initial density; default a Gaussian bump at x=0.25
};

/* Build a validated MFG problem from a user cost. `cost` and `terminal` are the
   only things a user supplies:
     cost(m)     : ℝ≥0 → ℝ   the running coupling f(m), m the local density
     terminal(x) : [0,1] → ℝ the terminal cost V(x)
   Both are plain functions; the caller is responsible for evaluating any
   user-typed expression into one (the UI does that behind a try/catch). */
function makeProblem(opts) {
  opts = opts || {};
  const P = Object.assign({}, DEFAULTS, opts);
  const NX = P.NX, NT = P.NT, H = 1 / (NX - 1), DT = P.T / NT, nu = 0.5 * P.sigma * P.sigma;
  const xs = new Float64Array(NX);
  for (let i = 0; i < NX; i++) xs[i] = i * H;

  const cost = typeof P.cost === 'function' ? P.cost : (m => 0);
  const term = typeof P.terminal === 'function' ? P.terminal : (x => 4 * (x - 0.8) ** 2);

  /* initial density: user-supplied or a default Gaussian bump, normalised to
     unit mass. mRef (the peak) sets the density scale a coupling is read on. */
  const m0 = new Float64Array(NX);
  if (P.m0 && P.m0.length === NX) { m0.set(P.m0); }
  else { for (let i = 0; i < NX; i++) m0[i] = Math.exp(-((xs[i] - 0.25) ** 2) / (2 * 0.10 ** 2)); }
  let sum = 0; for (let i = 0; i < NX; i++) sum += m0[i];
  for (let i = 0; i < NX; i++) m0[i] /= sum * H;
  let mRef = 0; for (let i = 0; i < NX; i++) if (m0[i] > mRef) mRef = m0[i];

  /* cost is written by the user in terms of the density; internally the scheme
     reads it against mRef exactly as Module 1 does, so f(m)=c·(m/mRef)^γ
     reproduces the fixed module when the same c,γ are used. We pass the RAW
     m to the user function and let them scale — simpler contract, one argument. */
  const f = m => cost(Math.max(m, 0));

  const tri = makeTri(NX);
  const A = new Float64Array(NX), B = new Float64Array(NX), C = new Float64Array(NX), D = new Float64Array(NX);

  function solveHJB(mH, U) {
    const rd = DT * nu / (H * H), rh = DT / H;
    const uT = U.subarray(NT * NX);
    for (let i = 0; i < NX; i++) uT[i] = term(xs[i]);
    for (let n = NT - 1; n >= 0; n--) {
      const uN = U.subarray((n + 1) * NX, (n + 2) * NX), uC = U.subarray(n * NX, (n + 1) * NX);
      const m = mH.subarray(n * NX, (n + 1) * NX);
      for (let i = 0; i < NX; i++) {
        const pm = (i > 0) ? (uN[i] - uN[i - 1]) / H : 0, pp = (i < NX - 1) ? (uN[i + 1] - uN[i]) / H : 0;
        const vm = Math.max(pm, 0), vp = Math.min(pp, 0);
        const fL = (i > 0) ? 1 : 0, fR = (i < NX - 1) ? 1 : 0;
        A[i] = -rd * fL - rh * vm; C[i] = -rd * fR + rh * vp;
        B[i] = 1 + rd * (fL + fR) + rh * vm - rh * vp;
        D[i] = uN[i] + DT * (0.5 * (vm * vm + vp * vp) + f(m[i]));
      }
      tri(A, B, C, D, uC);
    }
  }

  const ap = new Float64Array(NX + 1), am = new Float64Array(NX + 1);
  function solveFP(U, m0v, M) {
    const rd = DT * nu / (H * H), rh = DT / H;
    M.subarray(0, NX).set(m0v);
    for (let n = 0; n < NT; n++) {
      const u = U.subarray(n * NX, (n + 1) * NX), m = M.subarray(n * NX, (n + 1) * NX), mNew = M.subarray((n + 1) * NX, (n + 2) * NX);
      ap[0] = am[0] = ap[NX] = am[NX] = 0;
      for (let i = 0; i < NX - 1; i++) {
        const s = (u[i + 1] - u[i]) / H;
        ap[i + 1] = Math.max(-s, 0);
        am[i + 1] = Math.min(-s, 0);
      }
      for (let i = 0; i < NX; i++) {
        const fL = (i > 0) ? 1 : 0, fR = (i < NX - 1) ? 1 : 0;
        A[i] = -rd * fL - rh * ap[i]; C[i] = -rd * fR + rh * am[i + 1];
        B[i] = 1 + rd * (fL + fR) + rh * ap[i + 1] - rh * am[i];
        D[i] = m[i];
      }
      tri(A, B, C, D, mNew);
    }
  }

  /* Exploitability: the policy from uStar (against its own mStar) evaluated in
     the environment mTilde, minus the true best response to mTilde. Same
     construction as Module 1 — the pre-update ε-Nash gap. */
  function exploitability(uStar, mTildeH, m0v) {
    const rd = DT * nu / (H * H), rh = DT / H;
    const V = new Float64Array((NT + 1) * NX), uBR = new Float64Array((NT + 1) * NX);
    const vT = V.subarray(NT * NX);
    for (let i = 0; i < NX; i++) vT[i] = term(xs[i]);
    for (let n = NT - 1; n >= 0; n--) {
      const uN = uStar.subarray((n + 1) * NX, (n + 2) * NX), vN = V.subarray((n + 1) * NX, (n + 2) * NX),
        vC = V.subarray(n * NX, (n + 1) * NX);
      const mT = mTildeH.subarray(n * NX, (n + 1) * NX);
      for (let i = 0; i < NX; i++) {
        const pm = (i > 0) ? (uN[i] - uN[i - 1]) / H : 0, pp = (i < NX - 1) ? (uN[i + 1] - uN[i]) / H : 0;
        const wm = Math.max(pm, 0), wp = Math.min(pp, 0);
        const fL = (i > 0) ? 1 : 0, fR = (i < NX - 1) ? 1 : 0;
        A[i] = -rd * fL - rh * wm; C[i] = -rd * fR + rh * wp;
        B[i] = 1 + rd * (fL + fR) + rh * wm - rh * wp;
        D[i] = vN[i] + DT * (0.5 * (wm * wm + wp * wp) + f(mT[i]));
      }
      tri(A, B, C, D, vC);
    }
    solveHJB(mTildeH, uBR);
    let eps = 0;
    for (let i = 0; i < NX; i++) eps += (V[i] - uBR[i]) * m0v[i];
    return eps * H;
  }

  return { NX, NT, H, DT, nu, xs, m0, mRef, solveHJB, solveFP, exploitability, params: P };
}

/* Run fictitious play to convergence (or the iteration cap) and return the
   certified result. The verdict is gated on the certificate, never on the step
   size: a fixed point whose exploitability is not small is reported as NOT an
   equilibrium — the house rule. */
function solve(opts) {
  const Pb = makeProblem(opts);
  const { NX, NT, H, solveHJB, solveFP, exploitability, m0 } = Pb;
  const tol = Pb.params.tol, maxIter = Pb.params.maxIter, beta = Pb.params.beta;

  const mHist = new Float64Array((NT + 1) * NX), mTilde = new Float64Array((NT + 1) * NX);
  const U = new Float64Array((NT + 1) * NX);
  for (let n = 0; n <= NT; n++) mHist.set(m0, n * NX);

  let iter = 0, residual = Infinity, eps = NaN;
  while (iter < maxIter) {
    solveHJB(mHist, U);
    solveFP(U, m0, mTilde);
    let rm = 0, peak = 0;
    for (let j = 0; j < mHist.length; j++) {
      const d = Math.abs(mTilde[j] - mHist[j]); if (d > rm) rm = d;
      if (mTilde[j] > peak) peak = mTilde[j];
    }
    rm /= Math.max(peak, 1e-12);
    residual = rm;
    const last = rm < tol || iter + 1 >= maxIter;
    if (iter % 10 === 0 || last) eps = exploitability(U, mTilde, m0);
    const th = Math.pow(iter + 2, -beta);
    for (let j = 0; j < mHist.length; j++) mHist[j] = (1 - th) * mHist[j] + th * mTilde[j];
    iter++;
    if (rm < tol) break;
  }

  /* certificates */
  let minM = Infinity, massWorst = 0;
  for (let j = 0; j < mHist.length; j++) if (mHist[j] < minM) minM = mHist[j];
  for (let n = 0; n <= NT; n++) { let sl = 0; for (let i = 0; i < NX; i++) sl += mHist[n * NX + i]; const dr = Math.abs(sl * H - 1); if (dr > massWorst) massWorst = dr; }

  const converged = residual < tol;
  const v = verdictOf(converged, eps);

  return {
    iters: iter, residual, exploitability: eps,
    massDrift: massWorst, minDensity: minM,
    converged, isEquilibrium: v.isEquilibrium, verdict: v.verdict,
    m: mHist, u: U, NX, NT, xs: Pb.xs,
  };
}

/* THE VERDICT IS GATED ON THE CERTIFICATE, not on convergence. A fixed point
   the flow settled onto is called an equilibrium ONLY if a player cannot gain
   by deviating — |ε| below the ε-Nash threshold. Settled-but-exploitable is
   NOT_AN_EQUILIBRIUM; not-settled is STALLED. Pure and exported so the battery
   can prove the gate can flip — a verdict that always says EQUILIBRIUM is the
   fake certificate this lab exists to refuse. */
const EPS_NASH = 1e-3;
function verdictOf(converged, eps) {
  const isEquilibrium = converged && Number.isFinite(eps) && Math.abs(eps) < EPS_NASH;
  return {
    isEquilibrium,
    verdict: isEquilibrium ? 'EQUILIBRIUM'
      : converged ? 'NOT_AN_EQUILIBRIUM'
        : 'STALLED',
  };
}

module.exports = { makeProblem, solve, verdictOf, makeTri, DEFAULTS, EPS_NASH };
