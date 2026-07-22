"""certificate.py — what a certificate IS, made structural. Python twin of
``eqcert/src/certificate.js``.

THE ONE DESIGN DECISION, IDENTICAL IN BOTH LANGUAGES: the constructor REFUSES
to build a certificate without a falsifier. A check whose honest answer to
"what would make this go red?" is "nothing" is decoration, and this repository
has shipped decoration before — eight passing assertions of which three were
algebraic tautologies that would have passed on white noise.

Two further rules are enforced rather than documented:

* a ``PROVED`` verdict must carry evidence; a bare assertion is not a proof;
* ``assumes`` is separated from what was checked, and printed differently.
  "m > 0 was verified over the enclosure" and "m > 0 was assumed" are different
  statements and must never render the same way.

WHY THIS IS A TWIN AND NOT A SECOND IMPLEMENTATION OF THE ARITHMETIC.
``eqcert`` gets a Python twin, and the twin grows BY DEMAND rather than all at
once: this is the slice the Lab needs, and the interval and exact-rational
libraries are deliberately NOT ported,
because nothing in Python needs them yet and an unused second copy of delicate
arithmetic is precisely the drift ``eqcert/tests/test-single-source.js`` exists
to prevent. When something needs them, they arrive with their own differential.

The full rationale lives in the JavaScript sibling; this file carries the rules
rather than restating the essay, so the two cannot drift in prose.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

PROVED = "PROVED"
REFUSED = "REFUSED"
NOT_CHECKED = "NOT_CHECKED"
_VERDICTS = (PROVED, REFUSED, NOT_CHECKED)


def _req(value: Any, what: str) -> Any:
    if value is None:
        raise ValueError(f"Certificate: {what} is required")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"Certificate: {what} must not be empty")
    if isinstance(value, (list, tuple)) and len(value) == 0:
        raise ValueError(f"Certificate: {what} must not be empty")
    return value


def fmt(v: Any) -> str:
    """Render a number the way a certificate should read: no false precision,
    exponential where a fixed point would mislead."""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")):
            return str(f)
        if f == 0:
            return "0"
        a = abs(f)
        if a < 1e-4 or a >= 1e6:
            return f"{f:.3e}"
        return f"{float(f'{f:.10g}'):g}"
    if isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
        return f"[{fmt(v[0])}, {fmt(v[1])}]"  # an interval
    return str(v)


class Certificate:
    """A claim, its evidence, its assumptions, and the input that would sink it.

    Args:
        claim: what is asserted, in words a reader can check.
        verdict: ``PROVED`` | ``REFUSED`` | ``NOT_CHECKED``.
        falsifier: REQUIRED. What input would make this fail. A string or a
            sequence of them.
        evidence: the numbers. Required when the verdict is ``PROVED``.
        assumes: facts taken as hypotheses and NOT checked here.
        provenance: where the code and configuration were, so a reader can find it.
        why: required when the verdict is ``REFUSED``.
    """

    def __init__(
        self,
        claim: str,
        verdict: str,
        falsifier: str | Sequence[str],
        evidence: Mapping[str, Any] | None = None,
        assumes: Iterable[str] | None = None,
        provenance: Mapping[str, Any] | None = None,
        why: str = "",
    ) -> None:
        self.claim = _req(claim, "claim")
        self.verdict = _req(verdict, "verdict")
        if self.verdict not in _VERDICTS:
            raise ValueError(f"Certificate: unknown verdict {self.verdict}")

        # THE RULE THIS MODULE EXISTS FOR.
        falsifier = _req(falsifier, "falsifier — a certificate that cannot go red is decoration")
        self.falsifier: list[str] = [falsifier] if isinstance(falsifier, str) else list(falsifier)
        if not self.falsifier:
            raise ValueError("Certificate: falsifier — a certificate that cannot go red is decoration")

        self.assumes: list[str] = list(assumes or [])
        self.provenance: dict[str, Any] = dict(provenance or {})
        self.evidence: dict[str, Any] = dict(evidence or {})
        self.why = why

        if self.verdict == PROVED and not self.evidence:
            raise ValueError("Certificate: a PROVED verdict must carry evidence")
        if self.verdict == REFUSED and not self.why:
            raise ValueError("Certificate: a REFUSED verdict must say why")

    @property
    def proved(self) -> bool:
        return self.verdict == PROVED

    def line(self) -> str:
        """One line, safe for a status bar. Never says "converged"."""
        if self.verdict == PROVED:
            ev = " · ".join(f"{k} {fmt(v)}" for k, v in self.evidence.items())
            return f"PROVED — {self.claim}" + (f"  [{ev}]" if ev else "")
        if self.verdict == REFUSED:
            return f"NOT PROVED — {self.why} (nothing is claimed)"
        return f"NOT CHECKED — {self.claim}"

    def report(self) -> str:
        """The full text. Assumptions and falsifiers print for PROVED
        certificates too — especially for those, since that is when a reader is
        most likely to stop reading."""
        out = [f"{self.verdict}: {self.claim}"]
        if self.evidence:
            out.append("  evidence")
            out += [f"    {k:<22}{fmt(v)}" for k, v in self.evidence.items()]
        if self.why:
            out.append(f"  reason        {self.why}")
        if self.assumes:
            out.append("  ASSUMED (not checked here)")
            out += [f"    · {a}" for a in self.assumes]
        out.append("  falsified by")
        out += [f"    · {f}" for f in self.falsifier]
        if self.provenance:
            out.append("  provenance")
            out += [f"    {k:<22}{v}" for k, v in self.provenance.items()]
        return "\n".join(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim, "verdict": self.verdict, "evidence": self.evidence,
            "assumes": self.assumes, "falsifier": self.falsifier,
            "provenance": self.provenance, "why": self.why,
        }


def proved(**kw: Any) -> Certificate:
    return Certificate(verdict=PROVED, **kw)


def refused(**kw: Any) -> Certificate:
    return Certificate(verdict=REFUSED, **kw)


def not_checked(**kw: Any) -> Certificate:
    return Certificate(verdict=NOT_CHECKED, **kw)
