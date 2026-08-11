/* js_reference.js — solve the Wardrop scenarios with the SHIPPED JS kernel and
   print the certified totals as JSON, for the Python cross-language test.

   It extracts the MWD kernel FROM mfg-lab.html at run time (the same extraction
   test-wardrop-diff.js uses), so the Python port is validated against the kernel
   actually shipped in the artifact — not a copy. Chain:
   Python ↔ (here) shipped JS ↔ dev battery (test-wardrop-diff.js) ↔ paper.

   Usage: node js_reference.js            # prints JSON for S1/S2/S3
   Output: {"artifact":"/abs/path","sha256":"...",
            "S1":{"totals":[...],"gap":...}, "S2":{...}, "S3":{...}}

   `artifact` and `sha256` are the provenance pair, and BOTH are needed. A sha
   alone says only that some file was hashed; it never says whose. The consumer
   (test_crosslang.py) re-hashes `artifact` itself and checks the result is in
   the shipped export set, so this reference cannot validate a file the project
   does not publish. Emit the path whenever you change this output shape.
*/
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

/* M5a, 2026-07-28 — THE TWO TREES STOPPED HAVING THE SAME SHAPE FROM HERE, and that is new.
   This join was `'..','..','index.html'`: a sibling reach that was correct in BOTH trees,
   because the package sat at academic/mfg-lab/python/tools in the monorepo and at
   mfg-lab/python/tools in the export, so two levels up landed on mfg-lab/ either way. The
   package now sits at python/tools in BOTH trees, so two levels up is the TREE ROOT — and
   mfg-lab/ hangs off `academic/` here but off the root there. NO SINGLE `..` COUNT IS RIGHT
   IN BOTH PLACES ANY MORE, so the two trees are enumerated and the first that exists wins.
   This file SHIPS, so the export branch is not hypothetical; and a wrong answer here is
   invisible to every gate that runs in this repo, because it only breaks in the exported
   tree, which nobody runs on a normal day. Same shape, same reason, in lab_reference.js. */
const ROOT = path.resolve(__dirname, '..', '..');       // python/tools -> the tree root
/* 2026-07-29: the monorepo candidate is research/mfg-lab (every unit is a paper or report inside
   research/); the export stays flat at mfg-lab/. The retired academic/ candidate is REMOVED rather
   than left as a third option — a candidate that can never match is indistinguishable from one that
   stopped matching, which is how a two-tree list rots into a one-tree list nobody notices. */
/* AMENDED 2026-08-08 (REBUILD_PLAN phase 2): the monorepo candidate is site/mfg-lab, because
   every page now lives at its route and site/ publishes at the export root. The monorepo
   path is therefore the export path with `site/` in front of it, which is the first time
   these two candidates have differed by a prefix instead of by a rename. */
const MFGLAB_DIR = [path.join(ROOT, 'site', 'mfg-lab'),  /* the monorepo: site/<route> */
                    path.join(ROOT, 'mfg-lab')]              /* the flat exported tree */
                   .find(d => fs.existsSync(d)) || path.join(ROOT, 'mfg-lab');
const HTML = path.resolve(process.env.MFG_HTML || path.join(MFGLAB_DIR, 'index.html'));
if (!fs.existsSync(HTML)) {
  /* This is a MISSING FILE, not a failed assertion — say so, instead of dying in
     an ENOENT stack trace that reads like a bug in fs. js_reference.js exists to
     run the SHIPPED Wardrop kernel; with no artifact there is nothing to run and
     nothing to certify. If the artifact MOVED, re-point the default path above
     (and MFG_HTML, if that is what set it). If it was DELETED, this reference and
     the Python cross-language test that consumes it must be retired deliberately
     — not left to crash, and never left to pass. */
  console.error('js_reference.js: artifact not found at ' + HTML);
  console.error('  expected the shipped mfg-lab artifact; MFG_HTML=' +
    (process.env.MFG_HTML || '(unset)'));
  process.exit(2);
}
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
  artifact: HTML,
  sha256: sha,
  S1: solve(1, 2, 100, 100, 1e-8, 6000),
  S2: solve(2, 2, 100, 50, 1e-8, 6000),
  S3: solve(3, 2, 100, 50, 1e-7, 12000),
};
process.stdout.write(JSON.stringify(out));
