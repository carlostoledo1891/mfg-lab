# Literature check of the floor prose (2026-07-20)

## What the literature actually says

Bonnans–Liu–Pfeiffer, *Error estimates of a theta-scheme for second-order MFG*,
ESAIM M2AN 57 (2023) 2493–2528 (arXiv:2212.08128). Key facts:

1. They state plainly: theirs is "the first one, in the context of MFGs, to
   give a precise convergence order for a fully discrete numerical scheme".
   => Sharp convergence RATES for fully-discrete MFG are recent and rare.
      Our lab must not imply a rate is standard/known for OUR scheme.

2. Their main theorem (Thm 2.10):
      ||u_h - u*_h||_inf + ||m_h - m*_h||_{inf,1} <= C h^r,  r in (0,1)
   r is tied to Holder regularity C^{1+r/2,2+r} of the CONTINUOUS solution.
   => The exponent is NOT 1. It is a fractional r<1, and it is regularity-
      dependent, not a universal "O(h+dt)".

3. Crucially, the constant C is only ever asserted to exist and be
   "independent of h and dt". It is NEVER computed. Their consistency errors
   are O(dt h^r), O(dt h^{r+d}), etc. — all with unevaluated constants.
   => THIS IS THE POINT. The literature gives a RATE, never a usable
      absolute floor. So an artifact that PRINTS "floor = h+dt" is inventing
      a constant of 1 where the theory supplies none.

4. Their scheme uses a CENTERED difference for first-order terms and theta in
   (1/2,1) for diffusion, under a CFL dt <= h^2/(2d(1-theta)sigma).
   They explicitly note that upwinding (which OUR kernel uses) has
   "consistency error ... of a lower order" than centered.
   => Our upwind kernel is a DIFFERENT scheme; their r does not transfer.
      We may not quote their rate as ours.

## Verdict on our edit

Our measured statement — eps ~ (h+dt)^1.1 with constant ~5e-9, so the naive
O(h+dt) bound is ~9 orders too large — is CONSISTENT with the literature in
the only sense that matters: the theory delivers rates with unquantified
constants, therefore no absolute floor is derivable from it. Deleting the
fabricated 1e-4 and refusing to print h+dt as a floor is the correct call.

BUT our prose overreaches in two ways and must be tightened:

(a) We wrote "|eps| ~ (h+dt)^1.1". We measured an EMPIRICAL order on ONE
    parameter set over 4 grids (1.11, 1.16, 1.26 — drifting upward, not a
    settled asymptotic order). The literature's exponent for a related
    (centered, non-upwind) scheme is a fractional r<1 tied to solution
    regularity. Claiming ~1.1 as if it were an order is stronger than our
    evidence and stronger than theory supports for an upwind scheme.
    FIX: report it as an observed empirical slope over the tested range,
    not an order; note the drift; state it is scheme- and problem-specific.

(b) eps is a DIFFERENT object from ||u_h-u*_h||. Their theorem bounds the
    distance to the CONTINUOUS solution. Our eps measures exploitability of
    the DISCRETE fixed point — a residual-type quantity within the discrete
    game. These are not the same error and should not be conflated. Our
    grid-refinement of eps is a self-consistency probe, NOT a convergence
    rate to the continuous MFG.
    FIX: say so explicitly.
# Paper verification of Tab 07 claims vs arXiv:2504.16028v1 (fetched 2026-07-20)

| Artifact claim | Paper says | Verdict |
|---|---|---|
| 15 directed edges, 10 nodes | Table I lists 15 edges; nodes 1..10 | OK |
| entrances node 1 (pop1) and node 9 (pop2) | "population 1 enters exclusively at node 1, population 2 at node 9" | OK |
| exits 8, 10 | exit edges (7,8),(7,10) | OK |
| S1 cost c = j1+j2, inflow 100/100 | "c_k = j_k^1 + j_k^2"; B0 inflow 100 at nodes 1 and 9 | OK |
| S2 cost 0.5(j1+wT j2)+0.5 j^r, wT=2 | "c_k^r = 0.5(j_k^1 + 2 j_k^2) + 0.5 j_k^r" | OK |
| S2: 50 trucks from node 9, 100 cars from node 1 | "only 50 trucks enter from node 9, while 100 cars enter from node 1" | OK |
| S2 uniqueness = "Thm 4 live" | Thm 4: strict monotonicity => at most one Wardrop equilibrium; paper says S2 cost "satisfies the strict monotonicity conditions required by Theorem 4, resulting in a unique equilibrium" | OK |
| S1 non-uniqueness: c=j1+j2 monotone NOT strictly | Paper only claims strict monotonicity for S2, not S1 | OK - consistent |
| interior point >30 min vs HRF <1 s | "the conventional solver needed more than 30 minutes"; multi-pop "converged in less than 0.2 seconds" | OK |
| S3 Fig 3a edge lengths ILLUSTRATIVE (disclosed) | Fig 3a lengths appear only in the figure, not in the text; params given are t_k=50/s_k, beta=3, alpha=5, kappa=50 | OK - disclosure correct and necessary |
| S3 emission table, trucks 3x | Table II params; "e^2 = 3 e^1"; trucks twice congestion impact | OK |
| speed v=50/(1+5(j/50)^3) | v_k = (s_k/t_k)(1+alpha(j/kappa)^beta)^-1 with t_k=50/s_k => s_k/t_k=50, alpha=5, kappa=50, beta=3 | OK - algebra checks |

## NEW FINDING (worth telling Ribeiro)

Paper Table I is INTERNALLY INCONSISTENT on exactly one edge:
  edge (4,7): Flow1 = 39, Flow2 = 13  =>  F1+F2 = 52
              but the published "Total Flow" row says 54.
Our solver's total on (4,7) is 52 — i.e. it equals the SUM of their two
components (39+13) and disagrees only with their printed Total row. Every other
edge has F1+F2 == Total. (Our per-population split there need not equal theirs:
S1's cost is monotone but not strictly, so only totals are unique.)

RE-VERIFIED against the CURRENT arXiv link (Carlos, 2026-07-20): the (4,7) Total
still reads 54 in the live version, not only v1 — the row was not corrected by a
later revision. Solver re-run same date: total on (4,7) = 52.43 → 52. The
observation is safe to send.

Our two other deviations are genuine 1-unit rounding differences:
  (5,6) paper 10 / ours 9 ; (3,7) paper 76 / ours 77.
Max deviation 2 occurs ONLY on the internally inconsistent edge (4,7).

Kirchhoff sanity on their totals: (7,8)+(7,10) = 200 = total inflow. OK.

=> The battery's "max dev <= 2" threshold is correct but the STORY is better
   than "within their rounding": on the single edge driving the max deviation,
   the paper's own two components sum to our number. This is a precise,
   checkable, non-hostile observation — good outreach material, and exactly
   the kind of thing the certificate discipline is supposed to surface.
   It must be phrased as a rounding/typesetting artifact, NOT as "their table
   is wrong" (house rule).
# Floor study — measured, not asserted (session 2026-07-19/20)

## Method
M1 kernel extracted brace-balanced from mfg-lab.html into `kernel_param.js`
(grid parameterized). VALIDATED against in-page values before use:
  extracted @120x240 -> iter 153, eps 7.382e-11, mass 5.251e-14
  in-page reference  -> iter 153, eps 7.38e-11,  mass 5.25e-14   (exact match)

## Result 1 — eps IS first-order in the grid, but with a tiny constant
grid refinement (converged, res~1e-6):
  30x60   h+dt 5.11e-2  |eps| 3.64e-10
  60x120  h+dt 2.53e-2  |eps| 1.66e-10
  120x240 h+dt 1.26e-2  |eps| 7.38e-11
  240x480 h+dt 6.27e-3  |eps| 3.07e-11
observed order in (h+dt): 1.11, 1.16, 1.26  -> first order CONFIRMED.
BUT |eps|/(h+dt) ~ 5e-9, i.e. the naive bound "floor = h+dt = 1.26e-2"
is ~9 ORDERS above the actual eps. Printing it would declare a genuinely
converged eps=7.4e-11 "below the floor / meaningless". VACUOUS BOUND.

## Result 2 — eps is ITERATION-limited, not grid-limited
fixed 120x240, varying iteration budget:
  res 3.03e-3 -> eps 2.40e-7
  res 1.52e-4 -> eps 1.62e-8
  res 8.32e-6 -> eps 7.14e-10
  res 9.95e-7 -> eps 7.38e-11
power-law exponent eps~res^p: 0.90, 1.08, 1.07  -> LINEAR in the residual.
eps saturates exactly when the residual saturates (153 iters); more budget
changes nothing. The residual is eps's honest companion number.

## Result 3 — the proportionality constant is NOT universal
51 converged corners (sigma x c x gamma x congestion, 60x120):
  C = |eps|/res  ranges 9.0e-7 .. 2.2e-3  = 2400x spread.
=> No single calibrated constant is defensible. We must NOT invent one.

## Result 4 — the hardcoded 1e-4 gate
`const small=Math.abs(S.eps)<1e-4` (2D herding branch) is a magic number
disconnected from the grid. Prose asserts "consistency floor ~ 1e-4" while
the 2D grid (NG=48,NT=96) gives h+dt=3.17e-2 (317x larger).
Stalled-regime probe (1D analogue, beta sweep):
  beta 0.20: res 3.53e-1, eps 2.65e-1, ratio 0.75  <- genuinely stalled
  beta 0.55: res 9.80e-7, eps 4.92e-11, ratio 5e-5 <- genuinely converged
The 1e-4 gate separates these only by luck. The DEFENSIBLE discriminator
is the residual (already computed, already displayed), not a fabricated
absolute floor on eps.

## CONCLUSION — plan revised
DO NOT print "floor = O(h+dt)". It is vacuous (9 orders too large) and
would weaken the certificate.
DO: (a) delete the fabricated 1e-4 literal and the stale "~1e-4" prose;
    (b) gate the "orbits an equilibrium" claim on the RESIDUAL, which is
        what actually limits eps;
    (c) state eps's measured first-order grid behaviour in the Method tab
        as a refinement study (real, reproducible), not as a bound.

## Result 5 — the harness was validating a stale file (process bug, found late)
`smoke.js` hardcoded `readFileSync('/home/claude/mfg/script.js')` — a path from
an earlier session's scratch dir, NOT derived from the artifact under test.
Every "23/23 green" run after the edits was reading an UNPATCHED script.
The failures I first blamed on my own new checks were the harness reporting on
the wrong file; the checks were right all along.
FIX: smoke.js now extracts <script> from the HTML at run time
(`MFG_HTML` env override for mutation testing) and prints the path + byte count
on every run. A hardcoded-path harness can silently certify the wrong artifact —
this is the same species of error as a fake certificate, and it is now
structurally impossible.

## Result 6 — mutation testing (new house practice)
A green suite proves nothing unless it can go red. Deliberately reverted each
fix and re-ran:
  mutant1 (eps gate back to 1e-4 literal)      -> 27/29  CAUGHT
  mutant2 (mass back to terminal-row, v1)      -> 28/29  CAUGHT (after strengthening)
  mutant3 (mass terminal-row, row spoofed NT)  -> 28/29  CAUGHT (after strengthening)
  true artifact                                 -> 29/29
First version of the mass check did NOT catch mutant2/3: at rest the terminal
row IS the max, so both implementations print 5.25e-14 and are indistinguishable.
Measured that the rows diverge MID-ITERATION (19 of 400 frames), so the check
now samples across 400 frames and requires both agreement at every frame AND
at least one off-terminal max. Magnitude checks are weak; semantic checks bite.

## Old vs new — 22 displayed certificates compared under identical stubs
21 identical, 1 changed. No math was touched and the numbers prove it.
The single change is a RETRACTION: the 2D herding verdict no longer claims
"orbits a genuine equilibrium" at a 4.27e-2 residual.
The artifact now claims less and proves more.

## NOVELTY AUDIT — ϖ+Π+cQ IS the paper's balance condition (2026-07-21, later)

**Read the source before claiming an invariant.** Prompted by an adversarial
review asking whether the identity was already in GGR, the paper was checked
line-by-line (arXiv:2003.01945, Math. in Engineering 3(4), 2021). It is —
explicitly, as an equation, in **§3.1**:

> "The balance condition is Q_t = − (1/c)(ϖ_t + Π_t)."

That is `ϖ_t + Π_t + c·Q_t = 0`, **for all t**. Consequences, each checked:

1. **The combination is not ours.** It is the paper's market-clearing condition,
   stated as an identity in time. The ray (1,1,c) is not a discovery; it is the
   coefficient vector of an equation GGR writes down.
2. **The conserved value is 0, not an arbitrary constant** — the identity holds
   at the level 0 because clearing holds exactly.
3. **The battery seeds it that way.** `test-invariant.js` initializes
   `Π₀ = −c·Q̄ − w̄`, i.e. from the balance condition at t = 0 (which is how the
   paper itself derives the initial price, eq. (3.7)). So with c₁ = 1,
   `inv0 = w̄ + (−cQ̄ − w̄) + cQ̄ ≡ 0` — identically, by algebra, before any
   dynamics run.

**What survives, and it is worth keeping.** The scheme propagates the clearing
constraint pathwise with drift ~5e-15 under Euler–Maruyama, and it breaks at
O(ε) when the price loading is deformed. That is a genuine numerical
certificate: *our discretization respects the model's clearing condition along
every noise realization.* It is a statement about the
solver, not a new conservation law.

**What must not be claimed:** that the invariant is a previously unremarked
conservation law, that we discovered or "derived, not guessed" the combination,
or that it is "a small extra". To a GGR co-author, all three describe their own
§3.1. The [OPEN] Lie-closure result beyond LQ is unaffected — that is about
whether an analogous first integral survives non-LQ closure, which the paper
does not address.

## The GGR §4 invariant: uniqueness within the linear ansatz, and the obstruction beyond LQ (2026-07-21)

**Superseded in part by the novelty audit above — read it first.** What follows
characterizes the ray; it does not establish novelty, because the relation is
the paper's balance condition.
Battery: `mfg-lab/tests/test-invariant.js` (in `make check`; extracts the MGG
kernel from the artifact, sha-printed; every gate mutation-tested).

**1. The ray is unique within the linear ansatz. [PROVED — elementary]**
Write the ansatz I = c₀ϖ + c₁Π + c₂Q and demand pathwise dI ≡ 0 along the
Euler–Maruyama system. Drift cancellation forces c₂ = C·c₀ (the price drift is
−C × the supply drift, from clearing). Diffusion cancellation, after
substituting the clearing loading load = (C+a₂²)/(1+a₂³), reduces to

  (c₁ − c₀) · (a₂²(t) − C·a₂³(t)) = 0   for all t,

so the ray is unique up to scale — (1, 1, C) — wherever the margin a₂²−C·a₂³
is nonzero (measured min 1.59e-1 on [0, 0.9T]; it vanishes only at t = T,
where the terminal conditions collapse both coefficients and uniqueness
honestly degenerates). The uniqueness is **within the stated ansatz class**:
constant-coefficient linear functionals of (ϖ, Π, Q). It says nothing about
nonlinear, time-dependent, or path-functional first integrals.

**The battery does not derive this, and an earlier version of this file said it
did.** [RETRACTED 2026-07-21] The old text claimed the battery "derives c₁ by
least squares on the coefficient flow … never assuming the paper's
combination". Both halves were false:

- The least-squares step is `c₁ = Σ(A·b)/Σ(A²)` with `A = a₂²−a₂³·load` and
  `b = load−C`. But `A ≡ b` **algebraically** — both equal
  (a₂²−C·a₂³)/(1+a₂³) — so it computes Σ(A²)/Σ(A²) = 1. It returns 1 for white
  noise. Verified: 100k random (a₂², a₂³, C) triples with no ODE anywhere agree
  to 1.78e-15. A check that cannot fail is not a check.
- It *does* assume the paper's combination: c₀ = 1 and c₂ = C are imposed, not
  solved, and Π₀ is initialized from the balance condition (see the novelty
  audit above).

The derivation above is symbolic and stands on its own. The battery's job is
**verification**: conservation pathwise (5.3e-15), the wrong ray c₁ = 1.5
drifting at 3.1e-1 (U7 — the check that was doing the real work all along), and
the ε-sensitivity. Reported as such.

**2. Conservation is ε-sensitive. [PROVED — and it is ALGEBRA, not clearing-forcedness]**

   Superseded framing: this entry previously read "forced by clearing, not
   generic". The drift is now derived exactly: `dI^ε = −ε(C+a₂²(t))s_S(t)dW`,
   for every ε, verified pathwise to 4.7e-13. Being exactly LINEAR in ε with a
   coefficient independent of the deformation mechanism, it is an algebraic
   consequence of rescaling one diffusion coefficient — it does not establish
   that clearing forces conservation (ADVERSARIAL_REVIEWS P1-2). What it does
   give, and is stronger than the old claim: the deformed invariant is a
   MARTINGALE with `Var[I^ε(T)−I(0)] = ε²·E∫(C+a₂²)²s_S²dt`.
Perturb the price's volatility loading by (1+ε): conservation breaks at O(ε)
(drift 1.1e-2 at ε = 0.01, twelve orders above the conserved case). The wrong
ray (c₁ = 1.5) drifts at 3.1e-1: uniqueness is observable, not assumed.

**3. Beyond the LQ structure, NO first integral survives — of any C¹ form.
[PROVED for the loading-deformation class]** Deform the loading
state-dependently, L(t,Q) = load(t)·(1+εQ) — a minimal stand-in for
non-unit-elastic clearing. On the state (t, Q, ϖ, Π), the drift field
X_d = ∂_t + (1−Q)∂_Q − C(1−Q)∂_ϖ and diffusion field
X_σ = sQ(∂_Q − L∂_ϖ + M∂_Π), M = a₂² − a₂³L, generate the Lie brackets
C1 = [X_d, X_σ] and C2 = [X_σ, C1] (closed forms; only first time-derivatives
of the coefficients appear, supplied exactly by the a-ODEs' own right-hand
sides — no finite differences). Any pathwise-conserved F must satisfy
X_dF = X_σF = C1F = C2F = 0; if the four fields span the tangent space, dF = 0
and F is locally constant. Measured determinant of the closure (relative,
det/scale³): **≤ 1.7e-17 at ε = 0 at every sample point** — the
rank-deficiency IS the invariant's existence, and the co-kernel is exactly
dI = (C, 1, 1) — versus **≥ 1.6e-3 at ε = 0.2 and 6.3e-4 at ε = 0.02** on the
same points: full rank on an open set, hence no invariant, linear or not.

Honest scope: the no-go is for this deformation family and this state vector.
A different lift — augmenting the state so the deformed system becomes
integrable again — is not excluded; whether some augmentation restores a
conservation law, and what the right statement is at the measure-valued /
master-equation level, is the genuinely open remainder. What LQ linearity
buys is now precise: rank-deficiency of the drift/diffusion Lie closure, with
the invariant as its co-kernel.

---

## Conservation-law literature check (2026-07-21) — the field is occupied

Run before writing anything about first integrals in MFG. Verdicts blunt.

### The prior art that MUST be cited, ranked by how bad missing it would be

1. **Gomes, Nurbekyan & Sedjro, _Conservation laws arising in the study of
   forward-forward Mean-Field Games_** (arXiv:1704.07209). **Gomes has his own
   paper on conservation laws in MFG.** Writing to him about conservation laws
   in MFG without citing it is socially fatal, not merely sloppy. (Their
   "conservation law" means a hyperbolic PDE, not a conserved quantity — which
   is exactly why the distinction has to be drawn explicitly rather than
   ignored.) Related: Gomes et al., *One-dimensional forward-forward mean-field
   games* (arXiv:1606.09064), Riemann invariants.
2. **Kozlov, _Conservation laws of mean field games equations_**
   (arXiv:2305.06871, 2023) and *…with time discounting* (Commun. Nonlinear
   Sci. Numer. Simul. **152** (2026) 109157). Noether's theorem on the
   HJB+Kolmogorov variational structure. **This is the owner of the topic
   name.** No common noise, no price formation, no non-existence results — so
   the gap is real, but the vocabulary is taken.
3. **Huang, Li, Shi & Xu, _Local first integrals for stochastic differential
   equations_** (arXiv:2403.09074, Mar 2024). A **stochastic Poincaré
   non-integrability theorem**: for integrable ODEs satisfying nondegeneracy,
   there exist linear stochastic perturbations under which the SDE has no
   analytic first integrals at all. **The general version of what our
   deformation gestures at, published.**
4. Sussmann, *Orbits of families of vector fields…* (Trans. AMS **180** (1973));
   Olver, *Applications of Lie Groups to Differential Equations* Ch. 1 — the
   orbit/rank ↔ first-integral count. Hörmander's condition, Stroock–Varadhan
   support, for the stochastic reading.

**Gomes and Ribeiro have written nothing on invariants of their own price
models** — verified against arXiv:2003.01945 and arXiv:2109.01478, where the
words *invariant*, *conserved quantity* and *first integral* do not appear.
And §3.1 of arXiv:2003.01945 is confirmed verbatim at source: "The balance
condition is Q_t = −1/c (ϖ_t + Π_t)". The LQ relation is the model's own
market-clearing equation. Fourth pre-emption by the identical mechanism.

### The error this check caught in our own battery

`test-invariant.js` L2 previously read *"no C¹ first integral of any form
survives"*. **That is false as phrased.** A single vector field always admits
n−1 independent local first integrals near a non-equilibrium point (flow-box /
straightening theorem), so full rank is impossible for one flow and the
implication cannot hold. The argument is only valid for a **family**, and ours
is one — drift `X_d` and diffusion `X_σ`. For an Itô SDE, `I` is a first
integral iff `D₀(I)=0` **and** `D_α(I)=0` for every diffusion component, so the
correct statement concerns functions annihilated by **both** fields, with full
bracket rank being Hörmander's condition. Corrected in the battery; the chain
is standard and is cited, not claimed.

Also corrected: **openness needs one point, not a sample.** `det` is
continuous, so a single nonzero evaluation gives an open neighbourhood.
Reporting a min over four samples was reporting a number where a one-line
argument was available. And the coefficients are ODE-solved, so this is an
exact expression on numerical inputs — **not** a symbolic proof. A referee
would ask for the symbolic determinant; it is unavailable only because the
coefficients are numerical, and that is now stated rather than papered over.

### Banned vocabulary, and why

**"no-go", "non-integrable", "KAM-adjacent"** — each summons a specific
reviewer objection this computation cannot answer. *Non-integrable* invites
Morales-Ramis / differential Galois theory, which concerns meromorphic
integrability of complex Hamiltonian systems and is silent on C¹ integrals —
safe only while the claim stays "no common C¹ first integral of the drift +
diffusion family", fatal the moment it generalises. *KAM* is persistence of
invariant tori, not of first integrals; using it is a terminology error a
referee will flag. The correct lineage for the ε-result is **non-persistence
of first integrals under perturbation** — Poincaré (1892), Melnikov — not KAM.

### The strongest honest framing

The ε-differential is the headline and the Lie-rank observation is a labelled
numerical remark, not the other way round. `dI^ε = −ε(C+a₂²)s_S dW` is exact,
hand-checkable, and is precisely the one-line failure of the standard
first-integral test `D_α(I)=0`. It kills *that* candidate invariant, which is a
smaller claim than the rank computation attempts and the one that survives
review.
