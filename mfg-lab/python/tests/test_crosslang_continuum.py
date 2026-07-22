"""Cross-language differential: mfglab.continuum (Python) against the
SHIPPED sin-mfg.html kernel, extracted and run by sin_reference.js at test
time.  Same pattern as test_crosslang.py (Wardrop): the JS artifact is the
deployed reference; a drift between the two implementations is a red gate,
and the sha256 of the artifact actually validated is asserted into the
record.  Skips (loudly) when node is unavailable — a skipped gate is not a
pass."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from mfglab import continuum as C

RUNNER = Path(__file__).resolve().parents[3] / "sin-mfg" / "tools" / "sin_reference.js"


@pytest.fixture(scope="module")
def js():
    if shutil.which("node") is None:
        pytest.skip("node unavailable — differential DID NOT run")
    out = subprocess.check_output(["node", str(RUNNER)], text=True)
    return json.loads(out)


def test_sha_recorded(js):
    assert len(js["sha256"]) == 16, "no artifact provenance"


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
