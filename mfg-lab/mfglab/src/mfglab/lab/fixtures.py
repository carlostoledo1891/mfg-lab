"""fixtures.py — the kernels the Lab batteries study. Python twin of
``mfg-lab/tests/lab-fixtures.js``.

These ship inside the package rather than beside the tests because the
cross-language differential needs the two languages to study the SAME problems,
and because they double as the worked examples a new user copies.

WHY JACOBI AND NOT CONJUGATE GRADIENTS — a fixture mistake worth keeping. CG has
finite termination: on an m-unknown system it reaches the exact answer in m
steps, so at m=15 the residual fell from 4e-2 to 2e-16 in one iteration and
every tolerance below that returned bit-identical output. The tolerance knob was
inert, so the order study's contamination test had nothing to detect and passed
trivially — a green check measuring nothing. Jacobi converges linearly, so the
error moves continuously with the tolerance, and it is the honest fixture for
this lab's domain anyway: fictitious play, Picard and fixed-point MFG solvers
converge linearly and none terminate finitely.

THE MANUFACTURED SOLUTION IS DELIBERATELY NOT sin(pi x). That was the first
draft and it is an EIGENVECTOR of the discrete Laplacian, so an iterative solver
lands on the exact answer almost immediately. A fixture that cannot exhibit the
phenomenon under test is the same species of defect as a certificate that cannot
go red.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np


def jacobi(m: int, h: float, f: np.ndarray, k2: float, tol: float, maxit: int) -> dict:
    """Jacobi for the shifted 1D Dirichlet operator ``-u'' - k2 u = f``.

    ``k2 = 0`` is the Laplacian. ``k2 > 0`` is Helmholtz, whose iteration matrix
    has spectral radius ``2 cos(pi h) / (2 - h^2 k2)``, crossing 1 at
    ``k = 2 sin(pi h / 2) / h -> pi``. That one parameter carries a genuine,
    derivable failure boundary at the first eigenvalue, which is what makes it a
    fixture for the failure map rather than an invented one.

    Bails out on non-finite iterates, as a real solver does, so a divergent
    point does not spend its whole budget on NaN.
    """
    h2 = h * h
    diag = 2.0 - h2 * k2
    u = np.zeros(m)
    nf = math.sqrt(float(np.sum(f * f)))

    def relres(w: np.ndarray) -> float:
        aw = np.empty(m)
        aw[0] = (2 * w[0] - (w[1] if m > 1 else 0.0)) / h2 - k2 * w[0]
        if m > 2:
            aw[1:-1] = (2 * w[1:-1] - w[:-2] - w[2:]) / h2 - k2 * w[1:-1]
        if m > 1:
            aw[-1] = (2 * w[-1] - w[-2]) / h2 - k2 * w[-1]
        d = f - aw
        return math.sqrt(float(np.sum(d * d))) / nf

    iters, rel = 0, 1.0
    # Overflow is an ANTICIPATED outcome here, not a bug: past k ~ pi this
    # iteration is supposed to blow up, and the failure map classifies exactly
    # that. numpy would print a RuntimeWarning per divergent point, which is
    # noise about a result we are deliberately producing. Errors are still
    # detected — `relres` returns inf/nan and the loop breaks on it.
    with np.errstate(over="ignore", invalid="ignore"):
      while iters < maxit:
          rel = relres(u)
          if rel < tol or not math.isfinite(rel):
              break
          v = np.empty(m)
          v[0] = ((u[1] if m > 1 else 0.0) + h2 * f[0]) / diag
          if m > 2:
              v[1:-1] = (u[:-2] + u[2:] + h2 * f[1:-1]) / diag
          if m > 1:
              v[-1] = (u[-2] + h2 * f[-1]) / diag
          u = v
          iters += 1
    return {"u": u.tolist(), "iters": iters, "residual": rel}


def u_exact(x: float | np.ndarray):
    return x * (1 - x) * np.exp(x)


def minus_upp(x: float | np.ndarray):
    return x * (3 + x) * np.exp(x)


def _interior(n: int, fn) -> np.ndarray:
    h = 1.0 / n
    return fn(np.arange(1, n) * h)


@dataclass
class _Kernel:
    name: str
    levels: tuple
    _solve: Any = field(repr=False, default=None)
    _exact: Any = field(repr=False, default=None)
    params: dict = field(default_factory=dict)
    norm: str = "l2"

    def h(self, n: int) -> float:
        return 1.0 / n

    def solve(self, n: int, tol: float, params: dict | None = None) -> dict:
        return self._solve(n, tol, params or {})

    def exact(self, n: int, params: dict | None = None):
        return self._exact(n, params or {})


def _poisson_solve(n, tol, params):
    return jacobi(n - 1, 1.0 / n, _interior(n, minus_upp), 0.0, tol, 400_000)


#: ``-u'' = f``. Central differences: truncation O(h^2), so order 2.
poisson1d = _Kernel("poisson1d (central differences, Jacobi)", (16, 32, 64, 128),
                    _poisson_solve, lambda n, p: _interior(n, u_exact).tolist())


def _helmholtz_solve(n, tol, params):
    k = float(params.get("k", 0.0) or 0.0)
    k2 = k * k
    f = _interior(n, minus_upp) - k2 * _interior(n, u_exact)
    return jacobi(n - 1, 1.0 / n, f, k2, tol, 50_000)


#: ``-u'' - k^2 u = f``, same manufactured u. Jacobi fails past k ~ pi.
helmholtz1d = _Kernel("helmholtz1d (shifted Laplacian, Jacobi)", (16, 32, 64),
                      _helmholtz_solve, lambda n, p: _interior(n, u_exact).tolist())


def _euler_solve(n, tol, params):
    h = 1.0 / n
    u = [0.0] * (n + 1)
    for i in range(n):
        u[i + 1] = u[i] + h * math.pi * math.cos(math.pi * i * h)
    return {"u": u, "iters": 1, "residual": None}


#: ``u' = pi cos(pi x)``, explicit Euler, DIRECT. Order 1, and exactly zero
#: iteration movement — the control for the contamination test.
euler1d = _Kernel("euler1d (explicit Euler, direct)", (16, 32, 64, 128), _euler_solve,
                  lambda n, p: [math.sin(math.pi * i / n) for i in range(n + 1)])


def _stalled_solve(n, tol, params):
    out = _poisson_solve(n, tol, params)
    h = 1.0 / n
    u = np.asarray(out["u"]) + 1e-3 * np.sin(2 * math.pi * np.arange(1, n) * h)
    return {"u": u.tolist(), "iters": out["iters"], "residual": out["residual"]}


#: poisson1d carrying a fixed modelling error — a dropped term, or a wrong
#: boundary condition. Converges beautifully to the wrong thing: errors keep
#: falling and the spread stays narrow, so only a DECLARED order catches it.
stalled = _Kernel("stalled (poisson1d + a dropped term)", (16, 32, 64, 128),
                  _stalled_solve, lambda n, p: _interior(n, u_exact).tolist())

_PRESCRIBED = {16: 1e-2, 32: 1e-3, 64: 5e-4, 128: 4.9e-4}


def _pre_solve(n, tol, params):
    amp = _PRESCRIBED[n] * math.sqrt(2.0)
    u = amp * np.sin(2 * math.pi * np.arange(1, n) / n)
    return {"u": u.tolist(), "iters": 1, "residual": None}


#: A synthetic fixture with a PRESCRIBED error sequence — no PDE is solved. It
#: clears the monotonicity and contamination rules and lands on the
#: interval-width rule, which no physical kernel here reaches. Written because a
#: correct-but-untested branch is one refactor from wrong.
pre_asymptotic = _Kernel("preAsymptotic (synthetic fixture, prescribed errors)", (16, 32, 64, 128),
                         _pre_solve, lambda n, p: [0.0] * (n - 1))


def _explodes_solve(n, tol, params):
    if float(params.get("k", 0.0) or 0.0) > 4:
        raise RuntimeError(f"unsupported regime k={params['k']}")
    return _helmholtz_solve(n, tol, params)


#: Raises on a parameter value, so the failure map has a ``threw`` point to
#: classify rather than to die on.
explodes = _Kernel("explodes (throws above k=4)", (16, 32, 64),
                   _explodes_solve, lambda n, p: _interior(n, u_exact).tolist())

__all__ = ["jacobi", "poisson1d", "helmholtz1d", "euler1d", "stalled", "pre_asymptotic",
           "explodes", "u_exact", "minus_upp"]
