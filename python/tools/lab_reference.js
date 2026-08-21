/* lab_reference.js — run the JavaScript Lab instruments on the shared fixtures
   and print the results as JSON, for the Python cross-language test.

   WHAT THIS PINS. The Lab has two implementations of each instrument: the JS
   one the browser runs, and the Python one `pip install mfg-lab` provides. The
   web Lab lets a user switch between them, so "they agree" cannot be a claim in
   a README — it has to be a gate. This file is one half of it.

   WHAT IS COMPARED, AND WHY IT IS THE CODE AND NOT THE PROSE. Refusal messages
   are written for a human and are allowed to read differently in each language.
   The DECISION is not: every refusal carries a machine-readable code, and the
   differential compares codes exactly, plus the numbers underneath them.

   Cases use levels [16,32,64] rather than the fixtures' default [16,32,64,128].
   Cost, and nothing else: the n=128 solve at the tightened tolerance takes
   ~90k Jacobi iterations in each language, and the differential is a test of
   AGREEMENT, not of coverage — the per-language batteries carry the finest
   grid. Stated here so the choice is visible rather than inferred.

   Usage: node lab_reference.js       # prints JSON on stdout
   Output: {"artifacts":{"orderStudy":"/abs/path",...},
            "sha256":{"orderStudy":"...",...},"studies":{...},"maps":{...}}

   `artifacts` and `sha256` are the provenance pair, and BOTH are needed. A sha
   alone says only that some file was hashed; it never says whose. The consumer
   (test_crosslang_lab.py) re-hashes every `artifacts` path itself and checks
   each one is in the shipped export set, so this reference cannot certify the
   Python twin against files the project does not publish. Emit the paths
   whenever you change this output shape.
*/
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

/* The overrides exist so the gate can be PROVED RED against an unshipped copy
   — point MFG_LAB_DIR at .work/public/lab and every number still agrees
   perfectly, because the bytes are identical; only the provenance check
   notices. They are not a way to aim the differential elsewhere: the consumer
   rejects any path outside the export set, however it was set. */
/* M5a, 2026-07-28 — the package moved academic/mfg-lab/python -> python/, so `'..','..'` is
   the TREE ROOT now rather than academic/mfg-lab/. Both defaults below are re-derived from
   this file's OWN new depth, and neither literal appears in any grep for the old path.
   THE TWO TREES NO LONGER AGREE from here: mfg-lab/ hangs off `academic/` in the monorepo and
   off the root in the export, while this file is at python/tools in both. So the tracks are
   ENUMERATED rather than counted — see the long note in js_reference.js. This file SHIPS, so
   the export branch is real, and a wrong answer is invisible to every gate that runs here. */
const ROOT = path.resolve(__dirname, '..', '..');       // python/tools -> the tree root
/* AMENDED AGAIN 2026-08-21 (the structure migration), and this time the branch is DELETED rather
   than repointed. The two candidates existed because the monorepo and the export spelled this
   directory differently — research/mfg-lab, then site/mfg-lab, against a flat mfg-lab/ in the
   export. Source path and published path are the same string now, so there is one spelling and a
   two-entry list whose second entry can never be chosen would only mislead the next reader. */
const MFGLAB_DIR = path.join(ROOT, 'research', 'mfg-lab');
/* M5b, 2026-07-28: the instruments moved to lab/ at the TREE ROOT, so this one needs NO
   two-tree branch — python/tools and lab/ are both root-relative in the monorepo and in the
   export, which is exactly the property MFGLAB_DIR above exists to work around for the two
   things that did NOT move (the artifact and the fixtures). */
const LAB = path.resolve(process.env.MFG_LAB_DIR || path.join(ROOT, 'lab'));
const FIX = path.resolve(process.env.MFG_LAB_FIXTURES ||
                         path.join(MFGLAB_DIR, 'tests', 'lab-fixtures.js'));
                                    // the fixtures stay in research/mfg-lab/tests/, which does NOT move

/* role -> the ABSOLUTE path read for it. ONE object, so the sha map, the
   emitted provenance and the requires below cannot name different files. */
const SRC = {
  orderStudy: path.join(LAB, 'order-study.js'),
  failureMap: path.join(LAB, 'failure-map.js'),
  fixtures: FIX,
};
for (const role of Object.keys(SRC)) {
  if (!fs.existsSync(SRC[role])) {
    /* A MISSING FILE, not a failed assertion — say so, instead of dying in a
       MODULE_NOT_FOUND stack that reads like a bug in require. If the file
       MOVED, re-point the default above; if it was DELETED, this reference and
       the Python differential that consumes it must be retired deliberately —
       not left to crash, and never left to pass. */
    console.error('lab_reference.js: ' + role + ' not found at ' + SRC[role]);
    console.error('  MFG_LAB_DIR=' + (process.env.MFG_LAB_DIR || '(unset)') +
      '  MFG_LAB_FIXTURES=' + (process.env.MFG_LAB_FIXTURES || '(unset)'));
    process.exit(2);
  }
}

const { study } = require(SRC.orderStudy);
const { map } = require(SRC.failureMap);
const F = require(SRC.fixtures);

const sha = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex').slice(0, 16);

const LEVELS = [16, 32, 64];

function studyCase(kernel, opts) {
  const r = study(kernel, opts);
  return {
    code: r.code,
    order: r.order,
    table: r.table.map(t => ({ n: t.n, error: t.error, iters: t.iters, iterMove: t.iterMove })),
    worstRatio: r.worstRatio === undefined ? null : r.worstRatio,
    proved: r.certificate.proved
  };
}

function mapCase(kernel, opts) {
  const r = map(kernel, opts);
  return {
    code: r.code,
    counts: r.counts,
    outcomes: r.points.map(p => p.outcome),
    residuals: r.points.map(p => (p.residual === null || !isFinite(p.residual)) ? null : p.residual),
    brackets: r.brackets.map(b => ({ axis: b.axis, from: b.from, to: b.to, fromOutcome: b.fromOutcome, toOutcome: b.toOutcome })),
    proved: r.certificate.proved
  };
}

const out = {
  artifacts: SRC,
  sha256: { orderStudy: sha(SRC.orderStudy), failureMap: sha(SRC.failureMap), fixtures: sha(SRC.fixtures) },
  studies: {
    clean_second_order:  studyCase(F.poisson1d,      { tol: 1e-9, levels: LEVELS }),
    clean_first_order:   studyCase(F.euler1d,        { tol: 1e-9, levels: LEVELS }),
    contaminated:        studyCase(F.poisson1d,      { tol: 1e-3, levels: LEVELS }),
    contaminated_masked: studyCase(F.poisson1d,      { tol: 1e-3, levels: LEVELS, __unsafeSkipContaminationTest: true }),
    floored_undeclared:  studyCase(F.stalled,        { tol: 1e-9, levels: LEVELS }),
    floored_declared:    studyCase(F.stalled,        { tol: 1e-9, levels: LEVELS, expectedOrder: 2 }),
    spread_too_wide:     studyCase(F.preAsymptotic,  { tol: 1e-9, levels: [16, 32, 64, 128] }),
    too_few_levels:      studyCase(F.poisson1d,      { tol: 1e-9, levels: [32, 64] })
  },
  maps: {
    straddling: mapCase(F.helmholtz1d, { sweep: { k: [0.5, 6] }, samples: 12, n: 32, tol: 1e-6 }),
    safe:       mapCase(F.helmholtz1d, { sweep: { k: [0.5, 2.5] }, samples: 6, n: 32, tol: 1e-6 }),
    raising:    mapCase(F.explodes,    { sweep: { k: [1, 6] }, samples: 6, n: 32, tol: 1e-6 })
  }
};

process.stdout.write(JSON.stringify(out));
