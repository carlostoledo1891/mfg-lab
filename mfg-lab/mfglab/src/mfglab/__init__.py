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

The single source of truth for the mathematics is Python; the in-page JavaScript
(mfg-lab.html, sin-mfg.html) is a verified port. The cross-language tests assert
the implementations agree to machine precision on the certified equilibria, so
they cannot silently drift.
"""
from .wardrop import (
    EDGES, EXITS, TABLE1,
    make_system, interior_start, integrate, polish,
    wardrop_gap, kirchhoff_res, totals, totals_kkt_gap,
    solve_scenario,
)
from . import continuum

__version__ = "0.2.0"
__all__ = [
    "EDGES", "EXITS", "TABLE1",
    "make_system", "interior_start", "integrate", "polish",
    "wardrop_gap", "kirchhoff_res", "totals", "totals_kkt_gap",
    "solve_scenario", "continuum",
]
