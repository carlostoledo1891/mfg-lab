"""mfglab — certified kernels for mean-field games and network equilibria.

v0.1 ports the multi-population Wardrop / Hessian-Riemannian-Flow kernel
(Bakaryan-Aoun-Ribeiro-Hovakimyan-Gomes, arXiv:2504.16028), the cheapest and
most portable of the lab's kernels: it was already headless JS with assertions,
and it proves the certificate standard is formulation-neutral (a network VI, not
just a PDE).

v0.2 adds the SIN-MFG continuum kernel (`mfglab.continuum`) — the FD-monotone
HJB/Fokker-Planck field solve, band clearing, hydro dispatch with the
water-value bisection, Picard driver and DP exploitability audit, ported
statement-for-statement from `sin-mfg/sin-mfg.html`. The cross-language
differential (`tests/test_crosslang_continuum.py`) holds the Python against
the shipped artifact at ~1e-16 on the equilibrium price path. It also ships
the Achdou adjoint-matched scheme (`solve_field_upwind`, FP = HJBᵀ exact)
as a second, structurally-certified solver for the same model.

v0.3 adds `mfglab.lab` — the Live Lab's INSTRUMENTS, which are not solvers.
They take a kernel you already have and answer questions its own test suite
does not: `study` runs a convergence study that refuses to report an order it
cannot support, and `map_box` finds where in a parameter box a solver stops
working. Both speak one small kernel contract and return a `Certificate` that
cannot exist without a falsifier. `mfglab.certificate` is the first slice of
the eqcert Python twin; it grows by demand, and the interval and exact-rational
libraries are deliberately NOT ported, because an unused second copy of
delicate arithmetic is the drift `eqcert/tests/test-single-source.js` exists to
prevent.

The single source of truth for the mathematics is Python; the in-page JavaScript
(mfg-lab.html, sin-mfg.html) is a verified port. The cross-language tests assert
the implementations agree to machine precision on the certified equilibria, so
they cannot silently drift. The Lab INSTRUMENTS went the other way — specified
in JavaScript first, because the browser Lab is their primary surface — and
`tests/test_crosslang_lab.py` holds them together either way, which makes the
direction documentation rather than correctness.
"""
from .wardrop import (
    EDGES, EXITS, TABLE1,
    make_system, interior_start, integrate, polish,
    wardrop_gap, kirchhoff_res, totals, totals_kkt_gap,
    solve_scenario,
)
from . import continuum, lab
from .certificate import Certificate

__version__ = "0.3.0"
__all__ = [
    "EDGES", "EXITS", "TABLE1",
    "make_system", "interior_start", "integrate", "polish",
    "wardrop_gap", "kirchhoff_res", "totals", "totals_kkt_gap",
    "solve_scenario", "continuum", "lab", "Certificate",
]
