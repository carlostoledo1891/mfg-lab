#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_ml_beta.py — self-contained verifier for the attention-geometry note.

Decides, with Python fractions only (stdlib), that on the frozen GPT-tiny
attention scores embedded below:

  · PR(w) for w_i ∝ (1+β·s_i)^p  is strictly decreasing on the β-grid (p=2, p=1)
  · dual Σw² is strictly increasing (p=2)
  · flat scores give PR = dim exactly
  · planted mutants (flat; (β−3)²·s) fail strict decrease
  · fixture sha256 matches the three published certificates' pin

Softmax H/PR sound enclosure uses interval exp/log in eqcert (Node). This file
decides the rational-kernel certificate — the distinctive half — and checks the
pins. A skeptical reader needs only:

    python3 verify_ml_beta.py

SPDX-License-Identifier: MIT
Copyright (c) 2026 Carlos Toledo
"""
from __future__ import annotations

import hashlib
import json
import sys
from fractions import Fraction
from typing import Callable, List, Sequence

# ---------------------------------------------------------------------------
# CERTIFICATE DATA (committed fixture — sha256 pinned in CERT-ml-beta-*.json)
# ---------------------------------------------------------------------------

SEED = 0
P_PRIMARY = 2
BETA_GRID = [Fraction("1/4"), Fraction("1/2"), Fraction(1), Fraction("3/2"),
             Fraction(2), Fraction(3), Fraction(4), Fraction(6), Fraction(8)]
# IEEE binary64 scores, written as exact Fraction(numerator)/2**k via from float bits.
# Stored as the same decimal literals as fixtures/frozen_attn_scores.json; Fraction
# from float is lossless for finite floats.
SCORES_F64 = [
    -0.006244686667944583, 0.009383485655587137, 0.026350683891400856,
    0.0016395706897503288, -0.0008126143380353603, 0.016999061088513567,
    -0.02003186905922297, -0.0002932978869002959, -0.016945337622253722,
    -0.002777432087147219, 0.0015457793244680216, -0.014423454774380801,
    0.01035641755755256, 0.01721700215071087, -0.0036735485529039574,
    0.015610013203252112, -0.0031262436382945864, -0.007819210065303166,
    -0.0022981812158066306, 0.0029081189629996656, 0.03477829679899534,
    -0.0003601236294067441, -0.0038449052218670655, 0.016937875196637635,
    0.0072255203987375985, 0.013836544810765423, 0.016754166136397457,
    0.010088141717905803, -0.006244804451160461, 0.005167151014256437,
    -0.020716426069377368,
]
FIXTURE_SHA256 = "4f15743ea33e7972fb91ed4df412c6cd71c5d8aeb57639d2717e22876c8a9ca3"

passed = 0
failed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok  {name}" + (f"   {detail}" if detail else ""))
    else:
        failed += 1
        print(f"  FAIL {name}" + (f"   {detail}" if detail else ""))


def f64_to_q(x: float) -> Fraction:
    """Lossless: every finite float is an exact dyadic rational."""
    return Fraction(x)


def moments(scores: Sequence[Fraction], beta: Fraction, p: int):
    us = []
    for s in scores:
        base = 1 + beta * s
        if base <= 0:
            raise ValueError("kernel base non-positive")
        us.append(base ** p)
    Z = sum(us, Fraction(0))
    S2u = sum((u * u for u in us), Fraction(0))
    S2 = S2u / (Z * Z)
    PR = 1 / S2
    return PR, S2


def curve(scores: Sequence[Fraction], betas: Sequence[Fraction], p: int,
          scale: Callable[[Fraction, Fraction], Fraction]):
    out = []
    for b in betas:
        logits = [scale(b, s) for s in scores]
        # moments expects scores; pass logits as "s" with beta=1 → base=1+logit
        us = []
        for logit in logits:
            base = 1 + logit
            if base <= 0:
                raise ValueError("kernel base non-positive")
            us.append(base ** p)
        Z = sum(us, Fraction(0))
        S2u = sum((u * u for u in us), Fraction(0))
        S2 = S2u / (Z * Z)
        out.append((1 / S2, S2))
    return out


def strictly_decreasing(vals: Sequence[Fraction]) -> bool:
    return all(vals[i + 1] < vals[i] for i in range(len(vals) - 1))


def strictly_increasing(vals: Sequence[Fraction]) -> bool:
    return all(vals[i + 1] > vals[i] for i in range(len(vals) - 1))


def fixture_sha() -> str:
    payload = {
        "seed": SEED,
        "beta_grid": [float(b) for b in BETA_GRID],
        "scores": SCORES_F64,
    }
    # Match the on-disk JSON formatting used to compute the pin: re-load style.
    # The pin is over fixtures/frozen_attn_scores.json bytes, not a re-dump.
    # Embed those exact bytes below as FIXTURE_JSON.
    return hashlib.sha256(FIXTURE_JSON.encode("utf-8")).hexdigest()


# Exact file bytes of fixtures/frozen_attn_scores.json (pin source).
FIXTURE_JSON = r"""{
  "seed": 0,
  "beta_grid": [
    0.25,
    0.5,
    1.0,
    1.5,
    2.0,
    3.0,
    4.0,
    6.0,
    8.0
  ],
  "scores": [
    -0.006244686667944583,
    0.009383485655587137,
    0.026350683891400856,
    0.0016395706897503288,
    -0.0008126143380353603,
    0.016999061088513567,
    -0.02003186905922297,
    -0.0002932978869002959,
    -0.016945337622253722,
    -0.002777432087147219,
    0.0015457793244680216,
    -0.014423454774380801,
    0.01035641755755256,
    0.01721700215071087,
    -0.0036735485529039574,
    0.015610013203252112,
    -0.0031262436382945864,
    -0.007819210065303166,
    -0.0022981812158066306,
    0.0029081189629996656,
    0.03477829679899534,
    -0.0003601236294067441,
    -0.0038449052218670655,
    0.016937875196637635,
    0.0072255203987375985,
    0.013836544810765423,
    0.016754166136397457,
    0.010088141717905803,
    -0.006244804451160461,
    0.005167151014256437,
    -0.020716426069377368
  ],
  "rows": [
    {
      "beta": 0.25,
      "entropy": 3.433982067350596,
      "participation_ratio": 30.99968142073823,
      "max_prob": 0.03251409726340878
    },
    {
      "beta": 0.5,
      "entropy": 3.4339666458131157,
      "participation_ratio": 30.998724761361203,
      "max_prob": 0.03277182535515681
    },
    {
      "beta": 1.0,
      "entropy": 3.433904888908139,
      "participation_ratio": 30.99489185775792,
      "max_prob": 0.033292399053594775
    },
    {
      "beta": 1.5,
      "entropy": 3.433801812987749,
      "participation_ratio": 30.98849106747132,
      "max_prob": 0.03381984861410548
    },
    {
      "beta": 2.0,
      "entropy": 3.4336572980160294,
      "participation_ratio": 30.979512925088056,
      "max_prob": 0.03435423709477106
    },
    {
      "beta": 3.0,
      "entropy": 3.4332434746015563,
      "participation_ratio": 30.953790577073686,
      "max_prob": 0.0354440832570012
    },
    {
      "beta": 4.0,
      "entropy": 3.4326624739131177,
      "participation_ratio": 30.91766467646219,
      "max_prob": 0.036562442672710395
    },
    {
      "beta": 6.0,
      "entropy": 3.430995227271645,
      "participation_ratio": 30.814026346450937,
      "max_prob": 0.03888672206159136
    },
    {
      "beta": 8.0,
      "entropy": 3.4286482706638326,
      "participation_ratio": 30.668380488071552,
      "max_prob": 0.041331111773887194
    }
  ]
}
"""


def main() -> int:
    print("== verify_ml_beta: rational attention PR on frozen GPT-tiny scores ==")
    scores = [f64_to_q(x) for x in SCORES_F64]
    dim = len(scores)
    check("fixture-sha256", fixture_sha() == FIXTURE_SHA256, fixture_sha()[:16] + "…")

    def true_scale(b: Fraction, s: Fraction) -> Fraction:
        return b * s

    def flat_scale(b: Fraction, s: Fraction) -> Fraction:
        return Fraction(0)

    def quad_scale(b: Fraction, s: Fraction) -> Fraction:
        return (b - 3) * (b - 3) * s

    # p=2 primary
    cur = curve(scores, BETA_GRID, P_PRIMARY, true_scale)
    PRs = [c[0] for c in cur]
    S2s = [c[1] for c in cur]
    check("PR-strictly-decreasing-p2", strictly_decreasing(PRs),
          f"PR0={float(PRs[0]):.6f} PRn={float(PRs[-1]):.6f}")
    check("S2-strictly-increasing-p2", strictly_increasing(S2s))
    check("control-PR-not-increasing", not strictly_increasing(PRs))

    # p=1 sibling
    cur1 = curve(scores, BETA_GRID, 1, true_scale)
    check("PR-strictly-decreasing-p1", strictly_decreasing([c[0] for c in cur1]))

    # flat mutant
    flat_scores = [Fraction(0)] * dim
    flat_cur = curve(flat_scores, BETA_GRID, P_PRIMARY, true_scale)
    flat_PRs = [c[0] for c in flat_cur]
    check("mutant-flat-not-decreasing", not strictly_decreasing(flat_PRs))
    check("mutant-flat-PR-equals-dim", all(pr == dim for pr in flat_PRs), f"PR={flat_PRs[0]}")

    # quadratic mutant
    quad = curve(scores, BETA_GRID, P_PRIMARY, quad_scale)
    check("mutant-quadratic-not-decreasing",
          not strictly_decreasing([c[0] for c in quad]))

    # bases positive on true curve
    ok_base = True
    for b in BETA_GRID:
        for s in scores:
            if 1 + b * s <= 0:
                ok_base = False
    check("kernel-bases-positive", ok_base)

    print(f"== verify_ml_beta: {passed} passed, {failed} failed ==")
    if failed:
        print("REFUSED")
        return 1
    print("ATTENTION GEOMETRY (rational PR): VERIFIED")
    print("note: softmax H/PR enclosure is the sibling Node/eqcert certificate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
