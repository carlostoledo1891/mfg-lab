"""contract.py — the kernel contract. Python twin of ``mfg-lab/lab/contract.js``.

A lab runs YOUR problem, and the only way one instrument can study a solver it
has never seen is to agree in advance on the smallest possible interface. This
is that interface: five things, three optional.

    name    str. Used in reports and permalinks.
    solve   REQUIRED. ``solve(n, tol, params) -> {"u", "iters", "residual"}``.
            ``residual`` is RELATIVE — normalised so 1 means "no better than
            the initial guess". That convention is what lets the failure map
            separate a solver converging too slowly from one that has diverged
            without inventing a threshold for either. ``None`` means a direct
            solver, where there is no iteration to stall.
    exact   REQUIRED. ``exact(n, params) -> u``, the reference solution on the
            same grid. For a real problem this is a MANUFACTURED solution.
    h       optional. ``h(n) -> mesh size``. Default ``1/n``.
    levels  optional. Resolutions to study. Default ``(16, 32, 64, 128)``.
    params  optional. Model parameters, passed through to both.
    norm    optional. ``"l2"`` (default, h-weighted discrete L2) or ``"max"``.

WHY ``exact`` IS REQUIRED AND WHY THAT IS A FEATURE. A convergence study
without a reference solution compares successive grids to each other, and a
scheme converging steadily to the WRONG answer self-converges beautifully.
Requiring a reference forces the Method of Manufactured Solutions and turns
"what should the answer be?" from something the study hides into the first
thing it asks.

VALIDATION RUNS THE KERNEL. A contract checked with ``isinstance`` passes for a
function that raises, returns the wrong length, or returns NaN. ``validate``
calls both functions at the smallest level and checks what comes back. A
contract you cannot fail is the same species as a certificate that cannot go
red.

DIRECTION OF THE PORT, STATED BECAUSE IT DIFFERS FROM THE KERNELS. For the
mathematics kernels this package is the source of truth and the in-page
JavaScript is the verified port (see ``mfglab.__init__``). The Lab INSTRUMENTS
went the other way: they were specified in JavaScript first, because the
browser Lab is their primary surface. The cross-language differential
(``tests/test_crosslang_lab.py``) holds them together either way, which is what
makes the direction a matter of documentation rather than of correctness.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

DEFAULT_LEVELS: tuple[int, ...] = (16, 32, 64, 128)


class ContractError(Exception):
    """A contract failure is a message to a human plugging their code in, so it
    says what was expected, what arrived, and where."""

    def __init__(self, field_name: str, problem: str) -> None:
        super().__init__(f"kernel.{field_name}: {problem}")
        self.field = field_name


@dataclass
class Kernel:
    """Convenience container. Any object carrying these attributes works —
    ``validate`` duck-types, so an existing class needs no adapter."""

    name: str
    solve: Callable[..., Mapping[str, Any]]
    exact: Callable[..., Sequence[float]]
    h: Callable[[int], float] | None = None
    levels: Sequence[int] | None = None
    params: Mapping[str, Any] = field(default_factory=dict)
    norm: str = "l2"


@dataclass
class ValidatedKernel:
    name: str
    levels: tuple[int, ...]
    params: dict
    norm: str
    h: Callable[[int], float]
    solve: Callable[..., Mapping[str, Any]]
    exact: Callable[..., Sequence[float]]
    length: int


def _as_vector(v: Any, field_name: str) -> list[float]:
    if v is None:
        raise ContractError(field_name, "returned None")
    try:
        seq = list(v)
    except TypeError:
        raise ContractError(field_name, "returned something not iterable (expected a sequence of numbers)")
    out: list[float] = []
    for i, x in enumerate(seq):
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            raise ContractError(field_name, f"element {i} is {type(x).__name__}, expected a number")
        out.append(float(x))
    return out


def validate(kernel: Any) -> ValidatedKernel:
    if kernel is None:
        raise ContractError("<root>", "expected a kernel object")

    name = getattr(kernel, "name", None)
    if not isinstance(name, str) or not name.strip():
        raise ContractError("name", "required, a non-empty string")
    solve = getattr(kernel, "solve", None)
    if not callable(solve):
        raise ContractError("solve", "required, solve(n, tol, params) -> {'u', 'iters', 'residual'}")
    exact = getattr(kernel, "exact", None)
    if not callable(exact):
        raise ContractError("exact", "required, exact(n, params) -> u. Manufacture one — see contract.py")

    h_fn = getattr(kernel, "h", None)
    if h_fn is not None and not callable(h_fn):
        raise ContractError("h", "if present, must be h(n) -> mesh size")
    norm = getattr(kernel, "norm", None) or "l2"
    if norm not in ("l2", "max"):
        raise ContractError("norm", "if present, must be 'l2' or 'max'")

    # NOT `getattr(...) or DEFAULT_LEVELS`. An empty list is TRUTHY in
    # JavaScript and falsy in Python, so `||` keeps `[]` there and `or` would
    # silently substitute the default here — the same source line meaning two
    # different things. Caught by the port's own battery, which is what a
    # cross-language pair is for.
    levels = getattr(kernel, "levels", None)
    levels = list(DEFAULT_LEVELS if levels is None else levels)
    if not levels:
        raise ContractError("levels", "if present, must be a non-empty sequence of resolutions")
    for n in levels:
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ContractError("levels", f"every level must be a positive integer, got {n!r}")
    ordered = tuple(sorted(levels))
    if len(set(ordered)) != len(ordered):
        raise ContractError("levels", "duplicate level in levels")

    params = dict(getattr(kernel, "params", None) or {})

    # THE PART THAT ACTUALLY RUNS.
    n0 = ordered[0]
    try:
        out = solve(n=n0, tol=1e-6, params=params)
    except Exception as e:  # noqa: BLE001 — any failure here is a contract failure
        raise ContractError("solve", f"raised at the smallest level (n={n0}): {e}")
    if not isinstance(out, Mapping):
        raise ContractError("solve", "must return a mapping {'u', 'iters', 'residual'}")
    u = _as_vector(out.get("u"), "solve()['u']")
    iters = out.get("iters")
    if iters is not None and (isinstance(iters, bool) or not isinstance(iters, (int, float)) or not math.isfinite(iters)):
        raise ContractError("solve()['iters']", "if present, must be a finite number")
    res = out.get("residual")
    if res is not None and (isinstance(res, bool) or not isinstance(res, (int, float)) or not math.isfinite(res)):
        raise ContractError("solve()['residual']", "if present, must be a finite number or None")

    try:
        ex = exact(n=n0, params=params)
    except Exception as e:  # noqa: BLE001
        raise ContractError("exact", f"raised at the smallest level (n={n0}): {e}")
    e0 = _as_vector(ex, "exact()")
    if len(e0) != len(u):
        raise ContractError(
            "exact",
            f"returned length {len(e0)} but solve() returned length {len(u)} at n={n0} "
            "— they must sample the same grid",
        )

    h = h_fn(n0) if h_fn else 1.0 / n0
    if not isinstance(h, (int, float)) or not math.isfinite(h) or h <= 0:
        raise ContractError("h", f"must return a positive finite mesh size, got {h!r}")

    return ValidatedKernel(
        name=name, levels=ordered, params=params, norm=norm,
        h=h_fn if h_fn else (lambda n: 1.0 / n),
        solve=solve, exact=exact, length=len(u),
    )


def norm_of(diff: Sequence[float], h: float, kind: str) -> float:
    """Grid norms. The h weight is what makes the discrete L2 norm converge to
    the continuous one; without it a refining study measures a norm that is
    itself changing, and the "order" picks up an extra half power.

    Summation is deliberately naive rather than :func:`math.fsum`. fsum is the
    more accurate choice in isolation, but the JavaScript sibling accumulates
    sequentially, and the cross-language differential is SHARPER when the two
    are algorithmically identical: matching leaves only libm noise between
    them, so any real drift stands out instead of hiding under a permanent
    offset. Accuracy is not the binding constraint here — the errors being
    summed span a few orders of magnitude at most.
    """
    if kind == "max":
        return max((abs(d) for d in diff), default=0.0)
    total = 0.0
    for d in diff:
        total += d * d
    return math.sqrt(h * total)


def error_of(u: Sequence[float], ex: Sequence[float], h: float, kind: str) -> float:
    if len(u) != len(ex):
        raise ContractError("exact", f"length mismatch during study: {len(u)} vs {len(ex)}")
    return norm_of([a - b for a, b in zip(u, ex)], h, kind)
