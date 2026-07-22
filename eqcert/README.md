# eqcert — a certification toolkit for equilibrium computations

Not a solver, and deliberately **not a modelling framework**.

The models this was extracted from — a finite-difference mean-field game, a
spectral one, Wardrop flows on a network, an exact dynamic program over a
scenario tree — share almost no structure. Unifying *them* would produce a
lowest-common-denominator abstraction that makes every concrete case harder to
read and harder to verify, and verifiability is the whole product. What they do
share is the last step: turning a computed equilibrium into a claim somebody
else can check. That step is all this package contains.

## The one design decision

**A `Certificate` cannot be constructed without a falsifier.**

```js
const { proved } = require('eqcert').certificate;

proved({ claim: 'the equilibrium lies in this ball', evidence: { r: 1.2e-15 } });
// Error: Certificate: falsifier — a certificate that cannot go red is decoration
```

This is enforced rather than documented because the failure it prevents is real
and invisible: a suite of eight passing assertions in which three were algebraic
tautologies that would have passed on white noise, and one check was doing all
the work. Every certificate here carries the answer to *what input would make
this fail?*, and a `PROVED` verdict additionally requires evidence, a `REFUSED`
verdict requires a reason, and assumptions are printed separately from checked
facts — because "positivity was verified over the enclosure" and "positivity was
assumed" must never render the same way.

## Modules

| module | what it is for |
|---|---|
| `certificate` | the contract above |
| `interval` | outward-rounded interval arithmetic — **bounds** what you cannot compute exactly |
| `rational` | exact BigInt fractions — **decides**, and is the only tool that can resolve a tie |
| `sequence` | weighted ℓ¹_ν algebra with **explicit parity** |
| `radii` | the radii polynomial and the Krawczyk operator, side conditions enforced |

### Why both interval and exact arithmetic

They answer different questions, and picking the wrong one silently weakens a
certificate. Interval arithmetic bounds a genuinely nonlinear quantity. Exact
arithmetic *decides* a sign — and it is the only option when the answer is a
tie, because **no interval method can ever conclude that a quantity is exactly
zero**. That distinction was learned rather than designed: certifying a
multi-population Wardrop equilibrium, an unused edge turned out to carry slack
exactly zero. Intervals returned −1.6e−12 and could not conclude; exact
arithmetic settled it at once.

### Why parity is a required argument

A real even function has `f_{-k} = f_k`; its derivative is **odd**. Storing both
as "the array `f[0..N]`" and extending them the same way yields a Galerkin
system that is not the one you meant — and whose residual is *machine-zero*,
because it solves the wrong system exactly. That bug was live here: a Fourier
residual of 1e−16 at a point whose pointwise PDE residual was 4e−2. So there is
no default parity anywhere in this package.

## Things this package's own battery caught

- The textbook quadratic formula for the radii polynomial's smaller root loses
  all significant digits exactly when the defect `Y0` is tiny — i.e. when the
  numerical solution is *good*, which is nearly always. Fixed with the stable
  form `2·Y0/((1−Z1) + √disc)`.
- Returning the polynomial's root as the radius proves nothing: there `p(r) = 0`
  and the contraction is not strict. The radius is now enlarged until `p(r) < 0`
  is verified **in interval arithmetic**.
- `subset` is not `interior`. Krawczyk needs strict interior containment for
  uniqueness, and accepting `⊆` would claim more than was earned.
- A third copy of the rational arithmetic, hiding in a downstream battery,
  found by `tests/test-single-source.js` within a minute of that gate existing.

## Guarantees about copies

`tests/test-single-source.js` scans the whole working tree for the
*fingerprints* of a reimplementation and fails on any file carrying them that
is not the toolkit or a declared, byte-identical vendored copy. It is a text
scan on purpose: a second copy is created by pasting, not by importing.

## Rigor model

JavaScript cannot set the FPU rounding mode, so directed rounding is simulated:
every IEEE-754 basic operation returns the correctly-rounded nearest double, so
the exact result lies within half an ulp, and widening each bound outward by one
ulp encloses it. Conservative by a factor of about two in the last bit, and
free at the accuracy needed. The library is not trusted on that argument — the
battery checks 16 000 operations against exact rationals across six magnitude
scales, and removing the widening turns it red.

## Use

```bash
make check     # 24 checks + 4 falsifiers, plus the single-source gate
```

No dependencies. Node and browser compatible (CommonJS).

## License

MIT — see `LICENSE`.
