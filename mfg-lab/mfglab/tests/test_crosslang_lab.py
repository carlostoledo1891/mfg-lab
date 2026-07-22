"""Cross-language differential for the Lab instruments: the Python twin and the
shipped JavaScript must reach the same DECISIONS on the same problems.

WHY THIS GATE EXISTS. The web Lab lets a user switch between the JavaScript
instruments (instant, in the page) and the Python ones (``pip install
mfg-lab``, on their own machine and their own kernel). A toggle between two
implementations is only honest if something holds them together — otherwise it
is two tools with one name, and the moment they disagree the user has no way to
know which one lied. That is the same drift argument ``eqcert`` makes about
duplicated arithmetic, one level up, and no gate reaches across a language
boundary unless it is written to.

WHAT IS COMPARED
    codes      exactly. Refusal PROSE is written for a human and is allowed to
               read differently in each language; the DECISION is not. Every
               refusal carries a machine-readable code and those must match.
    outcomes   exactly, for the failure map. ok/stalled/diverged/threw is a
               classification, and a classification that differs across
               runtimes is a bug, not a rounding difference.
    numbers    to tolerances DERIVED from a measurement, below.

THE TOLERANCES, AND WHERE THEY COME FROM. Measured 2026-07-22 across all eleven
cases, on this machine:

    worst relative error deviation   5.1e-14
    worst order-interval deviation   4.2e-14
    worst residual deviation         5.0e-12
    iteration counts                 IDENTICAL in every case

The two implementations run the same algorithm in IEEE double precision, so the
only irreducible difference is libm: ``exp`` is not correctly rounded and JS and
numpy may disagree in the last ulp, which the Jacobi iteration then amplifies by
the condition number of the discrete Laplacian. The gates below sit a few orders
above those measurements for platform headroom, and many orders BELOW anything
that could change a verdict — the study reasons about ~1e-3 relative differences
between grid levels, and ``RESOLUTION`` (what an order claim must resolve) is
0.5. So any drift able to alter a decision fails this test long before it
alters one.

Iteration counts are asserted to agree within 1 rather than exactly. They were
measured identical, but a residual agreeing only to 1e-12 could in principle
cross the tolerance one iteration earlier on another platform, and a gate that
flakes is a gate that gets disabled.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess

import pytest

from mfglab.lab import fixtures as F
from mfglab.lab import map_box, study

HERE = os.path.dirname(__file__)
JS_REF = os.path.abspath(os.path.join(HERE, "..", "tools", "lab_reference.js"))

# Derived above; see the module docstring.
TOL_ERROR_REL = 1e-11
TOL_ORDER_ABS = 1e-9
TOL_RESIDUAL_REL = 1e-9
TOL_ITERS_ABS = 1

LEVELS = [16, 32, 64]

STUDY_CASES = {
    "clean_second_order":   lambda: study(F.poisson1d, tol=1e-9, levels=LEVELS),
    "clean_first_order":    lambda: study(F.euler1d, tol=1e-9, levels=LEVELS),
    "contaminated":         lambda: study(F.poisson1d, tol=1e-3, levels=LEVELS),
    "contaminated_masked":  lambda: study(F.poisson1d, tol=1e-3, levels=LEVELS,
                                          _unsafe_skip_contamination_test=True),
    "floored_undeclared":   lambda: study(F.stalled, tol=1e-9, levels=LEVELS),
    "floored_declared":     lambda: study(F.stalled, tol=1e-9, levels=LEVELS, expected_order=2),
    "spread_too_wide":      lambda: study(F.pre_asymptotic, tol=1e-9, levels=[16, 32, 64, 128]),
    "too_few_levels":       lambda: study(F.poisson1d, tol=1e-9, levels=[32, 64]),
}

MAP_CASES = {
    "straddling": lambda: map_box(F.helmholtz1d, sweep={"k": [0.5, 6]}, samples=12, n=32, tol=1e-6),
    "safe":       lambda: map_box(F.helmholtz1d, sweep={"k": [0.5, 2.5]}, samples=6, n=32, tol=1e-6),
    "raising":    lambda: map_box(F.explodes, sweep={"k": [1, 6]}, samples=6, n=32, tol=1e-6),
}


@pytest.fixture(scope="module")
def js():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not found — the cross-language differential needs Node")
    if not os.path.exists(JS_REF):
        pytest.skip(f"lab_reference.js not found at {JS_REF}")
    out = subprocess.run([node, JS_REF], capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        pytest.fail(f"lab_reference.js failed: {out.stderr[:600]}")
    return json.loads(out.stdout)


def test_reference_names_the_files_it_read(js):
    """A differential that does not say WHICH bytes it compared is one edit away
    from certifying a stale pair (the stale-harness lesson, FINDINGS.md)."""
    assert set(js["sha256"]) == {"orderStudy", "failureMap", "fixtures"}
    assert all(len(v) == 16 for v in js["sha256"].values())


@pytest.mark.parametrize("name", list(STUDY_CASES))
def test_study_decisions_match(js, name):
    py = STUDY_CASES[name]()
    ref = js["studies"][name]

    assert py.code == ref["code"], (
        f"{name}: Python decided {py.code}, JavaScript decided {ref['code']} — "
        "the two implementations disagree about what this kernel deserves"
    )
    assert py.certificate.proved == ref["proved"], f"{name}: verdict disagrees with the code"


@pytest.mark.parametrize("name", [k for k, v in STUDY_CASES.items()])
def test_study_numbers_match(js, name):
    py = STUDY_CASES[name]()
    ref = js["studies"][name]

    if py.order is not None:
        assert ref["order"] is not None, f"{name}: Python reported an order interval and JavaScript did not"
        d = max(abs(a - b) for a, b in zip(py.order, ref["order"]))
        assert d < TOL_ORDER_ABS, (
            f"{name}: order intervals differ by {d:.2e} (> {TOL_ORDER_ABS:.0e}). "
            f"Python {py.order}, JavaScript {ref['order']}"
        )

    for row, jrow in zip(py.table, ref["table"]):
        assert row.n == jrow["n"]
        rel = abs(row.error - jrow["error"]) / abs(jrow["error"]) if jrow["error"] else 0.0
        assert rel < TOL_ERROR_REL, (
            f"{name} n={row.n}: errors differ by {rel:.2e} relative (> {TOL_ERROR_REL:.0e}). "
            f"Python {row.error:.17e}, JavaScript {jrow['error']:.17e} — the ports have drifted"
        )
        if row.iters is not None and jrow["iters"] is not None:
            assert abs(row.iters - jrow["iters"]) <= TOL_ITERS_ABS, (
                f"{name} n={row.n}: iteration counts differ by more than {TOL_ITERS_ABS} "
                f"(Python {row.iters}, JavaScript {jrow['iters']}) — the stopping rules have drifted"
            )


@pytest.mark.parametrize("name", list(MAP_CASES))
def test_map_classification_matches(js, name):
    py = MAP_CASES[name]()
    ref = js["maps"][name]

    assert py.code == ref["code"], f"{name}: Python {py.code}, JavaScript {ref['code']}"
    assert py.counts["ok"] == ref["counts"]["ok"], f"{name}: ok counts differ"
    assert py.counts["stalled"] == ref["counts"]["stalled"], f"{name}: stalled counts differ"
    assert py.counts["diverged"] == ref["counts"]["diverged"], f"{name}: diverged counts differ"
    assert py.counts["threw"] == ref["counts"]["threw"], f"{name}: threw counts differ"

    got = [p.outcome for p in py.points]
    assert got == ref["outcomes"], (
        f"{name}: the classification differs point by point.\n"
        f"  Python     {got}\n  JavaScript {ref['outcomes']}"
    )

    # Brackets are the answer a user acts on, so they are compared, not implied.
    assert len(py.brackets) == len(ref["brackets"]), f"{name}: different number of transition brackets"
    for pb, jb in zip(py.brackets, ref["brackets"]):
        assert pb["axis"] == jb["axis"]
        assert pb["from_"] == pytest.approx(jb["from"])
        assert pb["to"] == pytest.approx(jb["to"])
        assert (pb["fromOutcome"], pb["toOutcome"]) == (jb["fromOutcome"], jb["toOutcome"])


@pytest.mark.parametrize("name", list(MAP_CASES))
def test_map_residuals_match(js, name):
    py = MAP_CASES[name]()
    ref = js["maps"][name]
    for p, jr in zip(py.points, ref["residuals"]):
        if jr is None or p.residual is None or not math.isfinite(p.residual):
            continue
        rel = abs(p.residual - jr) / abs(jr)
        assert rel < TOL_RESIDUAL_REL, (
            f"{name}: residuals differ by {rel:.2e} relative at {p.params} "
            f"(Python {p.residual:.17e}, JavaScript {jr:.17e})"
        )


def test_the_differential_can_fail():
    """The gate must be able to go red, or it is decoration.

    Rather than mutating a shipped file, this compares two runs that SHOULD
    disagree — the same kernel at two tolerances — and asserts the comparison
    machinery notices. If this ever passes trivially, the assertions above are
    not comparing what they claim to.
    """
    a = study(F.poisson1d, tol=1e-9, levels=LEVELS)
    b = study(F.poisson1d, tol=1e-3, levels=LEVELS)
    assert a.code != b.code, "two genuinely different runs produced the same code — the comparison is inert"
    assert a.table and b.table, "a refusal must still hand back the table it measured, or there is nothing to compare"
    worst = max(abs(x.error - y.error) / y.error for x, y in zip(a.table, b.table))
    assert worst > TOL_ERROR_REL, (
        f"two genuinely different runs agree to {worst:.2e}, which is inside the gate's own tolerance "
        f"({TOL_ERROR_REL:.0e}) — the numeric comparison could not detect a real difference"
    )
