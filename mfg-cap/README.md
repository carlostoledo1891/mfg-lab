# mfg-cap — computer-assisted proofs for a mean-field game

Rigorous, machine-checked enclosures of solutions to the stationary (ergodic)
mean-field game system on the torus:

```
    −σ u'' + ½ (u')² + ρ  =  c·m + V(x)          (HJB)
    −σ m'' − ( m u' )'    =  0                    (Fokker–Planck)
    ∫m = 1,   ∫u = 0,   m > 0
```

Given a numerical candidate, the validation returns either a **refusal** or a
theorem: *there is an exact solution within an explicit distance `r` of the
candidate, it is the only solution in that ball, and the density is positive
there*. Every inequality is evaluated in outward-rounded interval arithmetic,
so it holds for exact real arithmetic and not merely for the floating-point
computation that suggested it.

No libraries, no build step. `make check` runs the whole battery in ~0.2 s.

## What is claimed, precisely

> The first rigorous computer-assisted enclosure of a solution to a mean-field
> game system — including a validated interval for the ergodic constant ρ —
> establishing existence, local uniqueness and density positivity with
> certified error bounds, **and a certified multiplicity result in the
> anti-monotone regime, where uniqueness theory is silent.**

Certified multiplicity is the part that needed the machine. For `c < 0` the
coupling is decreasing, Lasry–Lions uniqueness does not apply, and past
`c* = −σ²(2π)²` a branch bifurcates from the constant state. At `c = −12`,
`σ = 0.5` the constant state and a non-constant solution are each enclosed in
balls of radius `6.8e−15` and `3.4e−13` whose centres are `10.79` apart in the
same norm. **Disjoint enclosures at identical parameters prove there are at
least two distinct solutions** — a statement about the PDE, not about a solver.

## What is NOT claimed

Stated here rather than left for a referee (see `docs/FINDINGS_LIT_CAP.md`):

- **Not "the first CAP for a forward–backward system."** The stationary problem
  has no time, so it has no forward–backward structure. What remains is a 2×2
  adjoint-coupled elliptic system with a density, which is routine territory for
  this machinery (Breden–Payan, Physica D 2024).
- **Not a new existence or uniqueness theorem.** For `c > 0` both are classical
  (Lasry–Lions). The contribution is the enclosure, not the existence.
- **Not novel because the linearisation is non-coercive.** A computer-assisted
  proof never needs a bound on `‖DF⁻¹‖`; it needs an approximate inverse whose
  defect is small, obtained by construction. The finite-block + dominated-tail
  splitting *is* the standard `Z1` computation. See §4 below — the conjecture
  that motivated this project turned out to be mis-posed, and saying so is part
  of the result.
- **The Hopf–Cole reduction is not ours.** It is textbook for MFG (Cirant 2015;
  Cirant–Verzini 2017; Ullmo–Swiecicki–Gobron 2019). It is used here only as an
  independent cross-check, never as the route of proof.
- **Open, and the top item:** every instance certified so far has a quadratic
  Hamiltonian, where a scalar reduction exists. Until a non-quadratic
  Hamiltonian, two populations, or congestion is certified, the *system* method
  has not been shown to do anything the scalar method could not.

## Results (regenerate with `make demo`)

Monotone regime, `V = A·cos 2πx` — existence, local uniqueness, positivity:

| σ | c | A | N | radius r | certified min m | Z1 |
|---|---|---|---|---|---|---|
| 0.5 | 1 | 1 | 16 | 1.17e−15 | 0.909619 | 0.026 |
| 0.3 | 1 | 1 | 16 | 1.98e−15 | 0.790356 | 0.052 |
| 0.3 | 2 | 1.5 | 20 | 4.60e−15 | 0.744503 | 0.064 |
| 1.0 | 0.5 | 0.5 | 12 | 3.89e−16 | 0.987513 | 0.013 |

Anti-monotone regime, `V = 0`, `σ = 0.5` — certified multiplicity:

| c | branch amplitude a₁ | r (branch) | r (constant) | separation | verdict |
|---|---|---|---|---|---|
| −11 | −0.2445 | 3.20e−13 | 6.71e−15 | 6.70 | ≥2 solutions proved |
| −12 | −0.3421 | 3.38e−13 | 6.84e−15 | 10.79 | ≥2 solutions proved |
| −16 | −0.6257 | 1.54e−09 | 1.17e−14 | 27.28 | ≥2 solutions proved |
| −24 | −1.0885 | 1.96e−05 | 1.68e−14 | 70.01 | ≥2 solutions proved |

The radius degrades as the density concentrates (`min m` falls to 4.3e−4 at
`c = −24`); that is reported rather than tuned away. At the bifurcation point
itself the linearisation is singular and **the proof refuses** — as it must.

## Method

Newton–Kantorovich in radii-polynomial form, standard since van den Berg–Lessard.
With `T(x) = x − A Φ(x)` and bounds `‖T(x̄)−x̄‖ ≤ Y0`, `‖DT‖ ≤ Z1 + Z2 r`, a
negative value of `p(r) = ½Z2 r² − (1−Z1) r + Y0` gives a contraction, hence a
unique fixed point. Nothing here is new as machinery; what is new is the
operator it is pointed at.

The one step that makes it close: in `(u, m)` variables the nonlinearity `½(u')²`
costs a derivative and no Banach-algebra estimate works. Taking `p := u'` as the
unknown and dividing Fokker–Planck by `2πk` leaves both equations as *diagonal
linear part `O(k)` plus pure convolution*, with no derivative loss — and in the
weighted `ℓ¹_ν` norm convolution is a Banach algebra, so every quadratic bound
is `‖f*g‖ ≤ ‖f‖‖g‖` rather than a Sobolev embedding with an unevaluated
constant.

## Layout

```
kernel/interval.js   outward-rounded interval arithmetic; the rigor model
kernel/mfg1d.js      the model in Fourier + spectral Newton (floats only)
kernel/validate.js   the proof: Y0, Z1, Z2, radii polynomial, positivity
tests/test-cap.js    20 checks + 6 falsifiers
tools/report.js      regenerates every number quoted above
tools/build-artifact.js  generates mfg-cap.html FROM the kernels
docs/FINDINGS_LIT_CAP.md the literature gate, and what it corrected
docs/THEORY.md       the derivation, the norms, and the hypotheses
```

## On trusting this

The battery is built so that it can fail. Three **independent** witnesses check
the solver — the PDE evaluated pointwise on a fine grid, the Fokker–Planck flux,
and the Gibbs identity `m = e^{−u/σ}/Z` which the solver never uses — because
the first version of this code had a **machine-zero Fourier residual at a point
that did not solve the PDE**: `p = u'` is an *odd* sequence and was being
extended evenly. No residual check could have caught that. Six falsifiers each
mutate one thing and must turn their own target red, including that exact
parity bug.

The interval library is itself validated against exact BigInt rational
arithmetic on 12000 random operations, and removing the outward rounding turns
that check red.

## §4 — the conjecture that motivated this, and its answer

The project began from a conjecture: *monotonicity should supply for MFG the
inverse bound that coercivity supplies for elliptic problems, and that is why
no computer-assisted proof exists in this field.*

Having built it: **the question was mis-posed.** A computation needs neither
coercivity nor monotonicity — which is precisely why this code certifies
solutions in the anti-monotone regime, where the monotonicity theory has
nothing to say. The slot was empty not because of a mathematical obstruction
but because the validated-numerics and mean-field-game communities do not
overlap. That is a smaller and less romantic finding than the conjecture, and
it is the true one.

## License

MIT — see `LICENSE`.
