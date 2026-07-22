/* order-study.js — a convergence study that REFUSES TO LIE.

   THE PAIN. Essentially every computational paper contains a convergence
   table: solve at h, h/2, h/4, take log2 of the error ratios, report the
   observed order. Almost none of them check whether the number they just
   computed is the discretization order at all — because if the solver stopped
   iterating before the discretization error was resolved, the table measures
   the STOPPING CRITERION and reports it as a property of the scheme.

   This is not hypothetical here. This repository published "|eps| ~ (h+dt)^1.1"
   and then measured apparent slopes from -1.9 to +2.6 across five parameter
   sets. The cause was exactly this: eps was measured at a fixed iteration
   tolerance, the residual stalled near 1e-6 on every grid, and the refinement
   study measured ITERATION error while everyone read it as an order.
   `mfg-lab/docs/FINDINGS.md` has the full account. This file is that lesson
   made mechanical, so nobody has to learn it the way we did.

   THE TEST, AND WHY IT NEEDS NO FABRICATED CONSTANT
   The tempting check is "residual must be much smaller than the error". It is
   not available: the residual of the equation and the error in the solution
   have different units, and relating them needs a stability constant nobody
   has. Any threshold written down here would be a fabricated floor, which is
   a thing this house has retracted twice.

   So the study measures instead of asserting. At each level it solves TWICE —
   once at your tolerance, once at a much tighter one — and asks:

       does tightening the solver move the answer as much as refining the grid?

   If it does, the study is measuring iteration error and it says so and stops.
   The comparison is between two quantities in the same units, both measured on
   the same problem, and it involves no constant at all. That is the whole idea.

   WHAT IS REPORTED IS AN INTERVAL, NOT A SLOPE
   A single pair of grids always yields a number, and that number is the most
   over-quoted quantity in computational science. This study reports
   [min, max] over every consecutive pair. A wide interval is information —
   it means you are not in the asymptotic range yet — and it cannot be mistaken
   for precision the data does not have.

   MIT licensed. Part of the MFG Lab. */
'use strict';

const { validate, errorOf } = require('./contract.js');
const { proved, refused } = require('../../eqcert/src/certificate.js');

/* Tightening factor for the second solve at each level. This is an
   EXPERIMENTAL DESIGN choice, not a threshold that any verdict compares
   against: no criterion below contains it. It must simply be large enough
   that the tight solve is meaningfully closer to the converged answer than
   the working one. If the tight solve is itself iteration-limited the test
   understates contamination, which is why that is declared as an assumption
   on every certificate this file produces rather than hidden. */
const TIGHTEN_BY = 1e-3;

/* THE ONE RESOLUTION CONSTANT, DERIVED ONCE AND USED TWICE.

   Orders are read in practice by distinguishing adjacent integers: is this
   scheme first order or second? So the resolution any order claim needs is
   half the gap between neighbours. That single derivation fixes both places
   this file compares orders to anything:

     · an observed spread wider than 2*RESOLUTION cannot separate 1 from 2,
       so it supports no order claim at all;
     · a declared order further than RESOLUTION from the whole observed
       interval is contradicted by the data; anything closer is not
       distinguishable from it and the study says "consistent with", which is
       a weaker claim than equality and is the one the evidence supports.

   It is emphatically NOT a tolerance on a residual, and nothing here compares
   a computed quantity against it — it is a statement about what an order
   claim is FOR. Strict containment was tried first and is wrong: a genuinely
   second-order scheme measures [1.9995, 1.9999] at finite h, because the true
   order is the LIMIT of the pairwise orders, not a member of them. */
const RESOLUTION = 0.5;

const FALSIFIERS = [
  'a kernel whose error stops decreasing under refinement (the study refuses instead of fitting a slope through it)',
  'a kernel where tightening the iteration tolerance moves the error by as much as refining the grid does',
  'pairwise orders spanning more than 1, which cannot distinguish adjacent integer orders',
  'an order you declared that sits further than half an order from everything the study observed',
  'fewer than three levels, which cannot produce an order interval',
  'a reference solution that is not a solution of the continuous problem — this the study cannot detect, and it is declared as an assumption'
];

const ASSUMPTIONS = [
  'the tightened solve is itself converged; if it is not, contamination is UNDERSTATED',
  'the supplied reference solution solves the continuous problem (manufacture it, do not guess it) — nothing here can check this',
  'the error is measured in the discrete grid norm named in the evidence, and that norm is the one the claimed order refers to'
];

/* One level of the study: solve twice, and report the error YOUR setup
   produces — at YOUR working tolerance — with the tightened solve used only
   as a probe of how far that is from converged.

   The direction matters and was chosen deliberately. Reporting the tightened
   error instead would quietly hand the user a better answer than their own
   configuration produces, and the study would then be certifying a
   computation nobody ran. The point is to characterise the setup in front of
   us, and to refuse when that setup cannot support an order claim. */
function runLevel(K, n, tol) {
  const h = K.h(n);
  const ex = K.exact({ n, params: K.params });

  const working = K.solve({ n, tol, params: K.params });
  const tight = K.solve({ n, tol: tol * TIGHTEN_BY, params: K.params });

  const eWorking = errorOf(working.u, ex, h, K.norm);
  const eTight = errorOf(tight.u, ex, h, K.norm);

  return {
    n, h,
    error: eWorking,
    errorAtTightTol: eTight,
    iterMove: Math.abs(eWorking - eTight),   /* how much the SOLVER moved it */
    iters: working.iters,
    residual: working.residual
  };
}

/* opts:
     tol      working iteration tolerance (default 1e-6)
     levels   override the kernel's levels
     __unsafeSkipContaminationTest
              Exists for ONE reason: the battery must be able to show that the
              contamination test is load-bearing, by disabling it and watching
              a REFUSED verdict become PROVED. Any certificate produced with it
              set carries a loud assumption saying so, so it can never quietly
              look like a normal result. Never set it anywhere else. */
function study(kernel, opts) {
  opts = opts || {};
  const K = validate(kernel);
  const levels = opts.levels ? opts.levels.slice().sort((a, b) => a - b) : K.levels;
  const tol = opts.tol === undefined ? 1e-6 : opts.tol;
  const skipContam = !!opts.__unsafeSkipContaminationTest;

  /* DECLARE WHAT YOU BELIEVE, AND LET THE STUDY TRY TO FALSIFY IT.
     Optional, and the single most useful thing a user can supply. Without it
     the study can only report what it measured — and "the observed order is
     0.0 to 0.4" is a true statement that a tired reader will skim past. With
     it, the same data becomes a REFUSAL naming the contradiction. It is the
     eqcert idea moved up one level: a claim is worth more when its author
     also supplies the thing that would sink it. */
  const expected = opts.expectedOrder;
  if (expected !== undefined && (!Number.isFinite(expected) || expected <= 0))
    throw new Error('study: expectedOrder must be a positive finite number, got ' + expected);

  const assumes = ASSUMPTIONS.slice();
  if (skipContam) assumes.unshift('THE ITERATION-CONTAMINATION TEST WAS DISABLED for this run — the order below may be a property of the stopping criterion rather than of the scheme');
  if (expected === undefined) assumes.push('no expected order was declared, so the study reports what it measured and cannot tell you whether that is what your scheme should deliver');

  const base = { claim: expected === undefined
                   ? 'the observed order of accuracy of ' + K.name + ' lies in the reported interval'
                   : 'the observed order of accuracy of ' + K.name + ' is consistent with the declared order ' + expected,
                 falsifier: FALSIFIERS, assumes,
                 provenance: { kernel: K.name, norm: K.norm, tol, tightenBy: TIGHTEN_BY,
                               expectedOrder: expected === undefined ? '(none declared)' : expected } };

  /* Every refusal carries a machine-readable CODE alongside its prose. The
     prose is for the person; the code is what the cross-language differential
     compares, so the Python twin can be held to the same DECISION without
     being held to the same English. It also gives a UI something to branch on
     that is not a regex over a sentence. */
  const table = [];
  const refuse = (code, why, evidence) => ({
    code,
    certificate: refused(Object.assign({}, base, { why, evidence: Object.assign({ 'refusal code': code }, evidence || {}) })),
    /* A refusal hands back the table it measured. "We will not call this an
       order, and here is exactly what we saw" is actionable; a bare reason is
       an argument the user cannot check. */
    levels, order: null, table
  });

  if (levels.length < 3)
    return refuse('TOO_FEW_LEVELS', 'a convergence study needs at least three levels to report an order INTERVAL; ' +
                  levels.length + ' given. Two levels always produce a number, and that number is not evidence.');

  /* ---- run every level ---- */
  for (const n of levels) {
    const row = runLevel(K, n, tol);
    if (!Number.isFinite(row.error))
      return refuse('NON_FINITE_ERROR', 'the error at n=' + n + ' is not finite (' + row.error + ') — the solve did not produce a usable answer', { level: n });
    if (row.error === 0)
      return refuse('ZERO_ERROR', 'the error at n=' + n + ' is exactly zero, so no order can be measured. This usually means the reference solution is being compared against itself, or the scheme is exact for this manufactured solution — pick one the scheme cannot represent exactly.', { level: n });
    table.push(row);
  }

  /* ---- monotone decrease ---- */
  for (let i = 1; i < table.length; i++) {
    if (!(table[i].error < table[i - 1].error))
      return refuse('NOT_MONOTONE', 'the error did not decrease from n=' + table[i - 1].n + ' (' + table[i - 1].error.toExponential(3) +
                    ') to n=' + table[i].n + ' (' + table[i].error.toExponential(3) + '). A scheme whose error stops ' +
                    'falling under refinement has hit a floor — iteration tolerance, round-off, or a bug — and a slope ' +
                    'fitted through that floor is not an order.',
                    { coarser: table[i - 1].n, finer: table[i].n, errorCoarser: table[i - 1].error, errorFiner: table[i].error });
  }

  /* ---- THE ITERATION-CONTAMINATION TEST ----
     Same units on both sides, no constant anywhere: the movement caused by the
     SOLVER versus the movement caused by the GRID, over the same pair. */
  let worstRatio = 0, worstPair = null;
  for (let i = 1; i < table.length; i++) {
    const gridMove = Math.abs(table[i - 1].error - table[i].error);
    const iterMove = Math.max(table[i - 1].iterMove, table[i].iterMove);
    const ratio = gridMove === 0 ? Infinity : iterMove / gridMove;
    if (ratio > worstRatio) { worstRatio = ratio; worstPair = [table[i - 1].n, table[i].n]; }
    if (!skipContam && iterMove >= gridMove)
      return refuse('ITERATION_CONTAMINATION', 'between n=' + table[i - 1].n + ' and n=' + table[i].n + ', tightening the iteration tolerance moved ' +
                    'the error by ' + iterMove.toExponential(3) + ' while refining the grid moved it by ' +
                    gridMove.toExponential(3) + '. The solver is moving the answer at least as much as the mesh is, so ' +
                    'this study measures the STOPPING CRITERION, not the discretization order. Tighten tol and re-run.',
                    { coarser: table[i - 1].n, finer: table[i].n, iterationMove: iterMove, gridMove });
  }

  /* ---- pairwise observed orders ---- */
  const orders = [];
  for (let i = 1; i < table.length; i++) {
    const p = Math.log(table[i - 1].error / table[i].error) / Math.log(table[i - 1].h / table[i].h);
    orders.push({ from: table[i - 1].n, to: table[i].n, p });
    table[i].order = p;
  }
  const ps = orders.map(o => o.p);
  const lo = Math.min.apply(null, ps), hi = Math.max.apply(null, ps);

  /* ---- THE ASYMPTOTIC-RANGE TEST ----
     A fixed modelling error — a dropped term, a wrong boundary condition —
     does NOT make the error stop decreasing, which is why the monotonicity
     rule above cannot catch it. It makes the error approach a FLOOR, and the
     pairwise orders drift downward toward zero as the floor is reached. The
     signature is a wide spread, not a stalled table.

     The width is compared against 1, and that number is DERIVED rather than
     picked: orders are read in practice by distinguishing adjacent integers —
     is this scheme first order or second? An interval wider than 1 cannot
     separate 1 from 2, so it answers no question anyone asks of it. Claiming
     an order from such data would be reporting precision the study does not
     have, which is the failure this whole file exists to prevent. The interval
     and the table are still returned; only the CLAIM is withheld. */
  if (hi - lo > 2 * RESOLUTION)
    return refuse('SPREAD_TOO_WIDE', 'the observed orders span [' + lo.toFixed(3) + ', ' + hi.toFixed(3) + '] — wider than 1, so this ' +
                  'data cannot distinguish adjacent integer orders and supports no order claim at all. Pairwise: ' +
                  ps.map(p => p.toFixed(2)).join(' -> ') + '. A downward drift is the signature of an error FLOOR ' +
                  'being approached (a dropped term, a wrong boundary condition, round-off) rather than of a scheme ' +
                  'with an order; the errors keep falling, which is why the monotonicity rule cannot see it.',
                  { 'order interval': [lo, hi], 'pairwise orders': ps.map(p => p.toFixed(3)).join(', '),
                    'finest error': table[table.length - 1].error });

  /* ---- THE DECLARED-ORDER TEST ----
     This is what catches the failure the two rules above are blind to. A fixed
     modelling error (a dropped term, a wrong boundary condition) leaves the
     errors falling monotonically and the spread narrow — it simply floors them,
     and the observed order collapses toward zero. Reporting "order 0.0-0.4" is
     TRUE and is exactly the kind of true statement that gets skimmed. Against a
     declared order it becomes a contradiction with a number attached. */
  if (expected !== undefined && (expected < lo - RESOLUTION || expected > hi + RESOLUTION))
    return refuse('DECLARED_ORDER_MISMATCH', 'you declared order ' + expected + ', but the observed orders span [' + lo.toFixed(3) + ', ' + hi.toFixed(3) +
                  '], which is further than ' + RESOLUTION + ' from it — further than the resolution any order claim needs. Pairwise: ' + ps.map(p => p.toFixed(2)).join(' -> ') + '. The errors fall ' +
                  'monotonically and the solver is not the limit, so the scheme is converging — steadily, to something other ' +
                  'than the order you expect. An error FLOOR does this: a dropped term, a wrong boundary condition, or a ' +
                  'reference solution that is not quite the solution of the equation being solved.',
                  { 'declared order': expected, 'observed order': [lo, hi],
                    'pairwise orders': ps.map(p => p.toFixed(3)).join(', '), 'finest error': table[table.length - 1].error });

  const certificate = proved(Object.assign({}, base, {
    evidence: {
      'observed order': [lo, hi],
      'declared order': expected === undefined ? '(none)' : expected,
      'levels': levels.join(', '),
      'pairwise orders': ps.map(p => p.toFixed(3)).join(', '),
      'worst iter/grid move': worstRatio,
      'finest error': table[table.length - 1].error
    }
  }));

  return { code: 'PROVED', certificate, levels, order: [lo, hi], orders, table, worstRatio, worstPair };
}

module.exports = { study, TIGHTEN_BY, FALSIFIERS, ASSUMPTIONS };
