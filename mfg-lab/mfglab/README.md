# mfglab

Certified kernels for mean-field games and network equilibria in the
monotonicity school. **Numerical honesty is the product**: every solve returns
its certificates, and the Python is held to the in-page JavaScript by a
cross-language differential test.

## v0.1 — multi-population Wardrop by Hessian–Riemannian Flow

Port of the Tab 07 kernel (Bakaryan–Aoun–Ribeiro–Hovakimyan–Gomes,
[arXiv:2504.16028](https://arxiv.org/abs/2504.16028)). It was chosen first
because it was already headless JavaScript with assertions, and because it
proves the certificate standard is **formulation-neutral** — a network
variational inequality, not just a PDE.

```python
import mfglab

r = mfglab.solve_scenario(1, wT=2, Q1=100, Q2=100)   # S1, paper Table I
print(r["gap"], r["kirch"], r["totals"])
# relative Wardrop gap ~1e-16, Kirchhoff ~1e-14, totals match Table I to rounding
```

`solve_scenario` runs the HRF replicator flow (RK4 under a merit rule) to a small
Wardrop gap, then an active-set Newton polish that lands the certificates at
machine zero. Certificates returned: relative Wardrop gap (complementarity via
Bellman potentials), Kirchhoff residual, positivity, and — for S1 — an
independent single-population KKT check on the total flows.

## Tests

```
pytest                       # certificate battery, mirrors test-wardrop.js
pytest tests/test_crosslang.py   # Python vs shipped JS agree to ~1e-9 on totals
```

The cross-language test extracts the MWD kernel from `mfg-lab.html`, solves each
scenario in Node, and asserts the Python totals match to `1e-9` — so the two
implementations cannot silently drift. Chain: Python ↔ shipped JS ↔ dev battery
↔ paper Table I.

## Roadmap

The FD-monotone kernel (the continuum tabs 01/02/04/05 and the SIN-MFG note)
ports next; its battery `test-sin.js` becomes the pytest suite the same way.

## v0.2 — the SIN-MFG continuum kernel

`mfglab.continuum`: the coupled HJB/Fokker–Planck field solve, band-clearing
case analysis, hydro dispatch (water-value bisection, spill and cap-mixed
regimes), damped Picard driver, and the independent DP exploitability audit —
ported statement-for-statement from `sin-mfg/sin-mfg.html`.
`tests/test_crosslang_continuum.py` extracts and runs the shipped artifact at
test time and holds the Python against it at ~1e-16 on the equilibrium price
path (same iteration count, same certificates). A second solver,
`solve_field_upwind`, implements the Achdou adjoint-matched pair for the same
Hamiltonian (FP = HJBᵀ exactly, positivity by M-matrix, mass conservation as
an adjoint identity) and reaches its own certified equilibrium — its numbers
differ from the shipped scheme's by construction (numerical diffusion), and
both are always reported with their scheme label.

```python
from mfglab import continuum as C

r = C.picard()                     # the shipped scheme's equilibrium
print(r["disp"]["w"], C.mass_drift(r["field"]), C.clearing_worst(r))

r2 = C.picard(field_solver=C.solve_field_upwind)   # adjoint-matched scheme
print(C.transpose_defect(r2["field"]["u"][0], r2["price"][0]))  # 0.0 exactly
```
