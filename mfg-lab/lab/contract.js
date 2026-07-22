/* contract.js — the kernel contract: what the Lab needs from YOUR solver.

   THE AXIS THIS FILE EXISTS FOR. Until now every module in this repository
   ran OUR problem and showed what WE computed. That is a demonstration. A lab
   runs YOUR problem, and the only way one piece of software can study a solver
   it has never seen is to agree in advance on the smallest possible interface.

   This is that interface. It is deliberately tiny — five things, three of them
   optional — because every field added here is a field a researcher must
   supply before they can find out whether the tool is worth anything.

     name      string.   what this kernel is called, in reports and permalinks.
     solve     REQUIRED. ({n, tol, params}) -> {u, iters, residual}
               Solve at resolution n, to iteration tolerance tol. Return the
               grid function u, how many iterations it took, and the residual
               it stopped at.

               `residual` is RELATIVE — normalised so that 1 means "no better
               than the initial guess". That convention is what lets the
               failure map separate a solver that is converging too slowly
               from one that has diverged, without inventing a threshold for
               either. `null` is allowed and means a direct solver, where
               there is no iteration to stall. A kernel that reports an
               unnormalised residual still works; it will simply have its
               divergent points reported as stalled.
     exact     REQUIRED. ({n, params}) -> u
               The reference solution sampled on the same grid. For a real
               problem this is a MANUFACTURED solution: you choose u, push it
               through the operator to get the forcing term, and solve that.
               See §"Why exact is required" below — this requirement is the
               point, not a limitation.
     h         optional. (n) -> mesh size. Default 1/n.
     levels    optional. array of n to study. Default [16, 32, 64, 128].
     params    optional. object of model parameters, passed through to both.
     norm      optional. 'l2' (default, h-weighted discrete L2) or 'max'.

   WHY `exact` IS REQUIRED, AND WHY THAT IS A FEATURE
   A convergence study without a reference solution has to compare successive
   grids to each other (Richardson / self-convergence). That works, and it is
   also the single easiest way to convince yourself a wrong code is right: a
   scheme converging steadily to the wrong answer self-converges beautifully.
   Requiring a reference solution forces the Method of Manufactured Solutions,
   which is the standard remedy in code verification, and turns the awkward
   question — "what SHOULD the answer be?" — from something the study hides
   into the first thing it asks. Self-convergence is not implemented, and the
   study says so rather than silently substituting it.

   THE MAP ADDS NO FIELDS. Everything the failure map needs — sweep ranges,
   sample counts, the resolution to hold fixed — is an argument to the map,
   not a demand on your kernel, because `params` already flows through to both
   `solve` and `exact`. One contract, every instrument.

   VALIDATION RUNS THE KERNEL. A contract checked with `typeof` passes for a
   function that throws, returns the wrong length, or returns NaN. So `validate`
   actually calls both functions at the smallest level and checks the shapes it
   gets back. A contract you cannot fail is the same species as a certificate
   that cannot go red.

   MIT licensed. Part of the MFG Lab. */
'use strict';

const DEFAULT_LEVELS = [16, 32, 64, 128];

/* A contract failure is a message to a human who is trying to plug their code
   in, so each one says what was expected, what arrived, and where. */
class ContractError extends Error {
  constructor(field, problem) {
    super('kernel.' + field + ': ' + problem);
    this.field = field;
  }
}

function isFn(v) { return typeof v === 'function'; }

/* Accept a plain array or any typed array, and normalise to a plain array of
   numbers so downstream code has exactly one shape to reason about. */
function asVector(v, field) {
  if (v == null) throw new ContractError(field, 'returned null/undefined');
  if (typeof v.length !== 'number') throw new ContractError(field, 'returned something without .length (expected an array of numbers)');
  const out = new Array(v.length);
  for (let i = 0; i < v.length; i++) {
    const x = v[i];
    if (typeof x !== 'number') throw new ContractError(field, 'element ' + i + ' is ' + typeof x + ', expected number');
    out[i] = x;
  }
  return out;
}

function validate(kernel) {
  if (!kernel || typeof kernel !== 'object') throw new ContractError('<root>', 'expected an object');

  if (typeof kernel.name !== 'string' || !kernel.name.trim())
    throw new ContractError('name', 'required, a non-empty string');
  if (!isFn(kernel.solve)) throw new ContractError('solve', 'required, ({n, tol, params}) -> {u, iters, residual}');
  if (!isFn(kernel.exact)) throw new ContractError('exact', 'required, ({n, params}) -> u. Manufacture one — see contract.js');

  if (kernel.h !== undefined && !isFn(kernel.h)) throw new ContractError('h', 'if present, must be (n) -> mesh size');
  if (kernel.norm !== undefined && kernel.norm !== 'l2' && kernel.norm !== 'max')
    throw new ContractError('norm', "if present, must be 'l2' or 'max'");

  const levels = kernel.levels || DEFAULT_LEVELS;
  if (!Array.isArray(levels) || levels.length < 1)
    throw new ContractError('levels', 'if present, must be a non-empty array of resolutions');
  for (const n of levels) {
    if (!Number.isFinite(n) || n <= 0 || Math.floor(n) !== n)
      throw new ContractError('levels', 'every level must be a positive integer, got ' + n);
  }
  const sorted = levels.slice().sort((a, b) => a - b);
  for (let i = 1; i < sorted.length; i++)
    if (sorted[i] === sorted[i - 1]) throw new ContractError('levels', 'duplicate level ' + sorted[i]);

  /* THE PART THAT ACTUALLY RUNS. Smallest level, loose tolerance — cheap, and
     it catches the shape errors that would otherwise surface as a confusing
     NaN four solves into a study. */
  const n0 = sorted[0];
  const params = kernel.params || {};
  let out;
  try {
    out = kernel.solve({ n: n0, tol: 1e-6, params });
  } catch (e) {
    throw new ContractError('solve', 'threw at the smallest level (n=' + n0 + '): ' + e.message);
  }
  if (!out || typeof out !== 'object') throw new ContractError('solve', 'must return an object {u, iters, residual}');
  const u = asVector(out.u, 'solve().u');
  if (out.iters !== undefined && !Number.isFinite(out.iters))
    throw new ContractError('solve().iters', 'if present, must be a finite number');
  if (out.residual !== undefined && out.residual !== null && !Number.isFinite(out.residual))
    throw new ContractError('solve().residual', 'if present, must be a finite number or null');

  let ex;
  try {
    ex = kernel.exact({ n: n0, params });
  } catch (e) {
    throw new ContractError('exact', 'threw at the smallest level (n=' + n0 + '): ' + e.message);
  }
  const e0 = asVector(ex, 'exact()');
  if (e0.length !== u.length)
    throw new ContractError('exact', 'returned length ' + e0.length + ' but solve() returned length ' + u.length + ' at n=' + n0 + ' — they must sample the same grid');

  const h = kernel.h ? kernel.h(n0) : 1 / n0;
  if (!Number.isFinite(h) || h <= 0) throw new ContractError('h', 'must return a positive finite mesh size, got ' + h);

  return {
    name: kernel.name,
    levels: sorted,
    params,
    norm: kernel.norm || 'l2',
    h: kernel.h || (n => 1 / n),
    solve: kernel.solve,
    exact: kernel.exact,
    length: u.length
  };
}

/* Grid norms. The h weight is what makes the discrete L2 norm converge to the
   continuous one; without it a study on a refining grid measures a norm that
   is itself changing, and the "order" picks up an extra half power. */
function norm(diff, h, kind) {
  if (kind === 'max') {
    let m = 0;
    for (const d of diff) { const a = Math.abs(d); if (a > m) m = a; }
    return m;
  }
  let s = 0;
  for (const d of diff) s += d * d;
  return Math.sqrt(h * s);
}

function errorOf(u, ex, h, kind) {
  if (u.length !== ex.length) throw new ContractError('exact', 'length mismatch during study: ' + u.length + ' vs ' + ex.length);
  const d = new Array(u.length);
  for (let i = 0; i < u.length; i++) d[i] = u[i] - ex[i];
  return norm(d, h, kind);
}

module.exports = { validate, norm, errorOf, asVector, ContractError, DEFAULT_LEVELS };
