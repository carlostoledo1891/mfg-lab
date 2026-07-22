# MFG Lab — certificate-first mean-field games

[![verify](https://github.com/carlostoledo1891/mfg-lab/actions/workflows/verify.yml/badge.svg)](https://github.com/carlostoledo1891/mfg-lab/actions/workflows/verify.yml)

A certification toolkit, a computer-assisted proof, two single-file
zero-dependency interactive laboratories, and a validated Python kernel — for
mean-field games and network equilibria in the monotonicity school. Every solve
runs live; every claim ships with a certificate.

**The working thesis: numerical honesty is the product.** Certificates over
tolerances; pre-update residuals only (post-update identities that are
trivially exact are never displayed as certificates); failure modes
deliberately exposed and explained in the language of the theory; every
mathematical claim labeled **[PROVED] / [STANDARD] / [SKETCHED] / [OPEN]**.

## The stack

| | what it is |
|---|---|
| **[`eqcert/`](eqcert/)** | the certification toolkit and the bottom of the stack: one interval library, one exact-rational library, radii-polynomial and Krawczyk operators, and a `Certificate` that **cannot be constructed without a falsifier**. |
| **[`mfg-cap/`](mfg-cap/)** | computer-assisted proofs for a stationary mean-field game — existence, local uniqueness, a validated ergodic constant, density positivity, and **certified multiplicity** where uniqueness theory is silent. |
| **[`mfg-lab/`](mfg-lab/)** · **[`sin-mfg/`](sin-mfg/)** | the two interactive artifacts, below. |
| **[`mfg-lab/python/`](mfg-lab/python/)** | the Python package, held to the shipped JS by cross-language differentials. |

### `eqcert` — the toolkit

Not a solver, and deliberately not a modelling framework. The models it was
extracted from — a finite-difference mean-field game, a spectral one, Wardrop
flows on a network, an exact dynamic program over a scenario tree — share
almost no structure. What they share is the last step: turning a computed
equilibrium into a claim somebody else can check.

One design decision is enforced rather than documented: **a `Certificate`
cannot exist without a falsifier**, and a `PROVED` verdict carrying no evidence
throws. This prevents a failure that is real and invisible — a suite of eight
passing assertions in which three were algebraic tautologies that would have
passed on white noise. `eqcert/tests/test-single-source.js` scans this whole
tree for the *fingerprints* of a reimplementation, because a second copy of a
delicate implementation is created by pasting, not by importing, and a drifted
copy keeps printing PASS while quietly ceasing to be evidence.

### `mfg-cap` — the computer-assisted proof

Rigorous, machine-checked enclosures for the stationary (ergodic) MFG system on
the torus. Given a numerical candidate, the validation returns either a
**refusal** or a theorem: there is an exact solution within an explicit distance
`r` of the candidate, it is the only solution in that ball, and the density is
positive there. Every inequality is evaluated in outward-rounded interval
arithmetic, so it holds for exact real arithmetic and not merely for the
floating-point computation that suggested it.

The page [`mfg-cap/mfg-cap.html`](mfg-cap/mfg-cap.html) is **generated** from
the kernels and gated on byte-identity, so what the browser shows is what the
battery proved. What the literature check killed — three of the four claims that
would have been natural to make — is recorded in
[`mfg-cap/docs/FINDINGS_LIT_CAP.md`](mfg-cap/docs/FINDINGS_LIT_CAP.md), along
with a sign error it caught in our own algebra.

## The two interactive artifacts

Open either file in a browser — no build, no server, no libraries.

**[`mfg-lab/mfg-lab.html`](mfg-lab/mfg-lab.html)** — one page, eight live
experiments, organised as an argument rather than a menu. Every section has its
own address, so a result can be linked directly:

| route | what it carries |
|---|---|
| `#/` | the argument: what is claimed, and what would falsify it |
| `#/wardrop` | multi-population Wardrop — reproduced, certified, **proved** |
| `#/price` | Gomes–Saúde price formation, pre-update clearing residual |
| `#/water-value` | the stock constraint: the water value as a martingale |
| `#/random-supply` | Gomes–Gutiérrez–Ribeiro (2021) §4, pathwise |
| `#/bench` | four probes of the finite-difference kernel |
| `#/certificates` | the standard: what is displayed, and what is refused |
| `#/verification` | the failure log — every time this project was wrong |
| `#/program` | open directions, and the ideas a literature check killed |

The eight experiments:

1. 1D crowd MFG — fictitious play with an exploitability certificate.
2. LQ benchmark vs an RK4 Riccati reference — grid study, observed order.
3. 2D two-exit — crowd aversion (monotone, certified) vs herding
   (anti-monotone; the pitchfork traced by repeated solves, honestly
   uncertified).
4. Stationary crossed monotone flow (Almulla–Ferreira–Gomes),
   proximal-implicit; the explicit toggle stalls by design.
5. Gomes–Saúde price formation in a battery-fleet skin — the pre-update
   clearing residual is the convergence criterion.
6. Gomes–Gutiérrez–Ribeiro (2021) §4 verbatim — common noise, the pathwise
   invariant ϖ+Π+cQ conserved at ~5e-15 along every realization, seed
   displayed and editable (a reproducibility receipt).
7. Multi-population Wardrop equilibrium by Hessian–Riemannian flow
   (Bakaryan–Aoun–Ribeiro–Hovakimyan–Gomes, arXiv:2504.16028) — machine-zero
   KKT certificates, an independent single-population KKT audit of the
   totals, the projected-gradient duel measured honestly, and the S1
   split non-uniqueness demonstrated rather than hidden. Its equilibrium is
   also **proved**, not only certified: exact rational arithmetic for the
   strictly monotone scenario, a verified interval enclosure for the
   nonlinear one, and a refusal to certify the degenerate one
   (`mfg-lab/tests/test-wardrop-interval.js`).
8. The water value on a scenario tree — price formation with a stock
   constraint, solved exactly and certified by LP duality: zero duality gap,
   then the martingale identity read off the certified dual over interior
   nodes only. The kernel is `sin-mfg/tools/water_value_tree.js` embedded
   verbatim, with byte-identity gated by
   `mfg-lab/tests/test-water-value-diff.js` — one kernel, two artifacts.

The Certificates section states the standard, solver-structure matching, and
lineage — every claim checkable against the code in the same file.

**[`sin-mfg/sin-mfg.html`](sin-mfg/sin-mfg.html)** — a living research note:
the Brazilian interconnected system (SIN) as a mean-field game with an
administered price band (the ANEEL PLD floor/cap as a first-class object), a
storage crowd coupled to Hotelling hydro stock, formulated as a monotone
variational inequality. The deterministic water-value theorem is proved and
certified to machine zero in-page; the stochastic version and the
reflecting-boundary duality are stated as open problems, not claimed. All
units stylized — a formulation, not a calibrated Brazil model.

## Validation — `make check`

Every battery extracts the kernel from the artifact at run time (never a
copy that can go stale) and prints the sha256 of the file it validated.
Fixes are mutation-tested: a certificate that cannot go red is not a
certificate.

| battery | target |
|---|---|
| `eqcert/tests/test-eqcert.js` | the toolkit: interval arithmetic against exact rationals, the contraction operators, and the falsifier discipline |
| `eqcert/tests/test-single-source.js` | one interval library and one rational library in the whole tree — with a falsifier proving the scan can see a second copy if one is ever pasted in |
| `mfg-cap/tests/test-cap.js` | the computer-assisted proof: three independent witnesses for the solver, the validated enclosures, and six falsifiers each turning its own target red |
| `mfg-cap/tests/test-artifact.js` | the page is generated, fresh, byte-identical to the kernels and numerically identical to them |
| `mfg-lab/tests/smoke.js` | whole-artifact Proxy-DOM smoke (52 checks incl. routing, prose + design regressions) |
| `mfg-lab/tests/test-wardrop.js` | Wardrop kernel (21 assertions, incl. Table I comparison and the projected-gradient duel) |
| `mfg-lab/tests/test-wardrop-diff.js` | shipped kernel ≡ battery kernel differential |
| `mfg-lab/tests/test-wardrop-interval.js` | the equilibrium **proved**: exact rational (S2), Krawczyk enclosure (S3), required refusal (S1); 15 checks + 5 falsifiers |
| `mfg-lab/tests/test-water-value-diff.js` | one kernel, two artifacts: byte-identity of the embedded water-value tree, plus its certificates |
| `mfg-lab/tests/test-transpose.js` | FP = HJBᵀ certified for the lab's continuum kernel |
| `mfg-lab/tests/test-invariant.js` | GGR's §3.1 balance condition carried pathwise by the scheme (their relation, our certificate), ray unique within the linear ansatz, knife-edge under loading deformation; beyond-LQ first integrals obstructed (Lie-closure rank certificate) |
| `sin-mfg/tests/test-sin.js` | SIN-MFG kernel battery (43 checks; two-layer: math + display path) |
| `sin-mfg/tests/test-transpose-sin.js` | the Achdou adjoint-matched pair for the SIN Hamiltonian, `FP = HJBᵀ` exact |
| `sin-mfg/tests/test-water-value.js` | the water-value LP theorems: piecewise-constant w (deterministic) and martingale-off-binding w (scenario trees), zero-gap LP duality |

`make check-py` adds the Python batteries: the `mfglab` pytest suite (with a
cross-language differential holding Python == the shipped JS kernel) and the
PLD martingale-test selftest. `make check-all` adds headless-browser layout
batteries (real Chromium; run `make venv` first).

## The Python package

[`mfg-lab/python/`](mfg-lab/python/) — two kernels, each held to the shipped
JS by a cross-language differential run at test time with sha256 provenance:

- **Wardrop/HRF** (`mfglab.wardrop`): integrate → active-set Newton polish →
  certificates; agreement with `mfg-lab.html` to < 1e-9.
- **SIN-MFG continuum** (`mfglab.continuum`): the HJB/FP field solve, band
  clearing, hydro dispatch, Picard driver and DP audit, ported
  statement-for-statement; agreement with `sin-mfg.html` at ~1e-16 on the
  equilibrium price path (same iteration count, same certificates). Also
  ships the Achdou adjoint-matched scheme (`solve_field_upwind`,
  FP = HJBᵀ exact — see
  [`sin-mfg/tools/continuum_reference.js`](sin-mfg/tools/continuum_reference.js))
  running to its own certified equilibrium.

## Open problems

The genuinely open mathematics is stated at collaborator precision —
statement, hypotheses, known results, exact gap, candidate routes — in
[`sin-mfg/docs/OPEN_PROBLEMS.md`](sin-mfg/docs/OPEN_PROBLEMS.md). These are
offered as questions; nothing there is presented as nearly-done.

## Documents

- [`sin-mfg/docs/SIN_MFG_Model_Spec_v0.3.md`](sin-mfg/docs/SIN_MFG_Model_Spec_v0.3.md)
  — the model (v0.1 and v0.2 are kept as superseded drafts, corrections
  visible on purpose).
- [`sin-mfg/docs/FINDINGS_SIN.md`](sin-mfg/docs/FINDINGS_SIN.md),
  [`mfg-lab/docs/FINDINGS.md`](mfg-lab/docs/FINDINGS.md),
  [`mfg-lab/docs/FINDINGS_LIT.md`](mfg-lab/docs/FINDINGS_LIT.md) — the defect
  and findings logs: every retraction, every measurement that hurt, kept.
- [`sin-mfg/docs/pld-data-run.md`](sin-mfg/docs/pld-data-run.md) — recipe for
  the hourly-PLD empirical check (public CCEE data; raw CSVs are
  re-downloadable and not redistributed here; the result is exploratory and
  carries an administered-price caveat, stated wherever it appears).

## Requirements

- Node ≥ 18 for `make check` (no npm dependencies).
- Python 3.11+ for the Python batteries: `make venv`, then `make check-py`
  or `make check-all`.

## Citation & license

MIT license (see `LICENSE`). If you use this software or its results, please
cite it — see `CITATION.cff`.

Contact: Carlos Toledo — carlos@carlostoledo.co
