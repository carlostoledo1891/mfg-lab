"""failure_map.py — where does your solver stop working? Python twin of
``mfg-lab/lab/failure-map.js``.

You know your method works where you built it. You do not know where it STOPS.
This sweeps a parameter box and reports, per point, whether the solver reached
tolerance — plus, where adjacent samples disagree, the BRACKET containing the
change of behaviour.

It is called a bracket and never a boundary. A grid cannot see a failure region
thinner than its own spacing, and that limitation is an ASSUMPTION attached to
every certificate this module issues rather than a caveat in prose.

The outcome taxonomy is observed, not thresholded:

``ok``
    reached the tolerance it was given.
``stalled``
    still above tolerance but below 1 — converging, out of budget. "Give it
    more iterations."
``diverged``
    non-finite values, or a relative residual at or above 1, i.e. no better
    than the initial guess. "This will never work here."
``threw``
    the kernel raised.

The only number here is 1, and it is not a tolerance: it is the exact value of
the relative residual at the initial guess (see :mod:`.contract`), so a run
ending at or above it has gone backwards. Slow and divergent were ONE outcome
in the first version, and separating them was forced by measurement — the
Helmholtz fixture ended at residual 6.95e+24 and was reported as "stalled",
which tells a researcher to raise their iteration cap when no cap will help.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..certificate import Certificate, proved, refused
from .contract import ValidatedKernel, error_of, validate

OK, STALLED, DIVERGED, THREW = "ok", "stalled", "diverged", "threw"

FALSIFIERS = [
    "a parameter point inside the box where the solver does not reach tolerance",
    "a finer sample that finds failures this spacing stepped over — the reason this reports brackets and never boundaries",
    "a kernel that reports a residual it did not achieve (the map trusts the kernel on this one number)",
    "an iteration cap raised until a stalled point converges, which turns a \"failure\" into a cost",
]


def _assumptions_for(spacing_text: str) -> list[str]:
    return [
        f"a failure region thinner than the sample spacing ({spacing_text}) is INVISIBLE to this map — it samples, it does not prove",
        "the residual reported by the kernel is the residual it actually reached",
        '"stalled" is a property of the configuration swept, including its iteration cap, not of the scheme alone',
    ]


@dataclass
class Point:
    i: int
    j: int
    params: dict
    outcome: str
    detail: str = ""
    iters: Any = None
    residual: Any = None
    error: float | None = None


@dataclass
class Axis:
    name: str
    values: list[float]


@dataclass
class MapResult:
    code: str
    certificate: Certificate
    axes: list[Axis]
    points: list[Point]
    brackets: list[dict]
    counts: dict
    n: int
    tol: float
    samples: int = 0
    _by_index: dict = field(default_factory=dict, repr=False)


def _linspace(lo: float, hi: float, k: int) -> list[float]:
    if k == 1:
        return [(lo + hi) / 2]
    return [lo + (hi - lo) * i / (k - 1) for i in range(k)]


def _all_finite(v: Sequence[float]) -> bool:
    return all(isinstance(x, (int, float)) and math.isfinite(x) for x in v)


def _probe(K: ValidatedKernel, params: dict, n: int, tol: float) -> dict:
    """One parameter point. Every failure mode is classified rather than raised
    — a map that dies on its first bad point is a map of nothing."""
    try:
        out = K.solve(n=n, tol=tol, params=params)
    except Exception as e:  # noqa: BLE001 — classifying failures is the job
        return dict(outcome=THREW, detail=str(e), iters=None, residual=None, error=None)

    # NOT `out.get("u") or []`: numpy arrays raise on bool(), and a researcher's
    # Python kernel commonly returns np.ndarray for u. Truth-test None explicitly.
    raw = out.get("u")
    u = list(raw) if raw is not None else []
    if not u or not _all_finite(u):
        return dict(outcome=DIVERGED, detail="the returned solution contains non-finite values",
                    iters=out.get("iters"), residual=out.get("residual"), error=None)

    try:
        error = error_of(u, list(K.exact(n=n, params=params)), K.h(n), K.norm)
    except Exception:  # noqa: BLE001
        error = None
    if error is not None and not math.isfinite(error):
        return dict(outcome=DIVERGED, detail="the error against the reference solution is not finite",
                    iters=out.get("iters"), residual=out.get("residual"), error=None)

    r = out.get("residual")
    if r is None:
        return dict(outcome=OK, detail="", iters=out.get("iters"), residual=None, error=error)

    if not math.isfinite(r) or r >= 1:
        shown = f"{r:.3e}" if math.isfinite(r) else str(r)
        return dict(outcome=DIVERGED, iters=out.get("iters"), residual=r, error=error,
                    detail=f"the relative residual ended at {shown} — at or above its starting value, so the "
                           "iteration moved away from the solution rather than converging slowly")
    if r <= tol:
        return dict(outcome=OK, detail="", iters=out.get("iters"), residual=r, error=error)
    return dict(outcome=STALLED, iters=out.get("iters"), residual=r, error=error,
                detail=f"stopped at relative residual {r:.3e}, above the requested {tol:.3e} but still below 1 "
                       "— converging, too slowly for the budget it was given")


def map_box(
    kernel: Any,
    sweep: Mapping[str, Sequence[float]],
    samples: int = 12,
    n: int | None = None,
    tol: float = 1e-6,
    params: Mapping[str, Any] | None = None,
) -> MapResult:
    """Sweep one or two parameters over a box and classify every sample.

    Named ``map_box`` rather than ``map`` so it does not shadow the builtin —
    the JavaScript sibling is ``map`` because JS has no such conflict.
    """
    K = validate(kernel)
    if not sweep or not isinstance(sweep, Mapping):
        raise ValueError("map: sweep is required, e.g. {'k': [0.5, 6]}")
    names = list(sweep.keys())
    if not 1 <= len(names) <= 2:
        raise ValueError(f"map: sweep one or two parameters, got {len(names)}. "
                         "A three-dimensional box needs a different instrument.")
    for nm in names:
        r = sweep[nm]
        if (not isinstance(r, Sequence) or isinstance(r, str) or len(r) != 2
                or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in r) or not r[0] < r[1]):
            raise ValueError(f"map: sweep.{nm} must be [lo, hi] with lo < hi")
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 2:
        raise ValueError("map: samples must be an integer >= 2; one sample per axis is a spot-check, "
                         "which is the thing this replaces")
    if n is None:
        n = K.levels[len(K.levels) // 2]

    axes = [Axis(nm, _linspace(sweep[nm][0], sweep[nm][1], samples)) for nm in names]
    spacing_text = ", ".join(
        f"{a.name} {(a.values[-1] - a.values[0]) / (samples - 1):.3g}" for a in axes)

    base = dict(K.params)
    base.update(params or {})
    points: list[Point] = []
    counts = {OK: 0, STALLED: 0, DIVERGED: 0, THREW: 0}

    outer = axes[0].values
    inner = axes[1].values if len(axes) > 1 else [None]
    for i, a in enumerate(outer):
        for j, b in enumerate(inner):
            p = dict(base)
            p[axes[0].name] = a
            if len(axes) > 1:
                p[axes[1].name] = b
            r = _probe(K, p, n, tol)
            counts[r["outcome"]] += 1
            points.append(Point(i=i, j=j, params=p, **r))

    def at(i: int, j: int) -> Point:
        return points[i * len(inner) + j]

    brackets: list[dict] = []
    for i in range(len(outer)):
        for j in range(len(inner)):
            a_pt = at(i, j)
            if i + 1 < len(outer):
                b_pt = at(i + 1, j)
                if b_pt.outcome != a_pt.outcome:
                    brackets.append(dict(axis=axes[0].name, from_=outer[i], to=outer[i + 1],
                                         fromOutcome=a_pt.outcome, toOutcome=b_pt.outcome,
                                         at={axes[1].name: inner[j]} if len(axes) > 1 else {}))
            if len(axes) > 1 and j + 1 < len(inner):
                b_pt = at(i, j + 1)
                if b_pt.outcome != a_pt.outcome:
                    brackets.append(dict(axis=axes[1].name, from_=inner[j], to=inner[j + 1],
                                         fromOutcome=a_pt.outcome, toOutcome=b_pt.outcome,
                                         at={axes[0].name: outer[i]}))

    total = len(points)
    bad = total - counts[OK]
    evidence = {
        "box": " x ".join(f"{nm} in [{sweep[nm][0]}, {sweep[nm][1]}]" for nm in names),
        "sampled points": total,
        "reached tolerance": counts[OK],
        "stalled / diverged / threw": f"{counts[STALLED]} / {counts[DIVERGED]} / {counts[THREW]}",
        "resolution n": n,
        "tolerance": tol,
    }
    common = dict(falsifier=FALSIFIERS, assumes=_assumptions_for(spacing_text),
                  provenance={"kernel": K.name, "samplesPerAxis": samples, "n": n, "tol": tol, "norm": K.norm})

    if bad == 0:
        code = "PROVED"
        worst = max(points, key=lambda p: p.iters or 0)
        cert = proved(claim=f"{K.name} reached its tolerance at every SAMPLED point of the box "
                            "(a sample, not a proof of the box)",
                      evidence={**evidence, "worst iteration count": worst.iters}, **common)
    else:
        code = "POINTS_FAILED"
        first_bad = next(p for p in points if p.outcome != OK)
        where = ", ".join(f"{nm}={first_bad.params[nm]:.4g}" for nm in names)
        if brackets:
            bracket_text = "The change of behaviour is bracketed by " + "; ".join(
                f"{b['axis']} in [{b['from_']:.4g}, {b['to']:.4g}] ({b['fromOutcome']} -> {b['toOutcome']})"
                for b in brackets[:3])
        else:
            bracket_text = ("No adjacent pair of samples changed outcome, so the whole sampled box behaves the "
                            "same way and no bracket exists.")
        cert = refused(claim=f"{K.name} reaches its tolerance across the box",
                       why=f"{bad} of {total} sampled points did not reach tolerance ({counts[STALLED]} stalled, "
                           f"{counts[DIVERGED]} diverged, {counts[THREW]} threw). First at {where}: "
                           f"{first_bad.detail or first_bad.outcome}. {bracket_text}",
                       evidence=evidence, **common)

    return MapResult(code=code, certificate=cert, axes=axes, points=points, brackets=brackets,
                     counts=counts, n=n, tol=tol, samples=samples)
