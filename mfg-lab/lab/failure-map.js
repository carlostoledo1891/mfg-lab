/* failure-map.js — where does YOUR solver stop working?

   THE PAIN. You know your method works, because you tested it where you built
   it. You do not know where it STOPS — and the parameter you are about to
   change for the next paper may be on the other side of a boundary nobody has
   drawn. The usual substitute is spot-checks: a handful of runs at values that
   felt interesting, none of which was chosen by the failure.

   This repository has already been caught by exactly that. A prose range in
   the artifact claimed a scheme "reaches 1e-9 in 50-160 iterations across the
   whole slider box". A 16-corner sweep measured 32-78 iterations AND found
   that FOUR OF SIXTEEN corners do not converge at all. The range was wrong in
   both directions, and the non-convergence was invisible until something swept
   the box instead of sampling the middle of it.

   WHAT THIS RETURNS, AND WHAT IT REFUSES TO CALL IT
   A sampled grid of outcomes over a parameter box, and — where the outcome
   changes between adjacent samples — the BRACKET containing the transition.
   It is called a bracket and never a boundary, because a grid sample cannot
   see a failure region thinner than its own spacing. That limitation is
   declared on every certificate this file produces; it is not a caveat in
   prose, it is an assumption attached to the claim.

   THE OUTCOME TAXONOMY IS OBSERVED, NOT THRESHOLDED
     ok        reached the tolerance it was given
     stalled   still above tolerance but below 1 — converging, and out of
               budget. "Give it more iterations."
     diverged  non-finite values, or a relative residual at or above 1 —
               no better than the initial guess. "This will never work here."
     threw     the kernel raised

   Nothing here compares against an invented constant. `ok` is the kernel's own
   residual against the tolerance the caller passed; `diverged` uses 1, which
   is not a tolerance but the exact value of the relative residual at the
   initial guess (see the contract) — a run ending there has gone backwards.
   The other two are structural.

   Slow and divergent were ONE outcome in the first version of this file, and
   separating them was forced by measurement rather than foresight: the
   Helmholtz fixture ended at residual 6.95e+24 and got reported as "stalled",
   which tells a researcher to raise their iteration cap when the truth is that
   no cap will help.

   ONE HONEST CONSEQUENCE, STATED UP FRONT. `stalled` is a property of YOUR
   configuration, not of the mathematics: a run that would converge in ten
   million iterations is stalled at a cap of ten thousand, and this map will
   say so. That is deliberate and matches the order study — the instrument
   characterises the setup in front of it, and says which knob it was holding.

   MIT licensed. Part of the MFG Lab. */
'use strict';

const { validate, errorOf } = require('./contract.js');
const { proved, refused } = require('../../eqcert/src/certificate.js');

const OK = 'ok', STALLED = 'stalled', DIVERGED = 'diverged', THREW = 'threw';

const FALSIFIERS = [
  'a parameter point inside the box where the solver does not reach tolerance',
  'a finer sample that finds failures this spacing stepped over — the reason this reports brackets and never boundaries',
  'a kernel that reports a residual it did not achieve (the map trusts the kernel on this one number)',
  'an iteration cap raised until a stalled point converges, which turns a "failure" into a cost'
];

function assumptionsFor(spacingText) {
  return [
    'a failure region thinner than the sample spacing (' + spacingText + ') is INVISIBLE to this map — it samples, it does not prove',
    'the residual reported by the kernel is the residual it actually reached',
    '"stalled" is a property of the configuration swept, including its iteration cap, not of the scheme alone'
  ];
}

function linspace(lo, hi, k) {
  if (k === 1) return [(lo + hi) / 2];
  const out = new Array(k);
  for (let i = 0; i < k; i++) out[i] = lo + (hi - lo) * i / (k - 1);
  return out;
}

function allFinite(v) {
  for (let i = 0; i < v.length; i++) if (!Number.isFinite(v[i])) return false;
  return true;
}

/* One parameter point. Every failure mode is caught and classified rather than
   thrown, because a map that dies on its first bad point is a map of nothing. */
function probe(K, params, n, tol) {
  let out;
  try {
    out = K.solve({ n, tol, params });
  } catch (e) {
    return { outcome: THREW, detail: e.message, iters: null, residual: null, error: null };
  }
  if (!out || !out.u || !allFinite(out.u))
    return { outcome: DIVERGED, detail: 'the returned solution contains non-finite values', iters: out && out.iters, residual: out && out.residual, error: null };

  let error = null;
  try {
    error = errorOf(out.u, K.exact({ n, params }), K.h(n), K.norm);
  } catch (e) { error = null; }
  if (error !== null && !Number.isFinite(error))
    return { outcome: DIVERGED, detail: 'the error against the reference solution is not finite', iters: out.iters, residual: out.residual, error: null };

  /* residual === null means a direct solver: there is no iteration to stall. */
  const r = out.residual;
  if (r === null || r === undefined) return { outcome: OK, detail: '', iters: out.iters, residual: null, error };

  /* DIVERGED vs STALLED, decided structurally rather than by a threshold.
     The contract asks for a RELATIVE residual, so 1 is exactly "no better than
     the initial guess". A run that ends at or above 1 has not converged slowly
     — it has moved away from the answer, or overflowed on the way. Slow and
     divergent are different answers to the question being asked, and lumping
     them together was the first version of this file: the Helmholtz fixture
     ended at residual 6.95e+24 and was reported as "stalled", which reads as
     "needs more iterations" when the truth is "this iteration will never work
     here". Measured, then fixed. */
  if (!Number.isFinite(r) || r >= 1)
    return { outcome: DIVERGED, detail: 'the relative residual ended at ' + (Number.isFinite(r) ? r.toExponential(3) : String(r)) +
             ' — at or above its starting value, so the iteration moved away from the solution rather than converging slowly',
             iters: out.iters, residual: r, error };

  if (r <= tol) return { outcome: OK, detail: '', iters: out.iters, residual: r, error };
  return {
    outcome: STALLED,
    detail: 'stopped at relative residual ' + r.toExponential(3) + ', above the requested ' + tol.toExponential(3) +
            ' but still below 1 — converging, too slowly for the budget it was given',
    iters: out.iters, residual: r, error
  };
}

/* opts:
     sweep    REQUIRED. {paramName: [lo, hi]} for one or two parameters.
     samples  per axis, default 12
     n        resolution to hold fixed, default the kernel's median level
     tol      iteration tolerance, default 1e-6
     params   base parameters; the swept ones are overwritten per point     */
function map(kernel, opts) {
  opts = opts || {};
  const K = validate(kernel);
  const sweep = opts.sweep;
  if (!sweep || typeof sweep !== 'object') throw new Error('map: sweep is required, e.g. {k: [0.5, 6]}');

  const names = Object.keys(sweep);
  if (names.length < 1 || names.length > 2)
    throw new Error('map: sweep one or two parameters, got ' + names.length + '. A three-dimensional box needs a different instrument.');
  for (const nm of names) {
    const r = sweep[nm];
    if (!Array.isArray(r) || r.length !== 2 || !Number.isFinite(r[0]) || !Number.isFinite(r[1]) || !(r[0] < r[1]))
      throw new Error('map: sweep.' + nm + ' must be [lo, hi] with lo < hi');
  }

  const samples = opts.samples === undefined ? 12 : opts.samples;
  if (!Number.isInteger(samples) || samples < 2)
    throw new Error('map: samples must be an integer >= 2; one sample per axis is a spot-check, which is the thing this replaces');
  const tol = opts.tol === undefined ? 1e-6 : opts.tol;
  const n = opts.n === undefined ? K.levels[Math.floor(K.levels.length / 2)] : opts.n;

  const axes = names.map(nm => ({ name: nm, values: linspace(sweep[nm][0], sweep[nm][1], samples) }));
  const spacingText = axes.map(a => a.name + ' ' + ((a.values[a.values.length - 1] - a.values[0]) / (samples - 1)).toPrecision(3)).join(', ');

  /* ---- sweep ---- */
  const base = Object.assign({}, K.params, opts.params || {});
  const points = [];
  const counts = { ok: 0, stalled: 0, diverged: 0, threw: 0 };

  const outer = axes[0].values;
  const inner = axes[1] ? axes[1].values : [null];
  for (let i = 0; i < outer.length; i++) {
    for (let j = 0; j < inner.length; j++) {
      const params = Object.assign({}, base);
      params[axes[0].name] = outer[i];
      if (axes[1]) params[axes[1].name] = inner[j];
      const r = probe(K, params, n, tol);
      counts[r.outcome]++;
      points.push(Object.assign({ i, j, params }, r));
    }
  }

  /* ---- transition brackets: adjacent samples whose outcome differs ----
     This is the answer to the question actually being asked. "Your solver
     stops reaching tolerance between k=3.0 and k=3.5" is usable; a grid of
     coloured cells is a picture of it. */
  const at = (i, j) => points[i * inner.length + j];
  const brackets = [];
  for (let i = 0; i < outer.length; i++) {
    for (let j = 0; j < inner.length; j++) {
      const a = at(i, j);
      if (i + 1 < outer.length) {
        const b = at(i + 1, j);
        if (b.outcome !== a.outcome) brackets.push({ axis: axes[0].name, from: outer[i], to: outer[i + 1], fromOutcome: a.outcome, toOutcome: b.outcome, at: axes[1] ? { [axes[1].name]: inner[j] } : {} });
      }
      if (axes[1] && j + 1 < inner.length) {
        const b = at(i, j + 1);
        if (b.outcome !== a.outcome) brackets.push({ axis: axes[1].name, from: inner[j], to: inner[j + 1], fromOutcome: a.outcome, toOutcome: b.outcome, at: { [axes[0].name]: outer[i] } });
      }
    }
  }

  /* ---- the certificate ---- */
  const total = points.length;
  const bad = total - counts.ok;
  const evidence = {
    'box': names.map(nm => nm + ' in [' + sweep[nm][0] + ', ' + sweep[nm][1] + ']').join(' x '),
    'sampled points': total,
    'reached tolerance': counts.ok,
    'stalled / diverged / threw': counts.stalled + ' / ' + counts.diverged + ' / ' + counts.threw,
    'resolution n': n,
    'tolerance': tol
  };
  const commonBase = {
    falsifier: FALSIFIERS, assumes: assumptionsFor(spacingText),
    provenance: { kernel: K.name, samplesPerAxis: samples, n, tol, norm: K.norm }
  };

  let certificate, code;
  if (bad === 0) {
    code = 'PROVED';
    const worst = points.reduce((w, p) => (p.iters || 0) > (w.iters || 0) ? p : w, points[0]);
    certificate = proved(Object.assign({}, commonBase, {
      claim: K.name + ' reached its tolerance at every SAMPLED point of the box (a sample, not a proof of the box)',
      evidence: Object.assign({}, evidence, { 'worst iteration count': worst.iters })
    }));
  } else {
    code = 'POINTS_FAILED';
    const firstBad = points.find(p => p.outcome !== OK);
    const where = names.map(nm => nm + '=' + (+firstBad.params[nm]).toPrecision(4)).join(', ');
    certificate = refused(Object.assign({}, commonBase, {
      claim: K.name + ' reaches its tolerance across the box',
      why: bad + ' of ' + total + ' sampled points did not reach tolerance (' + counts.stalled + ' stalled, ' +
           counts.diverged + ' diverged, ' + counts.threw + ' threw). First at ' + where + ': ' +
           (firstBad.detail || firstBad.outcome) + '. ' +
           (brackets.length ? 'The change of behaviour is bracketed by ' +
              brackets.slice(0, 3).map(b => b.axis + ' in [' + (+b.from).toPrecision(4) + ', ' + (+b.to).toPrecision(4) + '] (' + b.fromOutcome + ' -> ' + b.toOutcome + ')').join('; ')
            : 'No adjacent pair of samples changed outcome, so the whole sampled box behaves the same way and no bracket exists.'),
      evidence
    }));
  }

  return { code, certificate, axes, points, brackets, counts, n, tol, samples };
}

module.exports = { map, OK, STALLED, DIVERGED, THREW, FALSIFIERS };
