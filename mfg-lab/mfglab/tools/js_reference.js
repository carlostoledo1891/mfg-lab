/* js_reference.js — solve the Wardrop scenarios with the SHIPPED JS kernel and
   print the certified totals as JSON, for the Python cross-language test.

   It extracts the MWD kernel FROM mfg-lab.html at run time (the same extraction
   test-wardrop-diff.js uses), so the Python port is validated against the kernel
   actually shipped in the artifact — not a copy. Chain:
   Python ↔ (here) shipped JS ↔ dev battery (test-wardrop-diff.js) ↔ paper.

   Usage: node js_reference.js            # prints JSON for S1/S2/S3
   Output: {"S1":{"totals":[...],"gap":...}, "S2":{...}, "S3":{...}, "sha256":"..."}
*/
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const HTML = process.env.MFG_HTML ||
  path.resolve(__dirname, '..', '..', 'mfg-lab.html');   // mfglab/tools -> mfg-lab/
const html = fs.readFileSync(HTML, 'utf8');
const sha = crypto.createHash('sha256').update(html).digest('hex').slice(0, 16);

const OPEN = 'const MWD=(()=>{';
const DOM = 'const cvG=$(';
const iOpen = html.indexOf(OPEN);
const iDom = html.indexOf(DOM, iOpen);
if (iOpen < 0 || iDom < iOpen) { console.error('MWD module not found in ' + HTML); process.exit(2); }
const mwdSrc = html.slice(iOpen + OPEN.length, iDom);

const API = ['makeSystem', 'interiorStart', 'integrate', 'polish', 'wardropGap',
  'totals', 'kirchhoffRes', 'totalsKKTGap'];
const K = new Function(mwdSrc + '\nreturn {' + API.join(',') + '};')();

function solve(scen, wT, Q1, Q2, tol, maxSteps) {
  const sys = K.makeSystem(scen, wT, Q1, Q2);
  const th1 = K.interiorStart(sys.P1, null);
  const th2 = K.interiorStart(sys.P2, null);
  K.integrate(sys, th1, th2, { tol, maxSteps });
  const pol = K.polish(sys, th1, th2);
  return {
    totals: Array.from(K.totals(sys, th1, th2)),
    gap: K.wardropGap(sys, th1, th2),
    kirch: Math.max(K.kirchhoffRes(sys.P1, th1), K.kirchhoffRes(sys.P2, th2)),
    polished: !!pol,
  };
}

const out = {
  sha256: sha,
  S1: solve(1, 2, 100, 100, 1e-8, 6000),
  S2: solve(2, 2, 100, 50, 1e-8, 6000),
  S3: solve(3, 2, 100, 50, 1e-7, 12000),
};
process.stdout.write(JSON.stringify(out));
