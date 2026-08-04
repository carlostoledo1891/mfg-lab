"""Battery for the Python Lab instruments — the twin of the two JavaScript
batteries (``mfg-lab/tests/test-order-study.js``, ``test-failure-map.js``).

The load-bearing checks are the ones where the instruments must REFUSE. A study
that reports "order 2" for a second-order scheme proves nothing that a study
with the honesty machinery deleted would not also report; what distinguishes
them is whether the refusals fire.

Two are worth reading if you read any:

``test_disabling_contamination_produces_a_confident_wrong_answer``
    turns the contamination test off on a genuinely second-order scheme at a
    slack tolerance and asserts the study then reports an order that is visibly
    NOT 2 — the wrong number every hand-rolled convergence table risks printing,
    made executable.

``test_failure_map_brackets_the_derived_boundary``
    checks the map against a boundary theory fixes in advance, not against
    whatever it printed.
"""
from __future__ import annotations

import math

import pytest

from mfglab.certificate import Certificate
from mfglab.lab import ContractError, map_box, study, validate
from mfglab.lab import fixtures as F
from mfglab.lab.failure_map import DIVERGED, OK, STALLED, THREW

LEVELS = [16, 32, 64]

# The failure boundary of Jacobi on -u'' - k^2 u, derived independently of the
# code under test: rho(k) = 2 cos(pi h)/(2 - h^2 k^2) crosses 1 at this k.
N = 32
KSTAR = 2 * math.sin(math.pi / (2 * N)) * N


# --------------------------------------------------------------- contract

def test_validate_accepts_a_conforming_kernel():
    v = validate(F.poisson1d)
    assert v.name == F.poisson1d.name
    assert v.length == 15  # n=16 -> 15 interior nodes


@pytest.mark.parametrize(
    "attr,value,field",
    [
        ("name", "", "name"),
        ("levels", [], "levels"),
        ("levels", [16, 16, 32], "levels"),
        ("levels", [16, 32.5], "levels"),
        ("norm", "l1", "norm"),
    ],
)
def test_validate_rejects_a_malformed_kernel(attr, value, field):
    import copy
    k = copy.copy(F.poisson1d)
    setattr(k, attr, value)
    with pytest.raises(ContractError) as e:
        validate(k)
    assert e.value.field == field


def test_validation_runs_the_kernel_rather_than_typechecking_it():
    """A contract checked with isinstance passes for a solve() that raises."""
    import copy
    k = copy.copy(F.poisson1d)
    k.solve = lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))
    with pytest.raises(ContractError) as e:
        validate(k)
    assert e.value.field == "solve" and "boom" in str(e.value)


def test_certificate_refuses_to_exist_without_a_falsifier():
    with pytest.raises(ValueError, match="falsifier"):
        Certificate(claim="something is true", verdict="PROVED", falsifier=None, evidence={"x": 1})
    with pytest.raises(ValueError, match="must carry evidence"):
        Certificate(claim="x", verdict="PROVED", falsifier="a counterexample")


# ------------------------------------------------------------ order study

def test_second_order_scheme_is_identified():
    r = study(F.poisson1d, tol=1e-9, levels=LEVELS)
    assert r.code == "PROVED"
    lo, hi = r.order
    assert 1.5 < lo and hi < 2.5, f"order interval {r.order} does not identify 2"
    assert r.certificate.falsifier
    assert any("reference solution" in a for a in r.certificate.assumes)


def test_first_order_direct_scheme_is_identified_and_has_no_iteration_movement():
    r = study(F.euler1d, tol=1e-9, levels=LEVELS)
    assert r.code == "PROVED"
    lo, hi = r.order
    assert 0.5 < lo and hi < 1.5, f"order interval {r.order} does not identify 1"
    assert r.worst_ratio == 0.0


def test_slack_tolerance_is_refused_not_credited_with_an_order():
    r = study(F.poisson1d, tol=1e-3, levels=LEVELS)
    assert r.code == "ITERATION_CONTAMINATION"
    assert not r.certificate.proved
    assert "STOPPING CRITERION" in r.certificate.why


def test_disabling_contamination_produces_a_confident_wrong_answer():
    """THE load-bearing test. Same scheme, same grids, same slack tolerance —
    only the check is removed, and a REFUSED becomes a PROVED carrying an order
    that is not the true one."""
    r = study(F.poisson1d, tol=1e-3, levels=LEVELS, _unsafe_skip_contamination_test=True)
    assert r.code == "PROVED"
    lo, hi = r.order
    assert not (1.5 < lo and hi < 2.5), (
        f"expected a WRONG order for a second-order scheme, got {r.order} — "
        "if this is right, the contamination test is not preventing anything"
    )
    assert any("DISABLED" in a for a in r.certificate.assumes), (
        "a certificate produced with the test disabled must say so loudly"
    )


def test_a_declared_order_catches_what_the_other_rules_cannot():
    """A fixed modelling error leaves the errors falling and the spread narrow.
    Undeclared it is PROVED with an order near zero — true, and skimmable.
    Declared, the same data is a refusal."""
    undeclared = study(F.stalled, tol=1e-9, levels=LEVELS)
    assert undeclared.code == "PROVED"
    assert undeclared.order[1] < 0.5

    declared = study(F.stalled, tol=1e-9, levels=LEVELS, expected_order=2)
    assert declared.code == "DECLARED_ORDER_MISMATCH"
    assert "declared order 2" in declared.certificate.why
    assert "FLOOR" in declared.certificate.why


def test_a_correct_declaration_is_accepted():
    """The declared-order test is not a one-way ratchet."""
    r = study(F.poisson1d, tol=1e-9, levels=LEVELS, expected_order=2)
    assert r.code == "PROVED"
    assert "consistent with the declared order 2" in r.certificate.claim


def test_a_spread_wider_than_one_supports_no_claim():
    r = study(F.pre_asymptotic, tol=1e-9)
    assert r.code == "SPREAD_TOO_WIDE"
    assert "adjacent integer orders" in r.certificate.why


def test_two_levels_cannot_produce_an_order():
    r = study(F.poisson1d, tol=1e-9, levels=[32, 64])
    assert r.code == "TOO_FEW_LEVELS"
    assert "three levels" in r.certificate.why


def test_expected_order_must_be_positive_and_finite():
    with pytest.raises(ValueError, match="expected_order"):
        study(F.poisson1d, tol=1e-9, levels=LEVELS, expected_order=-1)


# ------------------------------------------------------------ failure map

def test_failure_map_brackets_the_derived_boundary():
    r = map_box(F.helmholtz1d, sweep={"k": [0.5, 6]}, samples=12, n=N, tol=1e-6)
    assert r.code == "POINTS_FAILED"
    assert [p.outcome for p in r.points if p.params["k"] <= 3.0] == [OK] * 6
    assert [p.outcome for p in r.points if p.params["k"] >= 3.5] == [DIVERGED] * 6

    assert len(r.brackets) == 1
    b = r.brackets[0]
    assert b["from_"] <= KSTAR <= b["to"], (
        f"bracket [{b['from_']}, {b['to']}] misses the derived boundary k*={KSTAR:.4f}"
    )


def test_a_box_below_the_boundary_is_proved_but_says_sampled():
    r = map_box(F.helmholtz1d, sweep={"k": [0.5, 2.5]}, samples=6, n=N, tol=1e-6)
    assert r.code == "PROVED"
    assert not r.brackets
    assert "SAMPLED" in r.certificate.claim and "not a proof of the box" in r.certificate.claim
    assert any("thinner than the sample spacing" in a for a in r.certificate.assumes)


def test_slow_is_not_the_same_answer_as_divergent():
    r = map_box(F.helmholtz1d, sweep={"k": [3.05, 3.11]}, samples=3, n=N, tol=1e-9)
    assert [p.outcome for p in r.points] == [STALLED] * 3
    assert all(1e-9 < p.residual < 1 for p in r.points)
    assert "too slowly for the budget" in r.points[0].detail


def test_a_raising_kernel_is_classified_rather_than_fatal():
    r = map_box(F.explodes, sweep={"k": [1, 6]}, samples=6, n=N, tol=1e-6)
    assert r.counts[THREW] > 0
    assert len(r.points) == 6
    assert all("unsupported regime" in p.detail for p in r.points if p.outcome == THREW)


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (dict(sweep={}), "sweep is required"),
        (dict(sweep={"a": [0, 1], "b": [0, 1], "c": [0, 1]}), "one or two parameters"),
        (dict(sweep={"k": [6, 1]}), r"lo < hi"),
        (dict(sweep={"k": [1, 6]}, samples=1), "spot-check"),
    ],
)
def test_the_sweep_spec_is_checked(kwargs, match):
    with pytest.raises(ValueError, match=match):
        map_box(F.helmholtz1d, **kwargs)


def test_two_axes_and_the_grid_indexing():
    r = map_box(F.helmholtz1d, sweep={"k": [0.5, 6], "inert": [0, 1]}, samples=4, n=N, tol=1e-6)
    assert len(r.points) == 16
    assert [a.name for a in r.axes] == ["k", "inert"]
    # `inert` is not read by the kernel, so outcomes must depend on k alone.
    # A transposed index breaks this and nothing else would notice.
    by_k: dict = {}
    for p in r.points:
        by_k.setdefault(p.params["k"], set()).add(p.outcome)
    assert all(len(v) == 1 for v in by_k.values())


def test_a_direct_solver_has_no_residual_and_never_stalls():
    r = map_box(F.euler1d, sweep={"anything": [0, 1]}, samples=4, n=64, tol=1e-6)
    assert r.code == "PROVED"
    assert all(p.residual is None for p in r.points)
