"""Certificate battery for mfglab.continuum — the SIN-MFG kernel port.

Layer-A parity with sin-mfg/tests/test-sin.js for the shipped (centered)
scheme, plus the structural certificates of the adjoint-matched scheme.
Doctrine: gates that can go red (mutants included), measured values
recorded, no fabricated floors.  The cross-language differential against
the shipped artifact lives in test_crosslang_continuum.py.
"""
import math

import pytest

from mfglab import continuum as C


@pytest.fixture(scope="module")
def base():
    return C.picard()


# ---------------- shipped scheme: Layer-A parity ----------------

def test_picard_converges(base):
    assert base["conv"], f"res {base['res']:.2e} after {base['it']} it"
    assert base["it"] < 100


def test_mass_all_slices(base):
    assert C.mass_drift(base["field"]) < 1e-12


def test_positivity_strict(base):
    assert C.min_density(base["field"]) > 0


def test_clearing_balance(base):
    assert C.clearing_worst(base) < 1e-9


def test_budget(base):
    assert C.budget_error(base) < 1e-6


def test_t3_marginal_flatness(base):
    worst, nmarg = C.t3_flatness(base)
    assert nmarg > 0, "no marginal hours — flatness check would be vacuous"
    assert worst < 1e-9


def test_exploitability_nonnegative(base):
    a = C.dp_audit(base["price"], base["field"])
    assert a["eps"] >= -1e-9


def test_corner_sweep():
    """Small corner sweep (subset of the JS 64-corner box): every converged
    corner must certify; convergence rate and failures reported, not hidden."""
    corners = [
        dict(sol=0.6, EHYD=2.0), dict(sol=1.8, EHYD=5.0),
        dict(pk=0.8, PMAX=1.5), dict(phi=2.0, PMIN=0.30),
        dict(sol=1.8, pk=0.2, EHYD=2.0), dict(phi=0.0, PMAX=4.0),
    ]
    conv = 0
    for kw in corners:
        r = C.picard(C.Params(**kw))
        if not r["conv"]:
            continue  # honest: some corners stall (documented JS behavior)
        conv += 1
        assert C.mass_drift(r["field"]) < 1e-12, kw
        assert C.clearing_worst(r) < 1e-9, kw
        worst, nmarg = C.t3_flatness(r)
        if nmarg:
            assert worst < 1e-9, kw
    assert conv >= 4, f"only {conv}/6 corners converged"


# ---------------- adjoint-matched scheme: structural certs ----------------

def _test_field():
    return [1.8 * (x - 2.8) ** 2 + 0.4 * math.sin(3 * x) for x in C.XS]


def test_transpose_exact():
    u = _test_field()
    al = C.interface_alpha(u, 0.8)
    # coverage: the frozen field must exercise clamp and interior
    n_cl = sum(1 for f in range(1, C.NX) if abs(al[f]) >= C.AMAX)
    n_in = sum(1 for f in range(1, C.NX) if abs(al[f]) < C.AMAX)
    assert n_cl >= 1 and n_in >= 1, "test field lacks clamp/interior coverage"
    assert C.transpose_defect(u, 0.8) < 1e-12
    assert C.transpose_defect(_test_field(), 2.4) < 1e-12


def test_conservation_as_adjoint_identity():
    import numpy as np
    F = C.mat_fp(_test_field(), 0.8)
    H = C.mat_hjb(_test_field(), 0.8)
    assert abs(F.sum(axis=0) - 1).max() < 1e-13     # 1ᵀM_FP = 1ᵀ
    assert abs(H.sum(axis=1) - 1).max() < 1e-13     # M_HJB·1 = 1


def test_m_matrix():
    import numpy as np
    F = C.mat_fp(_test_field(), 0.8)
    off = F - np.diag(np.diag(F))
    assert off.max() <= 1e-15                        # off-diag ≤ 0
    assert np.diag(F).min() >= 1.0                   # diag ≥ 1


def test_mutant_dropped_sign_split_is_caught():
    """Gate can go red: donor-left flux (no sign split) breaks the transpose."""
    import numpy as np
    u = _test_field()
    al = C.interface_alpha(u, 0.8)
    rd = C.NU * C.DT / (C.HX * C.HX)
    rh = C.DT / C.HX
    M = np.zeros((C.NX, C.NX))
    for i in range(C.NX):
        fL = 1 if i > 0 else 0
        fR = 1 if i < C.NX - 1 else 0
        if i > 0:
            M[i, i - 1] = -rd * fL - rh * al[i]
        M[i, i] = 1 + rd * (fL + fR) + rh * al[i + 1]
        if i < C.NX - 1:
            M[i, i + 1] = -rd * fR
    H = C.mat_hjb(u, 0.8)
    defect = np.abs(M - H.T).max() / np.abs(M).max()
    assert defect > 1e-3, "mutant not caught — the gate is vacuous"


def test_upwind_equilibrium_certifies():
    """The matched scheme reaches its OWN certified equilibrium.  Its numbers
    differ from the shipped scheme's by construction (numerical diffusion) —
    both are recorded; neither is 'the' answer without its scheme label."""
    r = C.picard(field_solver=C.solve_field_upwind)
    assert r["conv"], f"res {r['res']:.2e}"
    assert C.mass_drift(r["field"]) < 1e-12
    assert C.min_density(r["field"]) > 0
    assert C.clearing_worst(r) < 1e-9
    assert C.budget_error(r) < 1e-6
    worst, nmarg = C.t3_flatness(r)
    assert nmarg > 0 and worst < 1e-9
    # the two schemes genuinely differ — if they agree to 1e-6 something is
    # wrong (the variant silently fell back to the shipped solver)
    base = C.picard()
    assert abs(r["disp"]["w"] - base["disp"]["w"]) > 1e-3


# ---------------- the literal discrete-KKT point (implicit scheme) ----------------

@pytest.fixture(scope="module")
def implicit():
    return C.picard(field_solver=C.solve_field_implicit)


def test_implicit_equilibrium_certifies(implicit):
    r = implicit
    assert r["conv"]
    assert C.mass_drift(r["field"]) < 1e-12
    assert C.min_density(r["field"]) > 0
    assert C.clearing_worst(r) < 1e-9
    worst, nmarg = C.t3_flatness(r)
    assert nmarg > 0 and worst < 1e-9


def test_kkt_point_certificate(implicit):
    """The deferred 'literal discrete KKT' statement, now measured: exact
    telescoping duality + zero control gradient (to the FD floor) + clean
    clamp signs at the solved equilibrium."""
    k = C.kkt_point_residual(implicit)
    assert k["telescoping"] < 1e-14, k
    assert k["stationarity"] < 1e-8, k          # FD truncation floor, not scheme
    assert k["clamp_sign_violations"] == 0, k
    assert k["n_interior"] > 300 and k["n_clamped"] > 0   # coverage


def test_kkt_mutant_staggered_freeze_is_caught(implicit):
    """Gate can go red: evaluating the SAME certificate with the staggered
    controls (the semi-implicit convention) must break the telescoping at
    O(dt) — the identity is load-bearing, not decorative."""
    r = implicit
    price = r["price"]
    staggered = [C.interface_alpha(r["field"]["u"][t + 1], price[t])
                 for t in range(C.NT)]
    J_bad = C.discrete_objective(staggered, price)
    u0m0 = C.HX * sum(r["field"]["u"][0][i] * r["field"]["m"][0][i]
                      for i in range(C.NX))
    assert abs(J_bad - u0m0) > 1e-4
