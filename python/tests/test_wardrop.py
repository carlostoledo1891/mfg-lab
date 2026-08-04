"""Certificate battery for the mfglab Wardrop kernel — the pytest mirror of
test-wardrop.js, covering ALL 21 of its assertions with the same semantic
targets. Same paper (arXiv:2504.16028):

  S1 validation : HRF reaches 1e-8, then Newton polish; TOTAL flows match
                  Table I to rounding; machine-zero gap; independent
                  single-population KKT on totals; totals unique across
                  reseeds while the split is not (monotone, not strict).
  S2 cars+trucks: strictly monotone -> unique equilibrium (Thm 4); Kirchhoff;
                  12-corner wT x Q2 sweep.
  S3 emissions  : converges with certificates.
  PG duel       : exact polyhedral projection (30 random VI tests); PG is
                  COMPETITIVE in step count (never rig the comparison); the
                  differentiator is structural — pre-projection Kirchhoff
                  violation O(10) per step vs the flow's identical zero.

Reseeds use mulberry32 with the JS battery's seeds (1234/777/9) and the same
shared-stream order, so the receipts are directly comparable across languages
(the RNG port is bit-exact; gate-checked in test_crosslang_wardrop_battery.py).

Plus a RED CONTROL: the merit rule deleted in a test-local mutant integrator
must break the flow's own certificate (green suites prove nothing until they
can go red — failure catalog).
"""
import numpy as np
import mfglab
from mfglab.wardrop import (
    make_system, interior_start, integrate, polish, wardrop_gap,
    kirchhoff_res, totals, totals_kkt_gap, min_pos, mulberry32,
    proj_pop, pg_run, EDGES, TABLE1, NE,
)


def _solve(scen, wT, Q1, Q2, tol=1e-8, max_steps=6000, rng=None):
    sys = make_system(scen, wT, Q1, Q2)
    th1 = interior_start(sys.P1, rng)
    th2 = interior_start(sys.P2, rng)
    integrate(sys, th1, th2, tol=tol, max_steps=max_steps)
    pol = polish(sys, th1, th2)
    return sys, th1, th2, pol


# ---- Scenario 1: Table I reproduction ---------------------------------------
def test_s1_hrf_gap_before_polish():
    """JS #1: 'S1 HRF gap < 1e-8 then Newton polish ok'. The flow's OWN
    certificate, asserted separately from the polish — the polish can rescue
    an iterate the flow never earned (see the red control below)."""
    sys = make_system(1, 2, 100, 100)
    th1, th2 = interior_start(sys.P1), interior_start(sys.P2)
    r = integrate(sys, th1, th2, tol=1e-8)
    assert r["gap"] < 1e-8
    assert polish(sys, th1, th2)


def test_s1_polished_gap_machine_zero():
    sys, th1, th2, pol = _solve(1, 2, 100, 100)
    assert pol
    assert wardrop_gap(sys, th1, th2) < 1e-12


def test_s1_independent_kkt_on_totals():
    sys, th1, th2, _ = _solve(1, 2, 100, 100)
    assert totals_kkt_gap(totals(sys, th1, th2)) < 1e-12


def test_s1_kirchhoff_and_positivity():
    sys, th1, th2, _ = _solve(1, 2, 100, 100)
    assert kirchhoff_res(sys.P1, th1) < 1e-9      # JS #4 (pop1)
    assert kirchhoff_res(sys.P2, th2) < 1e-9      # JS #5 (pop2)
    # off-support flows are EXACTLY 0 after polish, so positivity is
    # theta >= 0 overall (+ >0 on support), never theta > 0 everywhere
    assert min_pos(th1, th2) >= 0                 # JS #6


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
    totals are unique across reseeds, the per-population split is not.
    Reseed = mulberry32(1234), shared stream, P1 drawn first — exactly the
    JS battery's reseed, so the receipt is comparable across languages."""
    sysA, a1, a2, _ = _solve(1, 2, 100, 100)
    TA = totals(sysA, a1, a2)
    sysB, b1, b2, _ = _solve(1, 2, 100, 100, rng=mulberry32(1234))
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


def test_s2_kirchhoff():
    """JS #11: 'S2 Kirchhoff < 1e-9'."""
    sys, th1, th2, _ = _solve(2, 2, 100, 50)
    assert max(kirchhoff_res(sys.P1, th1), kirchhoff_res(sys.P2, th2)) < 1e-9


def test_s2_unique_across_reseeds():
    sysA, a1, a2, _ = _solve(2, 2, 100, 50)
    sysB, b1, b2, _ = _solve(2, 2, 100, 50, rng=mulberry32(777))
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


# ---- Projected-gradient comparison (the duel) --------------------------------
# House rule from the failure catalog: the naive "HRF beats PG" narrative died
# under measurement. PG is COMPETITIVE in step count on this instance (13 vs 27
# to 1e-3; full convergence in ~106 steps); the differentiator is structural.
# Never rig this comparison.

def test_pg_projection_exact_30_random_vi_tests():
    """JS #17: exactness of the polyhedral projection is CHECKED, not assumed —
    <y-x, z-x> <= 0 for feasible z, plus feasibility of x itself.
    Same rng (mulberry32(9)) and same perturbation as the JS battery."""
    sys = make_system(2, 2, 100, 50)
    rng = mulberry32(9)
    for _t in range(30):
        y = interior_start(sys.P1, rng)
        for i in range(len(y)):
            y[i] += (rng() - 0.5) * 80.0        # push outside the polyhedron
        x = proj_pop(sys.P1, y)
        assert kirchhoff_res(sys.P1, x) <= 1e-8
        assert float(x.min()) >= -1e-9
        for _s in range(8):
            z = interior_start(sys.P1, rng)     # random feasible point
            assert float(np.dot(y - x, z - x)) <= 1e-6


def test_pg_converges_to_1e3_for_some_fixed_step():
    """JS #18: PG with the best fixed eta reaches gap 1e-3."""
    sys = make_system(2, 2, 100, 50)
    best = None
    for eta in (0.02, 0.05, 0.1, 0.2, 0.4):
        a, b = interior_start(sys.P1), interior_start(sys.P2)
        r = pg_run(sys, a, b, eta, 4000, 1e-3)
        if r["gap"] < 1e-3 and (best is None or r["steps"] < best["steps"]):
            best = {"eta": eta, "steps": r["steps"]}
    assert best is not None


def test_hrf_reaches_1e3():
    """JS #19: HRF (merit RK4) reaches gap 1e-3 on the same instance."""
    sys = make_system(2, 2, 100, 50)
    a, b = interior_start(sys.P1), interior_start(sys.P2)
    r = integrate(sys, a, b, tol=1e-3)
    assert r["gap"] < 1e-3


def test_pg_full_convergence_eta04():
    """JS #20: PG (eta 0.4) reaches 1e-12 within 300 steps — PG converges
    FULLY on this instance; publish it (honesty rule)."""
    sys = make_system(2, 2, 100, 50)
    a, b = interior_start(sys.P1), interior_start(sys.P2)
    r = pg_run(sys, a, b, 0.4, 600, 1e-12)
    assert r["gap"] < 1e-12 and r["steps"] <= 300


def test_pg_pre_projection_kirchhoff_violation_is_o10():
    """JS #21: the honest differentiator — PG's pre-projection iterate
    violates Kirchhoff by O(10) per step (feasibility by repair); the HRF
    trajectory conserves it identically (feasibility by geometry)."""
    sys = make_system(2, 2, 100, 50)
    a, b = interior_start(sys.P1), interior_start(sys.P2)
    pg_run(sys, a, b, 0.4, 50, 1e-12)
    c = np.zeros(NE)
    sys.assemble(a, b)
    sys.cost(sys.J1, sys.J2, 1, c)
    y = a - 0.4 * c[np.asarray(sys.P1.act)]
    assert kirchhoff_res(sys.P1, y) > 1


# ---- solve_scenario convenience API -----------------------------------------
def test_solve_scenario_returns_certificates():
    r = mfglab.solve_scenario(1, 2, 100, 100)
    assert r["polished"] and r["gap"] < 1e-12 and r["kkt_totals"] < 1e-12
    assert len(r["totals"]) == NE


# ---- RED CONTROL: the battery can go red ------------------------------------
def _integrate_merit_dropped(sys, th1, th2, tol, max_steps):
    """Test-local MUTANT of mfglab.wardrop.integrate with the merit rule
    DELETED: any positivity-preserving RK4 trial is accepted and dt still
    grows 1.3x. Everything else is identical. Returns the final gap and the
    count of merit violations (steps where the relative Wardrop gap
    INCREASED — the exact property the merit rule enforces)."""
    n1, n2 = len(th1), len(th2)
    k1a, k2a, k3a, k4a = (np.zeros(n1) for _ in range(4))
    k1b, k2b, k3b, k4b = (np.zeros(n2) for _ in range(4))
    ta, tb = np.zeros(n1), np.zeros(n2)
    dt = 1e-4
    steps = 0
    g = wardrop_gap(sys, th1, th2)
    violations = 0

    def trial():
        sys.rhs(th1, th2, k1a, k1b)
        ta[:] = th1 + 0.5 * dt * k1a
        tb[:] = th2 + 0.5 * dt * k1b
        if min_pos(ta, tb) <= 0:
            return None
        sys.rhs(ta, tb, k2a, k2b)
        ta[:] = th1 + 0.5 * dt * k2a
        tb[:] = th2 + 0.5 * dt * k2b
        if min_pos(ta, tb) <= 0:
            return None
        sys.rhs(ta, tb, k3a, k3b)
        ta[:] = th1 + dt * k3a
        tb[:] = th2 + dt * k3b
        if min_pos(ta, tb) <= 0:
            return None
        sys.rhs(ta, tb, k4a, k4b)
        ta[:] = th1 + dt / 6.0 * (k1a + 2 * k2a + 2 * k3a + k4a)
        tb[:] = th2 + dt / 6.0 * (k1b + 2 * k2b + 2 * k3b + k4b)
        if min_pos(ta, tb) <= 0:
            return None
        return wardrop_gap(sys, ta, tb)

    while steps < max_steps and g > tol:
        g_new = None
        tries = 0
        while tries < 50:
            g_new = trial()
            if g_new is not None:          # MERIT RULE DELETED HERE
                break
            dt *= 0.4
            tries += 1
        if g_new is None:
            break
        if g_new > g * (1 + 1e-12):
            violations += 1
        th1[:] = ta
        th2[:] = tb
        g = g_new
        steps += 1
        dt *= 1.3
    return {"steps": steps, "gap": g, "violations": violations}


def test_red_control_merit_rule_is_load_bearing():
    """Both directions of the kill: on the SAME S1 start and the SAME step
    budget, the clean integrator earns its certificate (gap < 1e-8, and by
    its acceptance test the gap never increases), while the merit-dropped
    mutant violates monotone descent and FAILS the flow's certificate — the
    named assertion 'S1 HRF gap < 1e-8' goes red on the mutant.
    (Measured 2026-07-27: mutant stalls at ~1e-3 with ~166 violations in 400
    steps; the polish would still rescue this iterate, which is exactly why
    the battery asserts the flow's gap separately from the polish.)"""
    budget = 400
    # clean direction: the certificate is earned
    sys = make_system(1, 2, 100, 100)
    c1, c2 = interior_start(sys.P1), interior_start(sys.P2)
    clean = integrate(sys, c1, c2, tol=1e-8, max_steps=budget)
    assert clean["gap"] < 1e-8
    # mutant direction: monotone descent fails AND the certificate is lost
    sys = make_system(1, 2, 100, 100)
    m1, m2 = interior_start(sys.P1), interior_start(sys.P2)
    mut = _integrate_merit_dropped(sys, m1, m2, tol=1e-8, max_steps=budget)
    assert mut["violations"] >= 1, "mutant unexpectedly monotone — control is dead"
    assert mut["gap"] > 1e-8, "mutant unexpectedly certified — control is dead"
