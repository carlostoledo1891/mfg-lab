"""order_study.py — a convergence study that refuses to lie. Python twin of
``mfg-lab/lab/order-study.js``.

Every computational paper contains a convergence table, and almost none check
whether the number in it is the discretization order at all: if the solver
stopped iterating before the discretization error was resolved, the table
measures the STOPPING CRITERION and reports it as a property of the scheme.
This repository published "|eps| ~ (h+dt)^1.1" and then measured apparent
slopes from -1.9 to +2.6 for exactly that reason (``mfg-lab/docs/FINDINGS.md``).

Three rules, none of which rests on an invented constant:

1. **Iteration contamination.** Solve twice per level — at your tolerance and
   at a much tighter one — and ask whether tightening the solver moves the
   answer as much as refining the grid does. Same units on both sides, no
   threshold anywhere. The check people reach for ("residual must be much
   smaller than the error") needs a stability constant nobody has and would be
   a fabricated floor.
2. **Monotone decrease.**
3. **Declared order.** You say what you believe; the study tries to falsify it.
   This catches what the other two are blind to — a dropped term leaves the
   errors falling and the spread narrow, it merely floors them.

The full account is in the JavaScript sibling. This module carries the rules
rather than restating the essay, so the two cannot drift in prose; the
cross-language differential holds them to the same DECISIONS via
:attr:`StudyResult.code`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from ..certificate import Certificate, proved, refused
from .contract import ValidatedKernel, error_of, validate

#: Tightening factor for the second solve at each level. An EXPERIMENTAL DESIGN
#: choice, not a threshold any verdict compares against — no criterion below
#: contains it. If the tight solve is itself iteration-limited the test
#: understates contamination, which is why that is declared as an assumption on
#: every certificate rather than hidden.
TIGHTEN_BY = 1e-3

#: THE ONE RESOLUTION CONSTANT, DERIVED ONCE AND USED TWICE. Orders are read by
#: distinguishing adjacent integers — is this scheme first order or second? So
#: the resolution any order claim needs is half the gap between neighbours.
#: A spread wider than ``2 * RESOLUTION`` cannot separate 1 from 2 and supports
#: no claim; a declared order further than ``RESOLUTION`` from everything
#: observed is contradicted. It is NOT a tolerance on a residual. Strict
#: containment was tried first and is wrong: a genuinely second-order scheme
#: measures [1.9995, 1.9999], because the true order is the LIMIT of the
#: pairwise orders, not a member of them.
RESOLUTION = 0.5

FALSIFIERS = [
    "a kernel whose error stops decreasing under refinement (the study refuses instead of fitting a slope through it)",
    "a kernel where tightening the iteration tolerance moves the error by as much as refining the grid does",
    "pairwise orders spanning more than 1, which cannot distinguish adjacent integer orders",
    "an order you declared that sits further than half an order from everything the study observed",
    "fewer than three levels, which cannot produce an order interval",
    "a reference solution that is not a solution of the continuous problem — this the study cannot detect, and it is declared as an assumption",
]

ASSUMPTIONS = [
    "the tightened solve is itself converged; if it is not, contamination is UNDERSTATED",
    "the supplied reference solution solves the continuous problem (manufacture it, do not guess it) — nothing here can check this",
    "the error is measured in the discrete grid norm named in the evidence, and that norm is the one the claimed order refers to",
]


@dataclass
class Level:
    n: int
    h: float
    error: float
    error_at_tight_tol: float
    iter_move: float
    iters: Any
    residual: Any
    order: float | None = None


@dataclass
class StudyResult:
    code: str
    certificate: Certificate
    levels: tuple[int, ...] = ()
    order: tuple[float, float] | None = None
    table: list[Level] = field(default_factory=list)
    orders: list[dict] = field(default_factory=list)
    worst_ratio: float = 0.0


def _run_level(K: ValidatedKernel, n: int, tol: float) -> Level:
    """Report the error YOUR setup produces, at YOUR working tolerance, with the
    tightened solve used only as a probe of how far that is from converged.

    The direction is deliberate: reporting the tightened error instead would
    hand back a better answer than the configuration in front of us actually
    produces, and the study would be certifying a computation nobody ran.
    """
    h = K.h(n)
    ex = K.exact(n=n, params=K.params)
    working = K.solve(n=n, tol=tol, params=K.params)
    tight = K.solve(n=n, tol=tol * TIGHTEN_BY, params=K.params)

    e_working = error_of(list(working["u"]), list(ex), h, K.norm)
    e_tight = error_of(list(tight["u"]), list(ex), h, K.norm)
    return Level(
        n=n, h=h, error=e_working, error_at_tight_tol=e_tight,
        iter_move=abs(e_working - e_tight),
        iters=working.get("iters"), residual=working.get("residual"),
    )


def study(
    kernel: Any,
    tol: float = 1e-6,
    levels: Sequence[int] | None = None,
    expected_order: float | None = None,
    _unsafe_skip_contamination_test: bool = False,
) -> StudyResult:
    """Run the convergence study. See the module docstring for the three rules.

    Args:
        expected_order: what you believe the scheme delivers. Optional, and the
            single most useful thing you can supply — without it the study can
            only report what it measured, and "the observed order is 0.0 to
            0.4" is a true statement a tired reader will skim past. With it,
            the same data becomes a refusal naming the contradiction.
    """
    K = validate(kernel)
    lv = tuple(sorted(levels)) if levels is not None else K.levels
    if expected_order is not None and (not isinstance(expected_order, (int, float)) or not math.isfinite(expected_order) or expected_order <= 0):
        raise ValueError(f"study: expected_order must be a positive finite number, got {expected_order!r}")

    assumes = list(ASSUMPTIONS)
    if _unsafe_skip_contamination_test:
        assumes.insert(0, "THE ITERATION-CONTAMINATION TEST WAS DISABLED for this run — the order below may be a property of the stopping criterion rather than of the scheme")
    if expected_order is None:
        assumes.append("no expected order was declared, so the study reports what it measured and cannot tell you whether that is what your scheme should deliver")

    claim = (
        f"the observed order of accuracy of {K.name} lies in the reported interval"
        if expected_order is None else
        f"the observed order of accuracy of {K.name} is consistent with the declared order {expected_order}"
    )
    provenance = {"kernel": K.name, "norm": K.norm, "tol": tol, "tightenBy": TIGHTEN_BY,
                  "expectedOrder": "(none declared)" if expected_order is None else expected_order}

    table: list[Level] = []

    def refuse(code: str, why: str, evidence: dict | None = None) -> StudyResult:
        ev = {"refusal code": code}
        ev.update(evidence or {})
        # A refusal hands back the table it measured. "We will not call this an
        # order, and here is exactly what we saw" is actionable; a bare reason
        # is an argument the user cannot check.
        return StudyResult(code=code, levels=tuple(lv), table=table, certificate=refused(
            claim=claim, falsifier=FALSIFIERS, assumes=assumes, provenance=provenance, why=why, evidence=ev))

    if len(lv) < 3:
        return refuse("TOO_FEW_LEVELS",
                      "a convergence study needs at least three levels to report an order INTERVAL; "
                      f"{len(lv)} given. Two levels always produce a number, and that number is not evidence.")

    for n in lv:
        row = _run_level(K, n, tol)
        if not math.isfinite(row.error):
            return refuse("NON_FINITE_ERROR", f"the error at n={n} is not finite ({row.error}) — the solve did not produce a usable answer", {"level": n})
        if row.error == 0:
            return refuse("ZERO_ERROR",
                          f"the error at n={n} is exactly zero, so no order can be measured. This usually means the "
                          "reference solution is being compared against itself, or the scheme is exact for this "
                          "manufactured solution — pick one the scheme cannot represent exactly.", {"level": n})
        table.append(row)

    for i in range(1, len(table)):
        if not table[i].error < table[i - 1].error:
            return refuse("NOT_MONOTONE",
                          f"the error did not decrease from n={table[i-1].n} ({table[i-1].error:.3e}) to "
                          f"n={table[i].n} ({table[i].error:.3e}). A scheme whose error stops falling under refinement "
                          "has hit a floor — iteration tolerance, round-off, or a bug — and a slope fitted through "
                          "that floor is not an order.",
                          {"coarser": table[i - 1].n, "finer": table[i].n,
                           "errorCoarser": table[i - 1].error, "errorFiner": table[i].error})

    worst_ratio = 0.0
    for i in range(1, len(table)):
        grid_move = abs(table[i - 1].error - table[i].error)
        iter_move = max(table[i - 1].iter_move, table[i].iter_move)
        ratio = math.inf if grid_move == 0 else iter_move / grid_move
        worst_ratio = max(worst_ratio, ratio)
        if not _unsafe_skip_contamination_test and iter_move >= grid_move:
            return refuse("ITERATION_CONTAMINATION",
                          f"between n={table[i-1].n} and n={table[i].n}, tightening the iteration tolerance moved the "
                          f"error by {iter_move:.3e} while refining the grid moved it by {grid_move:.3e}. The solver is "
                          "moving the answer at least as much as the mesh is, so this study measures the STOPPING "
                          "CRITERION, not the discretization order. Tighten tol and re-run.",
                          {"coarser": table[i - 1].n, "finer": table[i].n,
                           "iterationMove": iter_move, "gridMove": grid_move})

    orders = []
    for i in range(1, len(table)):
        p = math.log(table[i - 1].error / table[i].error) / math.log(table[i - 1].h / table[i].h)
        orders.append({"from": table[i - 1].n, "to": table[i].n, "p": p})
        table[i].order = p
    ps = [o["p"] for o in orders]
    lo, hi = min(ps), max(ps)
    pairwise = ", ".join(f"{p:.3f}" for p in ps)
    arrow = " -> ".join(f"{p:.2f}" for p in ps)

    if hi - lo > 2 * RESOLUTION:
        return refuse("SPREAD_TOO_WIDE",
                      f"the observed orders span [{lo:.3f}, {hi:.3f}] — wider than 1, so this data cannot distinguish "
                      f"adjacent integer orders and supports no order claim at all. Pairwise: {arrow}. A downward "
                      "drift is the signature of an error FLOOR being approached (a dropped term, a wrong boundary "
                      "condition, round-off) rather than of a scheme with an order; the errors keep falling, which is "
                      "why the monotonicity rule cannot see it.",
                      {"order interval": [lo, hi], "pairwise orders": pairwise, "finest error": table[-1].error})

    if expected_order is not None and (expected_order < lo - RESOLUTION or expected_order > hi + RESOLUTION):
        return refuse("DECLARED_ORDER_MISMATCH",
                      f"you declared order {expected_order}, but the observed orders span [{lo:.3f}, {hi:.3f}], which "
                      f"is further than {RESOLUTION} from it — further than the resolution any order claim needs. "
                      f"Pairwise: {arrow}. The errors fall monotonically and the solver is not the limit, so the "
                      "scheme is converging — steadily, to something other than the order you expect. An error FLOOR "
                      "does this: a dropped term, a wrong boundary condition, or a reference solution that is not "
                      "quite the solution of the equation being solved.",
                      {"declared order": expected_order, "observed order": [lo, hi],
                       "pairwise orders": pairwise, "finest error": table[-1].error})

    cert = proved(claim=claim, falsifier=FALSIFIERS, assumes=assumes, provenance=provenance, evidence={
        "observed order": [lo, hi],
        "declared order": "(none)" if expected_order is None else expected_order,
        "levels": ", ".join(str(n) for n in lv),
        "pairwise orders": pairwise,
        "worst iter/grid move": worst_ratio,
        "finest error": table[-1].error,
    })
    return StudyResult(code="PROVED", certificate=cert, levels=tuple(lv), order=(lo, hi),
                       table=table, orders=orders, worst_ratio=worst_ratio)
