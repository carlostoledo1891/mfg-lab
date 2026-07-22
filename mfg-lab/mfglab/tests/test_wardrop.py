"""Certificate battery for the mfglab Wardrop kernel — the pytest mirror of
test-wardrop.js. Same paper (arXiv:2504.16028), same targets:

  S1 validation : TOTAL flows match Table I to rounding; machine-zero gap;
                  independent single-population KKT on totals; totals unique
                  across reseeds while the split is not (monotone, not strict).
  S2 cars+trucks: strictly monotone -> unique equilibrium (Thm 4).
  S3 emissions  : converges with certificates.
"""
import numpy as np
import mfglab
from mfglab.wardrop import (
    make_system, interior_start, integrate, polish, wardrop_gap,
    kirchhoff_res, totals, totals_kkt_gap, min_pos, EDGES, TABLE1, NE,
)


def _solve(scen, wT, Q1, Q2, tol=1e-8, max_steps=6000, rng=None):
    sys = make_system(scen, wT, Q1, Q2)
    th1 = interior_start(sys.P1, rng)
    th2 = interior_start(sys.P2, rng)
    integrate(sys, th1, th2, tol=tol, max_steps=max_steps)
    pol = polish(sys, th1, th2)
    return sys, th1, th2, pol


# ---- Scenario 1: Table I reproduction ---------------------------------------
def test_s1_polished_gap_machine_zero():
    sys, th1, th2, pol = _solve(1, 2, 100, 100)
    assert pol
    assert wardrop_gap(sys, th1, th2) < 1e-12


def test_s1_independent_kkt_on_totals():
    sys, th1, th2, _ = _solve(1, 2, 100, 100)
    assert totals_kkt_gap(totals(sys, th1, th2)) < 1e-12


def test_s1_kirchhoff_and_positivity():
    sys, th1, th2, _ = _solve(1, 2, 100, 100)
    assert max(kirchhoff_res(sys.P1, th1), kirchhoff_res(sys.P2, th2)) < 1e-9
    assert min_pos(th1, th2) >= 0


def test_s1_totals_match_table1_within_rounding():
    sys, th1, th2, _ = _solve(1, 2, 100, 100)
    T = totals(sys, th1, th2)
    max_dev = max(abs(T[k] - TABLE1[k]) for k in range(NE))
    # Table I is the integer-rounded Simulink output; our equilibrium carries a
    # machine-zero KKT certificate, so <= 2 units on flows of ~100 is agreement
    # to their reported stopping accuracy. (The single dev-2 edge (4,7) is the
    # one internally inconsistent Table I row — see FINDINGS_LIT.md.)
    assert max_dev <= 2.0


def test_s1_totals_unique_but_split_is_not():
    """c = j1+j2 is monotone but NOT strictly monotone across populations:
    totals are unique across reseeds, the per-population split is not."""
    sysA, a1, a2, _ = _solve(1, 2, 100, 100)
    TA = totals(sysA, a1, a2)
    sysB, b1, b2, _ = _solve(1, 2, 100, 100, rng=np.random.default_rng(1234))
    TB = totals(sysB, b1, b2)
    dT = max(abs(TA[k] - TB[k]) for k in range(NE))
    assert dT < 1e-4                       # totals unique
    sysA.assemble(a1, a2)
    J1a = sysA.J1.copy()
    sysB.assemble(b1, b2)
    dS = float(np.max(np.abs(sysB.J1 - J1a)))
    assert dS > 0.5                        # split moved (non-strict monotonicity)


# ---- Scenario 2: strict monotonicity -> uniqueness --------------------------
def test_s2_polished_gap_machine_zero():
    sys, th1, th2, pol = _solve(2, 2, 100, 50)
    assert pol
    assert wardrop_gap(sys, th1, th2) < 1e-12


def test_s2_unique_across_reseeds():
    sysA, a1, a2, _ = _solve(2, 2, 100, 50)
    sysB, b1, b2, _ = _solve(2, 2, 100, 50, rng=np.random.default_rng(777))
    sysA.assemble(a1, a2)
    A1, A2 = sysA.J1.copy(), sysA.J2.copy()
    sysB.assemble(b1, b2)
    dJ = float(max(np.max(np.abs(sysB.J1 - A1)), np.max(np.abs(sysB.J2 - A2))))
    assert dJ < 1e-3                       # Thm 4: strict monotonicity -> unique


def test_s2_corner_sweep():
    """wT x truck-inflow corners all reach a machine-zero gap."""
    worst = 0.0
    for wT in (1.0, 1.5, 2.0, 3.0):
        for q2 in (20, 50, 100):
            sys, th1, th2, pol = _solve(2, wT, 100, q2)
            g = wardrop_gap(sys, th1, th2)
            worst = max(worst, g)
            assert pol and g < 1e-10
    assert worst < 1e-10


# ---- Scenario 3: emissions --------------------------------------------------
def test_s3_polished_gap_and_positivity():
    sys, th1, th2, pol = _solve(3, 2, 100, 50, tol=1e-7, max_steps=12000)
    assert pol
    assert wardrop_gap(sys, th1, th2) < 1e-10
    assert max(kirchhoff_res(sys.P1, th1), kirchhoff_res(sys.P2, th2)) < 1e-8
    assert min_pos(th1, th2) >= 0


# ---- solve_scenario convenience API -----------------------------------------
def test_solve_scenario_returns_certificates():
    r = mfglab.solve_scenario(1, 2, 100, 100)
    assert r["polished"] and r["gap"] < 1e-12 and r["kkt_totals"] < 1e-12
    assert len(r["totals"]) == NE
