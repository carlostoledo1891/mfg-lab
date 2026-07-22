/* test-order-study.js — battery for the Lab's first feature: a convergence
   study that refuses to lie (mfg-lab/lab/order-study.js).

   WHAT MAKES THIS BATTERY WORTH ANYTHING
   A study that reports "order 2" for a second-order scheme proves almost
   nothing — so does a study with the honesty machinery deleted. The load-
   bearing checks here are the ones where the study must REFUSE:

     S3  a genuinely second-order scheme, run at a slack iteration tolerance,
         must be refused rather than credited with an order.
     S4  the SAME run with the contamination test disabled must come back
         PROVED — and with an order that is visibly NOT the true one. That is
         this file proving, executably, that the check is what did the work
         and that its absence produces a confident wrong answer.
     S5  a scheme carrying a fixed modelling error must be refused against a
         DECLARED order — the case both other rules are blind to, because its
         errors keep falling and its spread stays narrow.

   S4 is the one to read if you read one. It prints the wrong number the tool
   would have printed, which is the number every hand-rolled convergence table
   is at risk of printing.

   Kernels, each chosen to force a different branch:
     poisson1d   -u'' = f, Dirichlet, central differences, Jacobi.
                 Truncation O(h^2) -> order 2. A linearly-converging solver,
                 so the iteration tolerance genuinely moves the answer, which
                 is what makes the contamination test demonstrable at all.
     euler1d     u' = f, u(0)=0, explicit Euler, direct (no iteration).
                 Global error O(h) -> order 1, and exactly zero iteration
                 movement — the control for the contamination test.
     stalled     poisson1d plus a fixed function-sized modelling error, the
                 shape of a dropped term or a wrong boundary condition. Errors
                 still fall monotonically; the order collapses toward zero.
     preAsymptotic
                 a synthetic fixture with a PRESCRIBED error sequence (no PDE
                 solved), whose only job is to force the interval-width branch.
                 Written because a correct-but-untested branch is one refactor
                 from wrong, and no physical kernel here reaches that branch.
*/
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const LAB = path.join(__dirname, '..', 'lab');
const { validate, ContractError } = require(path.join(LAB, 'contract.js'));
const { study } = require(path.join(LAB, 'order-study.js'));

/* Print what was validated, per house practice: a battery that does not say
   which bytes it read is one edit away from certifying a stale file. */
function sha(f) { return crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex').slice(0, 16); }
console.log('== order-study battery ==');
for (const f of ['contract.js', 'order-study.js'])
  console.log('   ' + path.join('mfg-lab/lab', f) + '  sha256:' + sha(path.join(LAB, f)));

let pass = 0, fail = 0;
function ok(cond, msg) {
  if (cond) { pass++; }
  else { fail++; console.error('   FAIL  ' + msg); }
}
function throws(fn, wantField, msg) {
  try { fn(); ok(false, msg + ' (expected a ContractError, none thrown)'); }
  catch (e) {
    if (!(e instanceof ContractError)) { ok(false, msg + ' (threw ' + e.constructor.name + ': ' + e.message + ')'); return; }
    ok(wantField ? e.field === wantField : true, msg + ' (field was "' + e.field + '", wanted "' + wantField + '")');
  }
}

/* Kernels live in lab-fixtures.js, shared with the failure-map battery — two
   copies of a linearly-converging solver would drift exactly the way this
   house gates against one level down. Each fixture's design notes, including
   the two fixture bugs that shaped them, are in that file. */
const { poisson1d, euler1d, stalled, preAsymptotic } = require('./lab-fixtures.js');

/* ------------------------------------------------------ C · the contract */

ok(validate(poisson1d).name === poisson1d.name, 'C1 validate accepts a conforming kernel');
ok(validate(poisson1d).length === 15, 'C1b validate reports the smallest-level vector length (n=16 -> 15 interior)');

throws(() => validate(Object.assign({}, poisson1d, { name: '' })), 'name', 'C2a empty name rejected');
throws(() => validate(Object.assign({}, poisson1d, { solve: undefined })), 'solve', 'C2b missing solve rejected');
throws(() => validate(Object.assign({}, poisson1d, { exact: undefined })), 'exact', 'C2c missing exact rejected');
throws(() => validate(Object.assign({}, poisson1d, { levels: [] })), 'levels', 'C2d empty levels rejected');
throws(() => validate(Object.assign({}, poisson1d, { levels: [16, 16, 32] })), 'levels', 'C2e duplicate level rejected');
throws(() => validate(Object.assign({}, poisson1d, { levels: [16, 32.5] })), 'levels', 'C2f non-integer level rejected');
throws(() => validate(Object.assign({}, poisson1d, { norm: 'l1' })), 'norm', 'C2g unknown norm rejected');

/* The checks a typeof-only contract would pass. */
throws(() => validate(Object.assign({}, poisson1d, { solve: () => { throw new Error('boom'); } })), 'solve',
  'C3 a solve() that throws is caught at validation, not four solves into a study');
throws(() => validate(Object.assign({}, poisson1d, { solve: () => ({ u: [1, NaN, 3] }) })), 'exact',
  'C4 a solve() returning the wrong length is caught (length mismatch against exact)');
throws(() => validate(Object.assign({}, poisson1d, { exact: () => 'nope' })), 'exact()',
  'C5 an exact() returning a non-vector is caught');
throws(() => validate(Object.assign({}, poisson1d, { h: () => 0 })), 'h', 'C6 a non-positive mesh size is caught');

/* -------------------------------------------------- S · the study, clean */

const s1 = study(poisson1d, { tol: 1e-9 });
ok(s1.certificate.proved, 'S1a second-order scheme at a tight tolerance is PROVED');
ok(s1.order && s1.order[0] > 1.5 && s1.order[1] < 2.5,
   'S1b order interval identifies 2 (distinguishes it from 1 and 3) — got ' + JSON.stringify(s1.order && s1.order.map(x => +x.toFixed(3))));
ok(s1.table.length === 4, 'S1c every level appears in the table');
ok(s1.certificate.falsifier.length >= 3, 'S1d the PROVED certificate carries its falsifiers');
ok(s1.certificate.assumes.some(a => /reference solution/.test(a)),
   'S1e the manufactured-solution assumption is declared, since nothing can check it');
console.log('   S1  poisson1d order interval  [' + s1.order.map(x => x.toFixed(4)).join(', ') + ']   ' +
            'worst iter/grid move ' + s1.worstRatio.toExponential(2));

const s2 = study(euler1d, { tol: 1e-9 });
ok(s2.certificate.proved, 'S2a first-order direct scheme is PROVED');
ok(s2.order && s2.order[0] > 0.5 && s2.order[1] < 1.5,
   'S2b order interval identifies 1 — got ' + JSON.stringify(s2.order && s2.order.map(x => +x.toFixed(3))));
ok(s2.worstRatio === 0, 'S2c a direct solver has exactly zero iteration movement');
console.log('   S2  euler1d   order interval  [' + s2.order.map(x => x.toFixed(4)).join(', ') + ']');

/* ------------------------------- S3/S4 · THE LOAD-BEARING PAIR (see header) */

/* A slack tolerance. Same scheme, same kernel, same grids — only the stopping
   criterion changes, which is exactly the substitution that produced this
   repository's own retracted "order". 1e-3 is not a magic number: it is simply
   loose enough that Jacobi has not resolved the discretization error by the
   time it stops, which was MEASURED before being written here. */
const SLACK = 1e-3;

const s3 = study(poisson1d, { tol: SLACK });
ok(!s3.certificate.proved, 'S3a a second-order scheme at a slack tolerance is NOT credited with an order');
ok(s3.certificate.verdict === 'REFUSED', 'S3b the verdict is REFUSED, not merely unproved');
ok(/STOPPING CRITERION/.test(s3.certificate.why), 'S3c the refusal names the cause (stopping criterion), not just "failed"');
ok(s3.certificate.falsifier.length >= 3, 'S3d the REFUSED certificate carries falsifiers too');
console.log('   S3  refused: ' + s3.certificate.why.slice(0, 96).replace(/\s+/g, ' ') + '…');

const s4 = study(poisson1d, { tol: SLACK, __unsafeSkipContaminationTest: true });
ok(s4.certificate.proved, 'S4a with the contamination test DISABLED the same run is PROVED — the check is what refused, nothing else');
ok(s4.order !== null, 'S4b and it produces a confident order interval');
ok(!(s4.order[0] > 1.5 && s4.order[1] < 2.5),
   'S4c that order is NOT the true order 2 — the disabled check was preventing a wrong answer, not a missing one. Got ' +
   JSON.stringify(s4.order.map(x => +x.toFixed(3))));
ok(s4.certificate.assumes.some(a => /DISABLED/.test(a)),
   'S4d a certificate produced with the test disabled says so loudly and can never pass as a normal result');
console.log('   S4  WITH THE CHECK OFF the tool would have reported order [' +
            s4.order.map(x => x.toFixed(3)).join(', ') + '] for a scheme whose true order is 2.');

/* --------------------------------------------- S5+ · the other refusals */

/* The pair that shows what DECLARING an order buys. Same kernel, same data,
   same run — the only difference is whether the user said what they expected. */
const s5undeclared = study(stalled, { tol: 1e-9 });
ok(s5undeclared.certificate.proved, 'S5a undeclared, the stalled kernel is PROVED — its errors do fall, its solver is not the limit, and every rule so far is satisfied');
ok(s5undeclared.order[1] < 0.5, 'S5b and the order it reports collapses toward zero — true, and exactly the kind of true statement a tired reader skims. Got ' + JSON.stringify(s5undeclared.order.map(x => +x.toFixed(3))));

const s5 = study(stalled, { tol: 1e-9, expectedOrder: 2 });
ok(!s5.certificate.proved, 'S5c DECLARING order 2 turns the same data into a refusal');
ok(/declared order 2/.test(s5.certificate.why), 'S5d and the refusal names the contradiction with a number attached');
ok(/FLOOR/.test(s5.certificate.why), 'S5e and explains the mechanism (an error floor: dropped term, wrong BC, wrong reference)');
ok(Object.keys(s5.certificate.evidence).length > 0, 'S5f the refusal carries its evidence');
console.log('   S5  undeclared -> PROVED order [' + s5undeclared.order.map(x => x.toFixed(3)).join(', ') +
            ']   ·   declared 2 -> REFUSED');

/* The width branch, forced by a synthetic fixture (see the kernel note). */
const s5w = study(preAsymptotic, { tol: 1e-9 });
ok(!s5w.certificate.proved, 'S5g a spread wider than 1 supports no order claim');
ok(/wider than 1/.test(s5w.certificate.why), 'S5h refused on the width rule, naming it');
ok(/adjacent integer orders/.test(s5w.certificate.why), 'S5i and giving the reason the threshold is 1 rather than a picked number');

/* The clean case with a declaration: the check must also be able to say yes. */
const s5ok = study(poisson1d, { tol: 1e-9, expectedOrder: 2 });
ok(s5ok.certificate.proved, 'S5j a correct scheme with a correct declaration is PROVED — the declared-order test is not a one-way ratchet');
ok(/consistent with the declared order 2/.test(s5ok.certificate.claim), 'S5k and the claim states what was checked');

const s6 = study(poisson1d, { tol: 1e-9, levels: [32, 64] });
ok(!s6.certificate.proved, 'S6a two levels cannot produce an order');
ok(/three levels/.test(s6.certificate.why), 'S6b and the refusal explains why two is not enough');

/* A kernel whose "solution" IS the reference: error exactly zero. A study that
   divided by it would emit Infinity or NaN and call it an order. */
const perfect = Object.assign({}, poisson1d, { name: 'perfect', solve: a => ({ u: poisson1d.exact(a), iters: 0, residual: 0 }) });
const s7 = study(perfect, { tol: 1e-9 });
ok(!s7.certificate.proved, 'S7a a zero error is refused rather than turned into an infinite order');
ok(/exactly zero/.test(s7.certificate.why), 'S7b and the refusal explains what it usually means');

/* Structural: eqcert refuses to build a certificate without a falsifier, so
   every path out of study() must have gone through that constructor. */
for (const [nm, s] of [['s1', s1], ['s3', s3], ['s5', s5], ['s6', s6], ['s7', s7]])
  ok(Array.isArray(s.certificate.falsifier) && s.certificate.falsifier.length > 0,
     'S8 ' + nm + ' certificate carries a falsifier (enforced by eqcert, not by convention)');

ok(s1.certificate.provenance.tol === 1e-9 && s1.certificate.provenance.norm === 'l2',
   'S9 provenance records the tolerance and norm the claim depends on');

/* Machine-readable refusal codes. These are what the Python twin is held to by
   the cross-language differential — the same DECISION, not the same English —
   so every branch must carry the code the differential expects. */
const CODES = [[s1, 'PROVED'], [s2, 'PROVED'], [s3, 'ITERATION_CONTAMINATION'],
               [s4, 'PROVED'], [s5undeclared, 'PROVED'], [s5, 'DECLARED_ORDER_MISMATCH'],
               [s5w, 'SPREAD_TOO_WIDE'], [s5ok, 'PROVED'], [s6, 'TOO_FEW_LEVELS'], [s7, 'ZERO_ERROR']];
for (const [r, want] of CODES)
  ok(r.code === want, 'S10 refusal/verdict code is ' + want + ', got ' + r.code);
ok(s3.certificate.evidence['refusal code'] === 'ITERATION_CONTAMINATION',
   'S10b and the code travels inside the certificate, so a saved report keeps it');

/* ------------------------------------------------------------------ report */

console.log('   ' + pass + ' PASS, ' + fail + ' FAIL');
if (fail) { console.error('order-study battery FAILED'); process.exit(1); }
