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

Two implementations printing PASS at each other is exactly what this file exists
to prevent, so the chain is only worth its name if its first link — "the JS side
read the SHIPPED artifact" — is itself gated. See
test_js_reference_reads_the_shipped_artifact for how, and for what it used to
fail to prove.

NOTHING here skips. A missing Node, a missing js_reference.js and an artifact
outside the export set are all FAILURES: this gate is the sole reason the Python
port is admissible at all, and a gate that did not run is not a gate that passed.
"""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import mfglab

HERE = Path(__file__).resolve().parent
JS_REF = HERE.parent / "tools" / "js_reference.js"
NODE = shutil.which("node")

# scenario -> (wT, Q1, Q2, tol, max_steps), matching js_reference.js exactly
SCEN = {
    "S1": (1, 2, 100, 100, 1e-8, 6000),
    "S2": (2, 2, 100, 50, 1e-8, 6000),
    "S3": (3, 2, 100, 50, 1e-7, 12000),
}


def _real(p):
    """Compare paths through realpath on BOTH sides. Node's path.resolve does not
    follow symlinks and Path.resolve does; applying realpath to the emitted path
    and to the export set alike makes any symlinked checkout cancel out."""
    return os.path.realpath(str(p))


def _tree_root():
    """Find the root of whichever tree we are running in, and say WHICH tree.

    Two trees run this file. The monorepo, where tools/build-public.js is the one
    authority on what ships and unshipped files sit right beside shipped ones —
    this is where the hazard lives. And an exported public tree, which is BUILT by
    that allowlist and therefore contains nothing but shipped files, but does not
    carry build-public.js itself (it is not in ALLOW or SKEL).

    Nearest root wins, because a staged export lives INSIDE the monorepo
    (.work/public/): walking past it to the monorepo root would judge exported
    paths against monorepo paths and go red on a correct tree.
    """
    for d in [HERE, *HERE.parents]:
        if (d / "tools" / "build-public.js").is_file():
            return d, "monorepo"
        # an exported tree: the public skeleton at the root, the academic
        # subtrees hoisted out of academic/ by build-public.js's srcOf.
        if (d / "LICENSING.md").is_file() and not (d / "academic").is_dir():
            return d, "export"
    return None, None


def _shipped_paths(root):
    """The export set as build-public.js defines it: ALLOW + ENCLOSURE sources,
    mapped through its own srcOf and resolved against its own ROOT. Derived, never
    transcribed — the day mfg-lab.html splits into several papers this set changes
    by itself, and a hardcoded filename would not."""
    prog = (
        "const b=require(process.argv[1]);const p=require('path');"
        "const rel=[...b.ALLOW,...b.ENCLOSURE.map(e=>e[0])].map(b.srcOf);"
        "process.stdout.write(JSON.stringify(rel.map(r=>p.resolve(b.ROOT,r))));"
    )
    out = subprocess.run(
        [NODE, "-e", prog, str(root / "tools" / "build-public.js")],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0:
        pytest.fail(
            "could not read the export set from tools/build-public.js "
            f"(exit {out.returncode}): {out.stderr[:400]}\n"
            "This test cannot decide which artifact ships without it, and a "
            "provenance check that cannot name the shipped file is not a check."
        )
    return {_real(x) for x in json.loads(out.stdout)}


@pytest.fixture(scope="module")
def js_reference():
    if NODE is None:
        pytest.fail(
            "node not found — the cross-language differential DID NOT RUN. This is "
            "a failure, not a skip: the Python port is admissible only behind a "
            "working equivalence gate, and with no Node there is no gate."
        )
    if not JS_REF.is_file():
        pytest.fail(
            f"js_reference.js is missing at {JS_REF} — the JS half of the "
            "differential is gone. A harness file that vanished is never a "
            "legitimate skip. Restore it, or retire this test deliberately."
        )
    out = subprocess.run([NODE, str(JS_REF)], capture_output=True, text=True,
                         timeout=300)
    if out.returncode != 0:
        pytest.fail(
            f"js_reference.js failed (exit {out.returncode}): {out.stderr[:600]}"
        )
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
    """Bind the differential to the IDENTITY of the artifact, not to the SHAPE of
    a hash.

    This assertion used to read `len(js_reference["sha256"]) == 16`. It proved a
    16-character string had been emitted; it never proved WHOSE. Measured
    2026-07-28: with js_reference.js pointed at an unshipped copy of mfg-lab.html
    (same kernel, one appended HTML comment, sha 05a1c775e95bcda8 instead of the
    shipped d9398650ff82206a) the entire Python suite passed 101/101, exit 0 —
    and with a copy whose S2 cost coefficient had been altered, this test still
    passed while only the numeric comparison caught the drift. So the gate written
    to remember the stale-harness lesson (FINDINGS.md Result 5) was the one place
    the lesson was not implemented.

    It matters most on the day mfg-lab.html splits into several papers: a
    js_reference.js left aimed at a surviving-but-unshipped mfg-lab.html would go
    on printing a perfectly valid sha, and this suite would stay green against an
    artifact nobody ships. Three assertions, in order:

      1. js_reference.js says WHICH file it read.
      2. that file exists and its sha256 is the one it emitted — provenance
         recomputed here, not taken on the JS side's word.
      3. that file is a member of the SHIPPED export set, derived from
         tools/build-public.js (ALLOW + ENCLOSURE), never transcribed. A
         hardcoded filename dies the moment the file moves, which is precisely
         what is about to happen.
    """
    art = js_reference.get("artifact")
    assert art, (
        "js_reference.js emitted no `artifact` field, so this test cannot know "
        "which file it read. A sha with no path is not provenance. Re-add the "
        "field (see that file's header) rather than weakening this assertion."
    )
    p = Path(art)
    assert p.is_file(), (
        f"js_reference.js reports reading {art}, which is not a file now. Either "
        "it raced a moving artifact or it printed a path it never opened."
    )

    got = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    assert js_reference.get("sha256") == got, (
        f"provenance mismatch for {art}: js_reference.js emitted sha256 "
        f"{js_reference.get('sha256')!r}, but that file hashes to {got!r}. The "
        "emitted hash does not describe the emitted path."
    )

    root, mode = _tree_root()
    assert root is not None, (
        "cannot locate the tree root from "
        f"{HERE} — found neither tools/build-public.js (monorepo) nor an exported "
        "public tree. Without one of the two there is no definition of 'shipped', "
        "so this provenance check has nothing to check against."
    )

    if mode == "monorepo":
        shipped = _shipped_paths(root)
        assert _real(p) in shipped, (
            f"js_reference.js read {art}, which is NOT in the export set.\n"
            f"  expected: one of the {len(shipped)} files build-public.js ships "
            "(ALLOW + ENCLOSURE)\n"
            f"  found:    {_real(p)}\n"
            "The Python port would have been certified against an artifact the "
            "project does not publish. If the artifact moved, re-point "
            "js_reference.js; if it moved out of the allowlist, it is not the "
            "reference and this differential must be re-aimed deliberately."
        )
    else:
        # An exported tree is BUILT from the allowlist, so everything in it ships
        # and everything outside it does not — containment IS membership here.
        # Weaker than the monorepo branch (it cannot distinguish two files inside
        # the export), and that is the honest limit: the export carries no
        # allowlist to consult. The monorepo branch is the one that must hold.
        assert _real(root) == os.path.commonpath([_real(root), _real(p)]), (
            f"js_reference.js read {art}, which is outside the exported tree at "
            f"{root}. An export contains only files it ships; a reference "
            "reaching outside it is reading something this repo does not publish."
        )
