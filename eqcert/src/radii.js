/* radii.js — the radii-polynomial driver, and the Krawczyk operator.

   Two standard contraction arguments, packaged so that the SIDE CONDITIONS
   cannot be skipped. Neither is new mathematics; both are easy to apply
   slightly wrong in ways that produce a confident wrong answer.

   ---- radiiPolynomial(Y0, Z1, Z2) ----

   For T(x) = x − A F(x) with

       ||T(x̄) − x̄|| <= Y0,     ||DT(x)|| <= Z1 + Z2 r  on B_r(x̄),

   the map is a contraction of B_r(x̄) into itself whenever

       p(r) = ½ Z2 r² − (1 − Z1) r + Y0  <  0,

   and then it has a unique fixed point there — a zero of F. [STANDARD:
   Banach fixed point; the radii-polynomial formulation is the van den
   Berg–Lessard framework.]

   The trap this function closes: the smaller ROOT of p is not a valid radius.
   There p(r) = 0, the contraction is not strict, and nothing is proved. The
   float root is only a starting point; the returned radius is enlarged until
   p(r) < 0 is verified IN INTERVAL ARITHMETIC. This mattered — an earlier
   version of this code reported the root itself and its own consistency check
   caught it.

   ---- krawczyk(F, DF, x0, A) ----

   If K(X) = x0 − A F(x0) + (I − A DF(X))(X − x0) satisfies K(X) ⊂ int(X),
   then F has a unique zero in X. [STANDARD: Krawczyk / Moore.] Strict
   interior containment is the whole content: K(X) ⊆ X is not enough for
   uniqueness, and the check here is strict.

   MIT licensed. Part of eqcert. */
'use strict';

const I = require('./interval.js');
const { iv, add, sub, mul, ONE, ZERO, mag, interior } = I;

/* Y0, Z1, Z2 may be numbers or intervals; the upper bound of each is used. */
const up = v => (typeof v === 'number' ? v : v[1]);

function radiiPolynomial(Y0in, Z1in, Z2in, opts) {
  opts = opts || {};
  const Y0 = up(Y0in), Z1 = up(Z1in), Z2 = up(Z2in);
  const base = { Y0, Z1, Z2 };

  if (!(Z1 < 1)) {
    return Object.assign({ ok: false, why: 'Z1 >= 1 — the approximate inverse is not one; no contraction at any radius' }, base);
  }
  if (!(Z2 > 0)) {
    /* linear problem: p is affine, negative for r > Y0/(1−Z1) */
    const r = I.nextUp(Y0 / (1 - Z1) * 1.5 + Number.MIN_VALUE);
    return Object.assign({ ok: r > 0, r, rMin: Y0 / (1 - Z1), rMax: Infinity, linear: true }, base);
  }
  const disc = (1 - Z1) * (1 - Z1) - 2 * Z2 * Y0;
  if (!(disc > 0)) {
    return Object.assign({ ok: false, why: 'discriminant <= 0 — the defect is too large for the contraction to close', disc }, base);
  }
  const sq = Math.sqrt(disc);
  /* CANCELLATION. The textbook form ((1−Z1) − sqrt(disc))/Z2 for the SMALLER
     root loses all its significant digits exactly when 2·Z2·Y0 << (1−Z1)² —
     that is, when the defect is tiny, which is the case this driver is used in
     almost every time. The stable form is 2·Y0/((1−Z1) + sqrt(disc)), the
     standard trick for the root nearer zero. The battery caught this: a regime
     with Y0 = 1e−20 returned garbage and then failed to verify, which is the
     right failure but for the wrong reason. */
  const rMin = I.nextUp(2 * Y0 / ((1 - Z1) + sq));
  const rMax = I.nextDown(((1 - Z1) + sq) / Z2);

  /* p(r) evaluated rigorously */
  const IY = iv(Y0), IZ1 = iv(Z1), IZ2 = iv(Z2);
  const pAt = rr => {
    const R = iv(rr);
    return add(sub(mul(mul(iv(0.5), IZ2), mul(R, R)), mul(sub(ONE, IZ1), R)), IY);
  };
  /* the root itself has p(r) = 0; walk up until the ENCLOSURE is negative */
  let r = rMin, ok = false;
  for (let t = 0; t < 400; t++) {
    if (r > rMax) break;
    if (pAt(r)[1] < 0) { ok = true; break; }
    r = I.nextUp(r * 1.05 + Number.MIN_VALUE);
  }
  if (!ok) {
    return Object.assign({ ok: false, why: 'no radius verified p(r) < 0 in interval arithmetic', rMin, rMax, disc }, base);
  }
  return Object.assign({ ok: true, r, rMin, rMax, disc, pAtR: pAt(r)[1] }, base);
}

/* ---- Krawczyk enclosure for a finite-dimensional system ----
   F  : (X:interval[]) -> interval[]        the map whose zero is sought
   DF : (X:interval[]) -> interval[][]      its Jacobian over a box
   x0 : number[]                            the numerical candidate
   A  : number[][]                          approximate inverse of DF(x0)
   opts: {rad0, maxRounds, growth, radCap}                                  */
function krawczyk(F, DF, x0, A, opts) {
  opts = opts || {};
  const n = x0.length;
  const maxRounds = opts.maxRounds || 24;
  const Xp = x0.map(v => iv(v));
  const F0 = F(Xp);

  /* d = A F(x0) */
  const d = new Array(n);
  for (let i = 0; i < n; i++) {
    let s = ZERO;
    for (let j = 0; j < n; j++) s = add(s, mul(iv(A[i][j]), F0[j]));
    d[i] = s;
  }
  let rad = new Array(n);
  for (let i = 0; i < n; i++) rad[i] = (opts.rad0 || 0) || (2 * mag(d[i]) + 1e-13 * Math.max(1, Math.abs(x0[i])));

  for (let round = 0; round < maxRounds; round++) {
    const X = x0.map((v, i) => iv(I.nextDown(v - rad[i]), I.nextUp(v + rad[i])));
    const J = DF(X);
    const K = new Array(n);
    let ok = true, maxRad = 0;
    for (let i = 0; i < n; i++) {
      let acc = sub(iv(x0[i]), d[i]);
      for (let j = 0; j < n; j++) {
        let s = ZERO;
        for (let k = 0; k < n; k++) {
          const jk = J[k][j];
          if (jk[0] === 0 && jk[1] === 0) continue;
          s = add(s, mul(iv(A[i][k]), jk));
        }
        let m = [-s[1], -s[0]];
        if (i === j) m = add(ONE, m);
        if (m[0] === 0 && m[1] === 0) continue;
        acc = add(acc, mul(m, sub(X[j], iv(x0[j]))));
      }
      K[i] = acc;
      if (!interior(acc, X[i])) ok = false;
      maxRad = Math.max(maxRad, (acc[1] - acc[0]) / 2);
    }
    if (ok) return { ok: true, box: X, image: K, maxRad, rounds: round + 1 };
    for (let i = 0; i < n; i++) {
      const need = Math.max(Math.abs(K[i][0] - x0[i]), Math.abs(K[i][1] - x0[i]));
      rad[i] = Math.max(rad[i] * (opts.growth || 2), need * 1.1 + 1e-15);
    }
    if (opts.radCap && Math.max.apply(null, rad) > opts.radCap)
      return { ok: false, why: 'no contraction below the radius cap' };
  }
  return { ok: false, why: 'no contraction within the round limit' };
}

module.exports = { radiiPolynomial, krawczyk };
