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

NOTHING here skips. A missing Node, a missing lab_reference.js and a source file
outside the export set are all FAILURES: this gate is the whole reason the
"switch to Python and get the same answer" claim is admissible, and a gate that
did not run is not a gate that passed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from mfglab.lab import fixtures as F
from mfglab.lab import map_box, study

HERE = Path(__file__).resolve().parent
JS_REF = HERE.parent / "tools" / "lab_reference.js"

# ---------------------------------------------------------------------------
# Provenance: ONE implementation of the export-set check, imported, never copied
# ---------------------------------------------------------------------------
# Deciding whether a path is SHIPPED is delicate — the export set has to be
# derived from tools/build-public.js at run time (a transcribed filename dies
# the day mfg-lab.html splits), and the tree root has to be the NEAREST one,
# because a staged export lives inside the monorepo at .work/public/ and walking
# past it would judge exported paths against monorepo paths. That check already
# landed in test_crosslang.py. This module IMPORTS it rather than restating it:
# two implementations of one delicate check is exactly the drift
# core/interval/tests/test-single-source.js exists to catch, and no gate reaches across
# a copy-paste. Loaded BY PATH, so it does not depend on pytest's import mode or
# on sys.path, and under a private module name so pytest's own import of the
# same file (with its assertion rewriting) is left alone.
PRIMARY = HERE / "test_crosslang.py"
_PROV = None


def _provenance():
    global _PROV
    if _PROV is None:
        if not PRIMARY.is_file():
            pytest.fail(
                f"test_crosslang.py is missing at {PRIMARY}. It owns the single "
                "implementation of the shipped-export-set check this test "
                "depends on. Restore it, or move that check somewhere both "
                "files can import — do NOT re-implement it here."
            )
        spec = importlib.util.spec_from_file_location("_mfglab_provenance", PRIMARY)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        _PROV = mod
    return _PROV


def _assert_shipped(role, p):
    """Fail unless `p` is a file the project actually publishes."""
    prov = _provenance()
    root, mode = prov._tree_root()
    assert root is not None, (
        f"cannot locate the tree root from {HERE} — found neither "
        "tools/build-public.js (monorepo) nor an exported public tree. Without "
        "one of the two there is no definition of 'shipped', so this provenance "
        "check has nothing to check against."
    )
    if mode == "monorepo":
        shipped = prov._shipped_paths(root)
        assert prov._real(p) in shipped, (
            f"lab_reference.js read {role} from {p}, which is NOT in the export "
            "set.\n"
            f"  expected: one of the {len(shipped)} files build-public.js ships "
            "(ALLOW + ENCLOSURE)\n"
            f"  found:    {prov._real(p)}\n"
            "The Python twin would have been certified against a file the "
            "project does not publish — a byte-identical stray under "
            ".work/public/ agrees perfectly and proves nothing. If the file "
            "moved, re-point lab_reference.js; if it moved out of the "
            "allowlist, it is not the reference and this differential must be "
            "re-aimed deliberately."
        )
    else:
        # An exported tree is BUILT from the allowlist, so everything in it ships
        # and everything outside it does not — containment IS membership here.
        # Honestly weaker than the monorepo branch (the export carries no
        # allowlist to consult); the monorepo branch is the one that must hold.
        assert prov._real(root) == os.path.commonpath(
            [prov._real(root), prov._real(p)]
        ), (
            f"lab_reference.js read {role} from {p}, which is outside the "
            f"exported tree at {root}. An export contains only files it ships; a "
            "reference reaching outside it is reading something this repo does "
            "not publish."
        )

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
        pytest.fail(
            "node not found — the cross-language differential DID NOT RUN. This "
            "is a failure, not a skip: the Python twin is admissible only behind "
            "a working equivalence gate, and with no Node there is no gate."
        )
    if not JS_REF.is_file():
        pytest.fail(
            f"lab_reference.js is missing at {JS_REF} — the JS half of the "
            "differential is gone. A harness file that vanished is never a "
            "legitimate skip. Restore it, or retire this test deliberately."
        )
    out = subprocess.run([node, str(JS_REF)], capture_output=True, text=True,
                         timeout=600)
    if out.returncode != 0:
        pytest.fail(
            f"lab_reference.js failed (exit {out.returncode}): {out.stderr[:600]}"
        )
    return json.loads(out.stdout)


ROLES = {"orderStudy", "failureMap", "fixtures"}


def test_reference_names_the_files_it_read(js):
    """Bind the differential to the IDENTITY of the files compared, not to the
    SHAPE of a hash.

    This used to assert `all(len(v) == 16 for v in js["sha256"].values())`. It
    proved three 16-character strings had been emitted; it never proved WHOSE —
    the same defect measured on test_crosslang.py 2026-07-28, where the whole
    Python suite passed 101/101 against an artifact the project does not ship.
    A sha with no path is not provenance, and .work/public/ already holds
    byte-identical strays whose numbers would agree perfectly.

    Three assertions per file, in order:

      1. lab_reference.js says WHICH file it read for each role.
      2. that file exists and its sha256 is the one emitted — provenance
         recomputed HERE, not taken on the JS side's word.
      3. that file is in the SHIPPED export set, derived at run time from
         tools/build-public.js (ALLOW + ENCLOSURE), never transcribed.
    """
    assert set(js["sha256"]) == ROLES, (
        f"lab_reference.js emitted shas for {sorted(js['sha256'])}, expected "
        f"{sorted(ROLES)} — the differential's inputs changed shape."
    )
    arts = js.get("artifacts")
    assert arts and set(arts) == ROLES, (
        "lab_reference.js emitted no complete `artifacts` map, so this test "
        f"cannot know which files it read (got {sorted(arts or [])}). Re-add the "
        "field (see that file's header) rather than weakening this assertion."
    )

    for role in sorted(ROLES):
        p = Path(arts[role])
        assert p.is_file(), (
            f"lab_reference.js reports reading {role} from {p}, which is not a "
            "file now. Either it raced a moving source or it printed a path it "
            "never opened."
        )
        got = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        assert js["sha256"][role] == got, (
            f"provenance mismatch for {role} ({p}): lab_reference.js emitted "
            f"sha256 {js['sha256'][role]!r}, but that file hashes to {got!r}. "
            "The emitted hash does not describe the emitted path."
        )
        _assert_shipped(role, p)


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
