"""Cross-language differential: mfglab.continuum (Python) against the
SHIPPED sin-mfg.html kernel, extracted and run by sin_reference.js at test
time.  Same pattern as test_crosslang.py (Wardrop): the JS artifact is the
deployed reference; a drift between the two implementations is a red gate,
and the artifact actually validated is PINNED here by path and sha256 — see
test_reference_reads_the_shipped_artifact for what that used to fail to prove.

NOTHING here skips.  A missing Node, a missing sin_reference.js and an artifact
outside the export set are all FAILURES: this gate is the sole reason the Python
continuum port is admissible at all, and a gate that did not run is not a gate
that passed.  (This docstring used to say the test 'skips (loudly) when node is
unavailable — a skipped gate is not a pass', which states the rule and then
breaks it in the same sentence.)"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from mfglab import continuum as C

HERE = Path(__file__).resolve().parent
# CROSS-TRACK, AND SPELLED OUT. THIS file has not moved; its TARGET has. parents[2] was
# `academic/`, and naming "sin-mfg" under it worked only because the JS reference happened to
# share this file's parent track. M7a (2026-07-28) moved it to research/stock-constraint, so
# parents[2] is now the wrong root as well as the wrong name. The index is the REPO ROOT,
# and the track is named rather than inferred, so this survives anything that moves THIS
# file's neighbours.
# M5a (2026-07-28): and now THIS file moved too — academic/mfg-lab/python -> python/ — so the
# root is two levels up, not four: python/tests -> python -> root. The index is re-derived from
# this file's OWN depth, which is the only way to get it right; a grep for the old package path
# could never have seen this line.
#
# AND THE TRACK NAME IS NOW A TWO-TREE QUESTION, which is a PRE-EXISTING defect this edit
# surfaced rather than caused. This file SHIPS (build-public.js ALLOW), and the export is flat:
# the note ships as sin-mfg/tools/sin_reference.js there, not research/stock-constraint/. Since
# M7a named the private track literally, the exported copy has been pointing at a path that
# does not exist in the tree it runs in — invisible here, because the monorepo branch is the
# one every local gate takes. Both trees are enumerated now, nearest-existing wins, and the
# is_file() guard below still fails LOUD rather than silently skipping if neither is there.
_ROOT = HERE.parents[1]
RUNNER = next(
    (p for p in (_ROOT / "site" / "sin-mfg" / "tools" / "sin_reference.js",  # monorepo (phase 2: path == route)
                 _ROOT / "sin-mfg" / "tools" / "sin_reference.js")                        # export
     if p.is_file()),
    _ROOT / "site" / "sin-mfg" / "tools" / "sin_reference.js",
)
NODE = shutil.which("node")

# ---------------------------------------------------------------------------
# Provenance: ONE implementation of the export-set check, imported, never copied
# ---------------------------------------------------------------------------
# Deciding whether a path is SHIPPED is delicate — the export set has to be
# derived from tools/build-public.js at run time (a transcribed filename dies
# the day an artifact splits or moves), and the tree root has to be the NEAREST
# one, because a staged export lives inside the monorepo at .work/public/ and
# walking past it would judge exported paths against monorepo paths.  That check
# already landed in test_crosslang.py.  This module IMPORTS it rather than
# restating it: two implementations of one delicate check is exactly the drift
# core/interval/tests/test-single-source.js exists to catch, and no gate reaches across
# a copy-paste.  Loaded BY PATH, so it does not depend on pytest's import mode
# or on sys.path, and under a private module name so pytest's own import of the
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


@pytest.fixture(scope="module")
def js():
    if NODE is None:
        pytest.fail(
            "node not found — the cross-language differential DID NOT RUN. This "
            "is a failure, not a skip: the Python continuum port is admissible "
            "only behind a working equivalence gate, and with no Node there is "
            "no gate."
        )
    if not RUNNER.is_file():
        pytest.fail(
            f"sin_reference.js is missing at {RUNNER} — the JS half of the "
            "differential is gone. A harness file that vanished is never a "
            "legitimate skip. Restore it, or retire this test deliberately."
        )
    out = subprocess.run([NODE, str(RUNNER)], capture_output=True, text=True,
                         timeout=600)
    if out.returncode != 0:
        pytest.fail(
            f"sin_reference.js failed (exit {out.returncode}): {out.stderr[:600]}"
        )
    return json.loads(out.stdout)


def test_reference_reads_the_shipped_artifact(js):
    """Bind the differential to the IDENTITY of the artifact, not to the SHAPE
    of a hash.

    This assertion used to read `len(js["sha256"]) == 16` under the name
    `test_sha_recorded`.  It proved a 16-character string had been emitted; it
    never proved WHOSE — the same defect measured on test_crosslang.py
    2026-07-28, where the entire Python suite passed 101/101, exit 0, against an
    artifact the project does not ship.  `.work/public/sin-mfg/sin-mfg.html` is
    a byte-identical copy sitting in this very tree: every number in this file
    agrees perfectly when the reference reads it, and only provenance notices.

    It matters most the day sin-mfg.html moves or splits: a sin_reference.js
    left aimed at a surviving-but-unshipped copy would go on printing a
    perfectly valid sha, and this suite would stay green against an artifact
    nobody publishes.  Three assertions, in order:

      1. sin_reference.js says WHICH file it read.
      2. that file exists and its sha256 is the one it emitted — provenance
         recomputed here, not taken on the JS side's word.
      3. that file is a member of the SHIPPED export set, derived from
         tools/build-public.js (ALLOW + ENCLOSURE), never transcribed.
    """
    art = js.get("artifact")
    assert art, (
        "sin_reference.js emitted no `artifact` field, so this test cannot know "
        "which file it read. A sha with no path is not provenance. Re-add the "
        "field (see that file's header) rather than weakening this assertion."
    )
    p = Path(art)
    assert p.is_file(), (
        f"sin_reference.js reports reading {art}, which is not a file now. "
        "Either it raced a moving artifact or it printed a path it never opened."
    )

    got = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    assert js.get("sha256") == got, (
        f"provenance mismatch for {art}: sin_reference.js emitted sha256 "
        f"{js.get('sha256')!r}, but that file hashes to {got!r}. The emitted "
        "hash does not describe the emitted path."
    )

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
            f"sin_reference.js read {art}, which is NOT in the export set.\n"
            f"  expected: one of the {len(shipped)} files build-public.js ships "
            "(ALLOW + ENCLOSURE)\n"
            f"  found:    {prov._real(p)}\n"
            "The Python port would have been certified against an artifact the "
            "project does not publish. If the artifact moved, re-point "
            "sin_reference.js (or SIN_HTML, if that is what set it); if it moved "
            "out of the allowlist, it is not the reference and this differential "
            "must be re-aimed deliberately."
        )
    else:
        # An exported tree is BUILT from the allowlist, so everything in it ships
        # and everything outside it does not — containment IS membership here.
        # Honestly weaker than the monorepo branch (the export carries no
        # allowlist to consult); the monorepo branch is the one that must hold.
        assert prov._real(root) == os.path.commonpath(
            [prov._real(root), prov._real(p)]
        ), (
            f"sin_reference.js read {art}, which is outside the exported tree at "
            f"{root}. An export contains only files it ships; a reference "
            "reaching outside it is reading something this repo does not publish."
        )


def test_both_converged(js):
    r = C.picard()
    assert js["converged"] and r["conv"]
    assert js["iterations"] == r["it"], "iteration paths diverged"


def test_price_path_identical(js):
    r = C.picard()
    dev = max(abs(a - b) for a, b in zip(r["price"], js["price"]))
    assert dev < 1e-13, f"max |price_py − price_js| = {dev:.3e}"


def test_water_value_identical(js):
    r = C.picard()
    assert abs(r["disp"]["w"] - js["w"]) < 1e-12


def test_certificates_identical(js):
    r = C.picard()
    assert abs(C.mass_drift(r["field"]) - js["massDrift"]) < 1e-14
    assert abs(C.clearing_worst(r) - js["clearWorst"]) < 1e-12
    a = C.dp_audit(r["price"], r["field"])
    assert abs(a["eps"] - js["eps"]) < 1e-12
    assert abs(C.welfare_of(r["price"], r["field"], r["disp"], r["P"])
               - js["welfare"]) < 1e-10
