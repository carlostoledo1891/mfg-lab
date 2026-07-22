/* report.js — regenerate every number quoted in README.md and in the artifact.
   Prose is a claim; if a number appears in text, it is printed here first.
   MIT licensed. Part of mfg-cap. */
'use strict';
const M = require('../kernel/mfg1d.js');
const V = require('../kernel/validate.js');
const TP = M.TWO_PI;
const f = (x, n) => (x === undefined ? '—' : x.toExponential(n === undefined ? 2 : n));

console.log('== monotone regime (Lasry-Lions applies; uniqueness classical) ==');
for (const [sigma, c, A, N] of [[0.5, 1, 1, 12], [0.5, 1, 1, 16], [0.3, 1, 1, 16], [0.3, 2, 1.5, 20], [1.0, 0.5, 0.5, 12]]) {
  const P = M.makeProblem({ sigma, c, A, N });
  const s = M.solve(P);
  const r = V.validate(s.x, P, { nu: 1.05 });
  const pos = r.ok ? V.certifyPositivity(s.x, P, r.r) : null;
  const rho = M.unpack(s.x, N).rho;
  console.log(`  sigma=${sigma} c=${c} A=${A} N=${N} -> ` +
    (r.ok ? `PROVED r=${f(r.r)}  rho in [${(rho - r.r).toFixed(12)}, ${(rho + r.r).toFixed(12)}]  min m>=${pos.minM.toFixed(6)}  Y0=${f(r.Y0)} Z1=${r.Z1.toFixed(4)} Z2=${f(r.Z2)}`
          : `REFUSED (${r.why})`));
}

console.log('\n== bifurcation of the constant state (V = 0) ==');
const SG = 0.5, N = 20;
const cStar = -SG * SG * TP * TP;
console.log(`  predicted c* = -sigma^2 (2 pi)^2 = ${cStar.toFixed(6)}`);
{
  const P = M.makeProblem({ sigma: SG, c: cStar, A: 0, N });
  const x = new Float64Array(2 * N + 1); x[0] = cStar;
  const r = V.validate(x, P, { nu: 1.02 });
  console.log(`  at c*: the proof ${r.ok ? 'CERTIFIES (this would be a bug)' : 'REFUSES — ' + r.why}`);
}

console.log('\n== anti-monotone regime: certified MULTIPLICITY ==');
const mk = c => M.makeProblem({ sigma: SG, c, A: 0, N });
const c0 = -10.5, nu = 1.02;
const seed = new Float64Array(2 * N + 1); seed[0] = c0; seed[1] = -SG * 0.35; seed[N + 1] = 0.35;
const st = M.solve(mk(c0), { x0: seed, maxIter: 200 });
for (const cT of [-11, -12, -14, -16, -20, -24]) {
  const br = M.continueBranch(mk, c0, cT, 32, st.x);
  if (!br.ok) { console.log(`  c=${cT}: branch lost`); continue; }
  const P = mk(cT);
  const rb = V.validate(br.x, P, { nu });
  const triv = new Float64Array(2 * N + 1); triv[0] = cT;
  const rt = V.validate(triv, P, { nu });
  const un = M.unpack(br.x, N);
  let sep = Math.abs(cT - br.x[0]);
  for (let k = 1; k <= N; k++) {
    sep += 2 * Math.pow(nu, k) * Math.abs(TP * k * un.a[k]);
    sep += 2 * Math.pow(nu, k) * Math.abs(un.b[k]);
  }
  const pos = rb.ok ? V.certifyPositivity(br.x, P, rb.r) : null;
  const disjoint = rb.ok && rt.ok && sep > rb.r + rt.r;
  console.log(`  c=${String(cT).padStart(4)}  branch a1=${un.a[1].toFixed(5)}  ` +
    `r_branch=${f(rb.r)} r_const=${f(rt.r)}  separation=${sep.toFixed(4)}  ` +
    `min m>=${pos ? pos.minM.toExponential(3) : '—'}  ${disjoint ? '=> >=2 SOLUTIONS PROVED' : 'inconclusive'}`);
}
