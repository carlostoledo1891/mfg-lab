# FINDINGS_LIT_CAP.md — the literature gate for mfg-cap, and what it changed

Run 2026-07-22, **before any prose**, per the house rule that has now been paid
eight times. The check did not kill the project, but it killed **three of the
four things I would naturally have claimed**, and it corrected an error in my
own algebra. Recording all of it, because the base rate is the useful number.

---

## 0 · What the check corrected before it got to the literature

**The reduced (Hopf–Cole) equation, as I first wrote it, had a sign error.**
I wrote `−2σ²w'' + ρw = (c/Z)w³ + Vw`. The correct reduction is

    −2σ² w'' + V w + (c/Z) w³ = ρ w ,     w = e^{−u/2σ},  Z = ∫w².

**Settled by computation, not by argument** — the battery evaluates both forms
on the same certified solution (`test-cap.js` S5): the stated form holds to
~1e-6 (finite-difference limited), the flipped one fails by O(1). The correct
object is the **mass-normalised Gross–Pitaevskii ground state on the torus**.

Two consequences worth keeping:

- `c > 0` (Lasry–Lions monotone / crowd-averse) ⇔ **defocusing** GP;
  `c < 0` (herding) ⇔ **focusing** GP.
- The flux constant in `−σm' − mu' = C` is **exactly zero** on the torus for a
  general reason, not just for even solutions: divide by `m > 0` and integrate,
  `C·∫(1/m) = 0`. My original argument (`m u'` is odd, so its integral
  vanishes) only covers the symmetric case. The general one is better and is
  what the code's cross-check now rests on.

---

## 1 · Verdicts

| claim I would have made | verdict |
|---|---|
| "first CAP for a **forward–backward** system" | **DEAD.** The stationary problem has no time, hence no forward–backward structure. What remains is a 2×2 adjoint-coupled elliptic system with a density — routine CAP territory (Breden–Payan chemotaxis, Physica D 2024; Breden–Kuehn–Soresina cross-diffusion, JDE 2018). |
| "novel because the linearisation is **non-coercive**" | **DEAD.** The finite-block + Laplacian-dominated-tail splitting *is* the standard `Z1` computation, in every radii-polynomial paper since the method's inception. Framing it as defeating an obstruction reads as re-describing the method. Also: "non-coercive MFG" already means something else in this literature (a non-coercive *Hamiltonian*) — conflating them invites a correction. |
| "a new existence/uniqueness result" | **DEAD** for `c > 0`: existence and uniqueness are classical Lasry–Lions. Certifying a theorem everyone already has is not a contribution. |
| "first CAP for the reduced 1D GP problem" | **WEAK.** Ayala, García-Azpeitia & Lessard, *Computer-Assisted Proofs of Gap Solitons in Bose–Einstein Condensates*, J. Nonlinear Sci. 2026 (arXiv:2503.04701) do radii-polynomial CAP for 1D GP with a periodic potential. Different solution class (homoclinic gap solitons on the line, eigenvalue in a spectral gap) than ours (mass-normalised periodic ground state, `ρ` determined by the constraint) — but one month and one boundary condition away, by the leading group, using the same tooling. |
| the Hopf–Cole reduction itself | **PRE-EMPTED, textbook.** Cirant, C. R. Acad. Sci. 2015 (arXiv:1505.06017); Cirant–Verzini, ESAIM COCV 2017 (arXiv:1511.09343); Ullmo–Swiecicki–Gobron, Phys. Reports 799 (2019) and PRL 116, 128701 (2016), whose stated programme is *literally* "transfer NLS/GP techniques to MFG". Must be cited in the first paragraph; can never be presented as an observation. |

### What came back genuinely empty

- **No computer-assisted / validated-numerics existence proof for any MFG
  system**, stationary or time-dependent, any dimension, under many phrasings.
  A search-based negative, but a robust one. Nearest neighbours stop short:
  **Berry** (arXiv:2511.13352, 2025) has the same Newton–Kantorovich skeleton —
  stability ⇔ invertibility of the linearisation, via Brezzi–Rappaz–Raviart —
  but a priori, non-explicit constants, no interval arithmetic, no enclosure;
  **Osborne–Smears** (arXiv:2502.14687, IMA JNA 2025) give computable a
  posteriori bounds to a solution **assumed to exist**.
- **No validated enclosure of an effective Hamiltonian / ergodic constant.**
  The check called this "the cleanest unclaimed gap in the whole sweep", and
  the constant `ρ` in this system is exactly such an object. Prior work on the
  cell problem is a priori numerical analysis only (Capuzzo-Dolcetta–Falcone
  lineage); the rigorous Aubry–Mather work is dynamical (Figueras–Haro–Luque,
  FoCM 2017), not Hamilton–Jacobi.
- **No CAP for a genuine time-dependent forward–backward control system**
  (backward HJB + forward FP with split boundary data in time). That remains
  open and is the natural sequel.

---

## 2 · The claim this project is allowed to make

> The first rigorous computer-assisted enclosure of a solution to a mean-field
> game system — including a validated interval for the ergodic constant ρ —
> establishing existence, local uniqueness and density positivity with
> certified error bounds, **and a certified multiplicity result in the
> anti-monotone regime, where uniqueness theory is silent.**

The two gating conditions the check attached, and how this repository meets
them:

1. **Do not route the proof through Hopf–Cole.** Met: the validation runs
   directly on the coupled `(ρ, p, b)` system in `ℓ¹_ν`. The reduction is used
   *only* as an independent cross-check on the same instance (battery S3/S5),
   which is a genuinely strong receipt rather than a shortcut.
2. **Exercise the method where the reduction fails.** **NOT YET MET.** Every
   instance certified here has a quadratic Hamiltonian, where the scalar
   reduction exists. Until a non-quadratic Hamiltonian (or two populations, or
   congestion) is certified, the "system" method has not been shown to do
   anything the scalar method could not. This is recorded as the top open item
   in `README.md`, and no claim in this repository depends on it.

---

## 3 · Must-cite

1. **Ayala, García-Azpeitia & Lessard**, CAPs of Gap Solitons in BEC,
   J. Nonlinear Sci. 2026, arXiv:2503.04701 — nearest CAP on the same reduced
   equation.
2. **Cirant**, A generalization of the Hopf–Cole transformation for stationary
   MFG systems, C. R. Acad. Sci. 2015, arXiv:1505.06017 — the reduction.
3. **Cirant & Verzini**, Bifurcation and segregation in quadratic
   two-population MFG systems, ESAIM COCV 2017, arXiv:1511.09343 — the
   bifurcation structure this repository certifies instances of.
4. **Berry**, error estimates for semidiscrete FE approximations of stable
   solutions to MFG systems, arXiv:2511.13352 — stability ⇔ invertibility; the
   closest prior framework.
5. **Breden & Payan**, CAPs for the many steady states of a chemotaxis model
   with local sensing, Physica D 2024, arXiv:2311.13896 — CAP for a coupled
   density system, and the reason the "2×2 system" framing is not novel.

Runners-up a referee will raise: Ullmo–Swiecicki–Gobron (Phys. Rep. 799, 2019);
Osborne–Smears (arXiv:2502.14687); Nakao–Plum–Watanabe (Springer 2019);
Figueras–Haro–Luque (FoCM 2017); Cirant, *Stationary focusing MFG* (CPDE 2016).

**One thing still to verify before submission:** arXiv:2601.19818
("Learn and Verify", PINN verification by interval arithmetic, Jan 2026) —
confirm MFG is not among its examples.

---

## 4 · The O1 conjecture, answered

The conjecture this project was commissioned around asked whether
**monotonicity supplies the inverse bound that coercivity supplies for elliptic
problems**. Having built it, the answer is: **the question was mis-posed, and
that is the finding.**

A computer-assisted proof never needs a bound on `‖DF⁻¹‖` at all. It needs an
approximate inverse `A` whose defect `‖I − A·DF‖` is small, and that is
obtained *by construction* — numerically on the finite block where the coupling
lives, and from the diagonal `σ(2πk)` on the tail, where the coupling is
dominated. Coercivity is what an **analytic** proof needs. A computation needs
neither coercivity nor monotonicity, which is exactly why this repository can
certify solutions in the anti-monotone regime where the monotonicity theory has
nothing to say.

So the slot was not empty because of a mathematical obstruction. It was empty
because the two communities do not overlap. That is a smaller and less
romantic finding than the conjecture, and it is the true one.
