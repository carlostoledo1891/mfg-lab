"""Cross-language differential test: the Python port must agree with the SHIPPED
JavaScript kernel to machine precision on the certified equilibrium totals.

This is the architecture the project committed to — Python is the source of
truth for the mathematics, mfg-lab.html's JS is a verified port, and CI asserts
they agree so the two cannot silently drift. tools/js_reference.js extracts the
MWD kernel from mfg-lab.html at run time and solves each scenario in Node; this
test solves the same scenarios in Python and compares.

Totals are the comparison object because they are the unique, physical content:
for S1 the per-population split is not unique (monotone, not strict) but the
totals are; S2/S3 are fully unique. So totals agree to ~1e-9 even though the two
implementations take independent floating-point paths.

Chain closed by this test plus test-wardrop-diff.js:
  Python  ==  shipped JS  ==  dev battery  ==  paper Table I.
"""
import json
import os
import shutil
import subprocess

import pytest

import mfglab

HERE = os.path.dirname(__file__)
JS_REF = os.path.abspath(os.path.join(HERE, "..", "tools", "js_reference.js"))

# scenario -> (wT, Q1, Q2, tol, max_steps), matching js_reference.js exactly
SCEN = {
    "S1": (1, 2, 100, 100, 1e-8, 6000),
    "S2": (2, 2, 100, 50, 1e-8, 6000),
    "S3": (3, 2, 100, 50, 1e-7, 12000),
}


@pytest.fixture(scope="module")
def js_reference():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not found — cross-language differential test needs Node")
    if not os.path.exists(JS_REF):
        pytest.skip(f"js_reference.js not found at {JS_REF}")
    out = subprocess.run([node, JS_REF], capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        pytest.fail(f"js_reference.js failed: {out.stderr[:400]}")
    return json.loads(out.stdout)


@pytest.mark.parametrize("name", ["S1", "S2", "S3"])
def test_python_totals_match_shipped_js(js_reference, name):
    scen, wT, Q1, Q2, tol, ms = SCEN[name]
    py = mfglab.solve_scenario(scen, wT, Q1, Q2, tol=tol, max_steps=ms)
    js = js_reference[name]

    # both must actually be certified equilibria, or "agreement" is vacuous
    assert py["polished"] and py["gap"] < 1e-9, f"Python {name} not certified"
    assert js["polished"] and js["gap"] < 1e-9, f"JS {name} not certified"

    d_tot = max(abs(a - b) for a, b in zip(py["totals"], js["totals"]))
    assert d_tot < 1e-9, (
        f"{name}: Python and shipped-JS totals differ by {d_tot:.2e} "
        f"(> 1e-9) — the port has drifted from the artifact"
    )


def test_js_reference_reads_the_shipped_artifact(js_reference):
    """The JS side must carry the artifact's sha256, so we know which file was
    validated (the stale-harness lesson, FINDINGS.md Result 5)."""
    assert "sha256" in js_reference and len(js_reference["sha256"]) == 16
