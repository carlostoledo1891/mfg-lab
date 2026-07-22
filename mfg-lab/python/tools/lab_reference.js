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
*/
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const LAB = path.resolve(__dirname, '..', '..', 'lab');          // mfglab/tools -> mfg-lab/lab
const FIX = path.resolve(__dirname, '..', '..', 'tests', 'lab-fixtures.js');
const { study } = require(path.join(LAB, 'order-study.js'));
const { map } = require(path.join(LAB, 'failure-map.js'));
const F = require(FIX);

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
  sha256: { orderStudy: sha(path.join(LAB, 'order-study.js')), failureMap: sha(path.join(LAB, 'failure-map.js')), fixtures: sha(FIX) },
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
