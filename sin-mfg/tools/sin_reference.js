/* sin_reference.js — headless reference run of the SHIPPED sin-mfg kernel,
   for the cross-language differential (mfglab test_crosslang_continuum.py).

   Pattern of mfglab/tools/js_reference.js: extract the kernel from the
   artifact at run time (never a copy that can go stale), solve, print JSON
   with the artifact's sha256 so the battery records exactly which file the
   Python port was validated against. The Picard mechanics mirror the
   artifact's own driver (theta=0.5, tol 1e-10, cap 250; residual PRE-update),
   identical to test-sin.js Layer A. */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const HTML = process.env.SIN_HTML || path.resolve(__dirname, '..', 'sin-mfg.html');
const html = fs.readFileSync(HTML, 'utf8');
const sha = crypto.createHash('sha256').update(html).digest('hex').slice(0, 16);

const FULL = html.match(/<script>([\s\S]*)<\/script>/)[1];
const MARK = '/* ---------------- canvases (dpr-crisp; logical coordinates) ---------------- */';
const KSRC = FULL.slice(0, FULL.indexOf(MARK));
const EXPORTS = ['NT', 'dt', 'NX', 'hx', 'xs', 'P', 'solveField', 'makeN', 'bisect',
  'clearSlice', 'dispatch', 'dpAudit', 'welfareOf', 'thomas'];
const K = new Function(KSRC + '\nreturn {' + EXPORTS.join(',') + '};')();

const { NT, NX, hx } = K;
const price = new Float64Array(NT).fill(0.8);
let field = null, disp = null, res = 1, it = 0;
for (let k = 0; k < 250; k++) {
  field = K.solveField(price);
  disp = K.dispatch(field.Ux);
  const pNew = disp.sl.map(s => s.p);
  res = 0;
  for (let t = 0; t < NT; t++) res = Math.max(res, Math.abs(pNew[t] - price[t]));
  it++;
  if (res < 1e-10) break;
  for (let t = 0; t < NT; t++) price[t] = 0.5 * price[t] + 0.5 * pNew[t];
}

let massDrift = 0, minM = Infinity;
for (let t = 0; t <= NT; t++) {
  let s = 0;
  for (let i = 0; i < NX; i++) { s += field.m[t][i] * hx; minM = Math.min(minM, field.m[t][i]); }
  massDrift = Math.max(massDrift, Math.abs(s - 1));
}
let clearWorst = 0;
for (let t = 0; t < NT; t++) {
  const s = disp.sl[t];
  clearWorst = Math.max(clearWorst, Math.abs(K.makeN(t, field.Ux[t])(s.p) - s.h + s.k - s.d));
}
const audit = K.dpAudit([...price], field);

console.log(JSON.stringify({
  artifact: HTML, sha256: sha,
  converged: res < 1e-10, iterations: it, residual: res,
  price: [...price], w: disp.w, spill: disp.spill, mix: disp.mix,
  massDrift, minM, clearWorst, eps: audit.eps,
  welfare: K.welfareOf([...price], field, disp),
}));
