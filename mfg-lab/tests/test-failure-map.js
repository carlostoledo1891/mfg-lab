/* test-failure-map.js — battery for the Lab's second feature: where does your
   solver stop working (mfg-lab/lab/failure-map.js).

   WHY THIS FIXTURE HAS A DERIVABLE ANSWER, WHICH IS THE POINT
   The map is checked against a boundary that theory fixes in advance rather
   than against whatever it happened to print. Jacobi applied to the shifted
   operator -u'' - k^2 u has iteration matrix with spectral radius

       rho(k) = 2 cos(pi h) / (2 - h^2 k^2),

   which crosses 1 at  k* = 2 sin(pi h / 2) / h  ->  pi  as h -> 0. At n=32
   that is k* = 3.1404. So the map is not merely asked to produce a picture:
   it is asked to bracket a number computed independently of it, and M5 fails
   if the bracket misses.

   THE LOAD-BEARING PAIR
     M1  a box that straddles k* must be REFUSED.
     M6  a box entirely below k* must be PROVED.
   Same kernel, same instrument, same tolerance — only the box moves. A map
   that cannot do both is a map that is not reading anything.

   M7 is the honesty check: the PROVED claim must say SAMPLED, because a grid
   cannot see a failure region thinner than its own spacing, and this file
   asserts that the wording never quietly upgrades a sample to a proof.
*/
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const LAB = path.join(__dirname, '..', 'lab');
const { map, OK, STALLED, DIVERGED, THREW } = require(path.join(LAB, 'failure-map.js'));
const { helmholtz1d, euler1d, explodes } = require('./lab-fixtures.js');

function sha(f) { return crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex').slice(0, 16); }
console.log('== failure-map battery ==');
console.log('   mfg-lab/lab/failure-map.js  sha256:' + sha(path.join(LAB, 'failure-map.js')));

let pass = 0, fail = 0;
function ok(cond, msg) { if (cond) pass++; else { fail++; console.error('   FAIL  ' + msg); } }
function throwsWith(fn, re, msg) {
  try { fn(); ok(false, msg + ' (nothing thrown)'); }
  catch (e) { ok(re.test(e.message), msg + ' (message was "' + e.message + '")'); }
}

/* The independently-computed boundary this battery is checked against. */
const N = 32, H = 1 / N;
const KSTAR = 2 * Math.sin(Math.PI * H / 2) / H;

/* ------------------------------------------- M1-M5 · the straddling box */

const wide = map(helmholtz1d, { sweep: { k: [0.5, 6] }, samples: 12, n: N, tol: 1e-6 });

ok(!wide.certificate.proved, 'M1 a box straddling the failure boundary is REFUSED');
ok(wide.counts.ok === 6 && wide.counts.diverged === 6 && wide.counts.stalled === 0 && wide.counts.threw === 0,
   'M2 outcomes are counted exactly: ' + JSON.stringify(wide.counts));
ok(/bracketed by/.test(wide.certificate.why), 'M2b the refusal hands back the bracket, not just a failure count');

const below = wide.points.filter(p => p.params.k <= 3.0);
const above = wide.points.filter(p => p.params.k >= 3.5);
ok(below.length === 6 && below.every(p => p.outcome === OK), 'M3 every sample below k*=' + KSTAR.toFixed(4) + ' reaches tolerance');
ok(above.length === 6 && above.every(p => p.outcome === DIVERGED), 'M4 every sample above k* diverges (not "stalls" — the taxonomy separates them)');

ok(wide.brackets.length === 1, 'M5a exactly one transition bracket on this box, got ' + wide.brackets.length);
const b = wide.brackets[0];
ok(b && b.from <= KSTAR && KSTAR <= b.to,
   'M5b the bracket [' + (b && b.from) + ', ' + (b && b.to) + '] contains the independently derived k* = ' + KSTAR.toFixed(4));
ok(b && b.fromOutcome === OK && b.toOutcome === DIVERGED, 'M5c the bracket records which way the transition goes');
console.log('   M5  bracket [' + b.from + ', ' + b.to + ']  contains derived k* = ' + KSTAR.toFixed(4) + '  (pi = ' + Math.PI.toFixed(4) + ')');

/* --------------------------------- M6-M9 · the other half of the pair */

const safe = map(helmholtz1d, { sweep: { k: [0.5, 2.5] }, samples: 6, n: N, tol: 1e-6 });
ok(safe.certificate.proved, 'M6 a box entirely below k* is PROVED — the map is not stuck saying no');
ok(safe.brackets.length === 0, 'M6b and reports no bracket, because nothing changed behaviour');
ok(/SAMPLED/.test(safe.certificate.claim) && /not a proof of the box/.test(safe.certificate.claim),
   'M7 the PROVED claim says SAMPLED and disclaims the box — a grid never becomes a proof by being green');
ok(safe.certificate.assumes.some(a => /thinner than the sample spacing/.test(a)),
   'M8 the sampling limitation is an ASSUMPTION on the certificate, not a caveat in prose');
ok(safe.certificate.assumes.some(a => /spacing \(k /.test(a)), 'M8b and it states the actual spacing swept');
ok(safe.certificate.falsifier.length >= 3 && wide.certificate.falsifier.length >= 3,
   'M9 both verdicts carry falsifiers (enforced by eqcert)');

/* ------------------ M10 · slow is not the same answer as divergent */

const slow = map(helmholtz1d, { sweep: { k: [3.05, 3.11] }, samples: 3, n: N, tol: 1e-9 });
ok(slow.points.every(p => p.outcome === STALLED),
   'M10a just below k*, a tight tolerance gives STALLED — converging, out of budget — got ' + slow.points.map(p => p.outcome).join(','));
ok(slow.points.every(p => p.residual > 1e-9 && p.residual < 1),
   'M10b and its residuals sit between the tolerance and 1, which is what distinguishes it from divergence');
ok(/too slowly for the budget/.test(slow.points[0].detail), 'M10c the detail says which of the two it is');

/* ------------------------------- M11 · a kernel that raises, mid-sweep */

const boom = map(explodes, { sweep: { k: [1, 6] }, samples: 6, n: N, tol: 1e-6 });
ok(boom.counts.threw > 0, 'M11a a raising kernel produces THREW points rather than killing the sweep');
ok(boom.points.length === 6, 'M11b every requested point still appears in the result');
ok(boom.points.filter(p => p.outcome === THREW).every(p => /unsupported regime/.test(p.detail)),
   'M11c and the kernel\'s own message is carried through to the user');

/* ------------------------------------- M12 · the sweep spec is checked */

throwsWith(() => map(helmholtz1d, {}), /sweep is required/, 'M12a a missing sweep is rejected');
throwsWith(() => map(helmholtz1d, { sweep: { a: [0, 1], b: [0, 1], c: [0, 1] } }), /one or two parameters/, 'M12b three axes are rejected with a reason');
throwsWith(() => map(helmholtz1d, { sweep: { k: [6, 1] } }), /lo < hi/, 'M12c a reversed range is rejected');
throwsWith(() => map(helmholtz1d, { sweep: { k: [1, 6] }, samples: 1 }), /spot-check/, 'M12d one sample per axis is rejected as the thing this replaces');

/* --------------------------------- M13 · two axes, and the grid indexing */

const grid = map(helmholtz1d, { sweep: { k: [0.5, 6], inert: [0, 1] }, samples: 4, n: N, tol: 1e-6 });
ok(grid.points.length === 16, 'M13a a two-axis sweep visits samples^2 points, got ' + grid.points.length);
ok(grid.axes.length === 2 && grid.axes[0].name === 'k' && grid.axes[1].name === 'inert', 'M13b both axes are labelled and ordered');
/* `inert` is not read by the kernel, so the outcome must depend on k alone.
   A transposed index would break this and nothing else would notice. */
const byK = {};
for (const p of grid.points) (byK[p.params.k] = byK[p.params.k] || []).push(p.outcome);
ok(Object.values(byK).every(v => new Set(v).size === 1),
   'M13c outcomes are constant along the inert axis — which is what catches a transposed grid index');

/* ------------------------------------ M14 · a direct solver has no stall */

const direct = map(euler1d, { sweep: { anything: [0, 1] }, samples: 4, n: 64, tol: 1e-6 });
ok(direct.certificate.proved, 'M14a a direct solver reaches tolerance everywhere (residual null is not a failure)');
ok(direct.points.every(p => p.residual === null), 'M14b and reports no residual at all');

/* Codes — what the cross-language differential compares. */
ok(wide.code === 'POINTS_FAILED' && safe.code === 'PROVED' && boom.code === 'POINTS_FAILED',
   'M15 verdict codes are machine-readable, for the Python differential and for a UI that should not regex a sentence');

console.log('   ' + pass + ' PASS, ' + fail + ' FAIL');
if (fail) { console.error('failure-map battery FAILED'); process.exit(1); }
