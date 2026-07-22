# SIN-MFG: A Major–Minor Mean Field Game for a Hydro-Dominated Power System with Cobb–Douglas Demand

## Mathematical Specification v0.1 — working document for pressure-testing

> Scope note. This specifies the *model*: state spaces, dynamics, objectives,
> the equilibrium concept, the coupled PDE/FBSDE system, theorem targets, and
> the calibration map to Brazilian data. Proofs are targets, not claims.
> Notation follows Gomes–Saúde (Dyn. Games Appl. 2021) and
> Gomes–Gutierrez–Ribeiro (Math. Eng. 2021 / SIAM J. Fin. Math. 2023),
> abbreviated GS and GGR.

---

## 1. Primitives and notation

Time horizon t ∈ [0,T] (one day to one week for the operational model; the
seasonal model reuses the same structure at monthly resolution). All
processes live on a filtered space carrying:

- **W_t** — idiosyncratic Brownian motions (one per agent, i.i.d.);
- **B_t = (B^I_t, B^S_t)** — the **common noise**: inflow shocks and
  variable-renewable (VRE) shocks. Everything aggregate is adapted to
  F^B_t; this is the conditional-McKean–Vlasov setting of GGR.

Exogenous aggregate processes (calibrated, §8):

- Inflow (ENA): dI_t = θ_I(Ī(t) − I_t)dt + σ_I dB^I_t, Ī(t) seasonal.
- VRE generation: dS_t = θ_S(S̄(t) − S_t)dt + σ_S(t) dB^S_t, S̄(t) the
  solar/wind daily profile (this is GGR's random supply Q_t, verbatim).
- Inflexible load L_t: deterministic profile (extension: own noise).

---

## 2. The minor agents (the mean field)

A continuum of small actors — households/firms entering the free market
under Lei 15.269, distributed batteries, prosumers. Each agent carries:

**State.** Storage level x_t ∈ [0, x̄] (battery SoC; x̄ = 0 for pure
consumers), with

  dx_t = α_t dt + σ dW_t,  reflecting at {0, x̄}.

σ > 0 is a small regularization (GS/GGR practice); reflection models the
SoC bounds. *Disclosed approximation:* reflecting dynamics are not state
constraints (same caveat, same wording as the lab).

**Controls.** α_t ∈ ℝ — charge (α>0) / discharge (α<0) rate;
c_t > 0 — consumption of energy services.

**Preferences — the Cobb–Douglas move.** Quasi-linear flow utility

  u_flow(c, α; ϖ, t) = a(t) log c − ϖ_t·(c + α) − ½η α²,

where ϖ_t is the market price, a(t) > 0 the preference weight (the CD
expenditure share, carrying the daily rhythm: a(t) peaks in the evening),
and ½η α² the storage throughput/degradation cost (GS's quadratic trading
cost). Terminal condition Ψ(x) = −κ(x − x*)² (storage target; GGR's
terminal cost) or a salvage value.

Log utility is the Cobb–Douglas workhorse: with u = a log c the first-order
condition a/c = ϖ gives

  **c*_t = a(t)/ϖ_t** ,  expenditure ϖ_t c*_t = a(t).

Three consequences do real work downstream:
(i) closed-form, iso-elastic demand (elasticity −1; the empirically
motivated generalization c* = (a/ϖ)^{1/(1+ε)} from CES utility is a drop-in,
kept as a remark);
(ii) **constant expenditure shares** — aggregation over heterogeneous
agents needs only ā(t) = ∫ a dμ(a), because demand is additive in a;
(iii) **ϖ_t > 0 automatically** — demand blows up as ϖ↓0, so the clearing
price is interior without side conditions. In GS/GGR (linear demand) prices
can cross zero; CD demand removes that pathology structurally.

**Agent problem.** Given the (F^B-adapted) price process ϖ:

  sup_{α,c} E[ ∫_0^T e^{−ρt}( a(t)log c_t − ϖ_t(c_t + α_t) − ½η α_t² )dt
               + Ψ(x_T) ].

The problem **separates**: consumption is the static CD choice above;
storage is exactly the GS/GGR control problem. The storage value function
u(x,t) (conditional on the common noise) solves

  (HJB)  −∂_t u − ½σ² ∂_xx u + (1/2η)(∂_x u + ϖ_t)² = 0,
         u(x,T) = Ψ(x),  ∂_x u = 0 at x ∈ {0, x̄},

with optimal control α*(x,t) = −(∂_x u + ϖ_t)/η. The population density
m(x,t) (conditional on the common noise) solves the transposed
Fokker–Planck equation

  (FP)   ∂_t m − ½σ² ∂_xx m − (1/η)∂_x( m(∂_x u + ϖ_t) ) = 0,
         m(·,0) = m_0,  zero-flux at {0, x̄}.

Aggregates that enter clearing:

  X_t = ∫ x m(x,t)dx  (fleet SoC),
  A_t = ∫ α*(x,t) m(x,t)dx = −(1/η)( ∫∂_x u·m dx + ϖ_t )  (net fleet flow),

using ∫m = 1. Note A_t is affine in ϖ_t with slope −1/η — the fleet is a
price-responsive resource with explicit sensitivity.

---

## 3. The major player: the hydro system as a benevolent planner

**Design choice, stated openly.** In the Carmona–Zhu / Huang major–minor
tradition the major player is selfish. Brazil's tight pool is not: hydro is
dispatched by ONS at system cost. We therefore take the major player to be
a **welfare-maximizing planner controlling the hydro resource** — formally
a principal–mean-field (Stackelberg) structure rather than a competitive
major. The profit-maximizing hydro variant (relevant to the price-bid vs
cost-based reform debate) is Model B, §10.

**State.** Aggregate reservoir R_t ∈ [0, R̄]:

  dR_t = (I_t − h_t) dt − dU_t,

h_t ∈ [0, h̄] hydro generation (turbined outflow in energy units), U_t the
spill process at R̄. (Aggregate-reservoir representation; cascades are out
of scope, §11.)

**Thermal fleet.** Convex increasing cost C_th(q), q ∈ [0, q̄]; supply
correspondence q*(ϖ) = (C_th′)^{−1}(ϖ) (from the CCEE CVU merit order, §8).
Deficit backstop at cost ϖ^def (the price cap).

**Planner objective.** Maximize expected welfare

  J = E[ ∫_0^T e^{−ρt}( ∫ a log c dμ − C_th(q_t) − ϖ^def d_t ) dt
         + V_T(R_T) ],

subject to the balance constraint (§4), where d_t is unserved energy and
V_T the terminal water value (the seam to the seasonal model: V_T is
NEWAVE's future-cost function in miniature).

**Water value.** The planner's value function V(R, I, S, ·, t) defines

  w_t := −∂_R V  (the marginal value of stored water).

Optimal hydro dispatch has the classical bang–interior structure: h_t = 0
if ϖ_t < w_t, h_t = h̄ if ϖ_t > w_t, and **ϖ_t = w_t on interior dispatch**
— hydro offers at its water value. The novelty is not this rule (it is
SDDP's economics) but that V is computed **against the equilibrium response
of the mean field**: the planner's HJB contains m through the clearing
price, so w_t anticipates how the fleet and CD demand react to the price
that w_t itself induces. That feedback loop is the object of study.

---

## 4. Market clearing and the equilibrium concept

**Balance (per unit time, conditional on the common noise):**

  (CLEAR)  ā(t)/ϖ_t + L_t + A_t(ϖ_t) + d_t·0 = h_t + q*(ϖ_t) + S_t + d_t,

i.e. CD consumption + inflexible load + fleet charging = hydro + thermal +
VRE + unserved energy. Substituting A_t = Ā_t − ϖ_t/η (with
Ā_t = −(1/η)∫∂_x u m dx), the **excess-demand map**

  Φ_t(ϖ) = ā(t)/ϖ − ϖ/η − q*(ϖ) + (L_t + Ā_t − h_t − S_t)

is **strictly decreasing on ϖ ∈ (0, ∞)**, with Φ→+∞ as ϖ↓0 and Φ→−∞ as
ϖ↑∞: the clearing price exists, is unique, and is interior — for *any*
state of the system. (This is the structural payoff of CD demand; in GS the
analogous map is affine.) Numerically, Φ is a scalar monotone root-find
per time slice, and the **pre-update clearing residual |Φ_t(ϖ_t)| is the
convergence certificate**, exactly as in Tab 05.

**Definition (SIN-MFG equilibrium).** A tuple (u, m, ϖ, h, V) adapted to
the common noise such that: (i) u solves (HJB) given ϖ; (ii) m solves (FP)
given u, ϖ; (iii) ϖ_t clears (CLEAR) at every t given (m, h, S, I);
(iv) h is the planner's optimal control for V given the field's response
map; (v) V solves the planner's HJB (§5). Conditional on B, this is a
McKean–Vlasov fixed point in the GGR sense with an embedded Stackelberg
layer.

---

## 5. The coupled system

### 5.1 Deterministic benchmark (σ_I = σ_S = 0)

Writing the planner's HJB with sufficient statistics (R; and the field
entering through the clearing functional):

  −∂_t V − (I(t) − h*)∂_R V = e^{−ρt}[ ā log(ā/ϖ) − ā − C_th(q*(ϖ)) ],
  h* = h*(ϖ, w) as in §3,   V(·,T) = V_T,

coupled to (HJB), (FP), (CLEAR). Four equations, four unknowns
(u, m, ϖ, V). This is the system the first numerical implementation solves
— it is GS with three additions: the ā/ϖ demand term, the thermal supply
curve, and the reservoir ODE-with-HJB on top.

### 5.2 Common noise and the finite-dimensional reduction (the GGR move)

Under the LQ storage structure, posit the GGR ansatz conditional on B:

  u(x,t) = ½Θ(t)x² + b_t x + κ_t,

with Θ a deterministic Riccati coefficient and (b_t, κ_t) F^B-adapted
processes; then α* = −(Θx + b_t + ϖ_t)/η, the fleet aggregate closes as

  dX_t = −(1/η)(Θ_t X_t + b_t + ϖ_t)dt,

and the system reduces to a **forward–backward SDE in
(R_t, I_t, S_t, X_t; b_t, w_t)**:

- forward: R (reservoir), I, S (exogenous OU), X (fleet SoC);
- backward: b (the field's marginal-value loading; GGR's stochastic
  coefficient, now driven by a *nonlinear* ϖ through (CLEAR)) and w (the
  water value, from the planner's adjoint);
- algebraic: ϖ_t = ϖ(X_t, b_t, w_t, S_t, L_t) from the scalar monotone
  clearing equation.

**Proposition target P1.** Under the ansatz, the SIN-MFG equilibrium is
characterized by this six-dimensional FBSDE; conversely a solution of the
FBSDE yields an equilibrium. (GGR proved the analogous statement for
linear clearing; the work is extending their verification argument through
the strictly monotone nonlinear clearing map — the monotonicity should
carry the argument, not obstruct it.)

This reduction is what makes the model *computable with the validated
stack*: RK4 on the Riccati layer, Monte Carlo over B with the price
adapted path-by-path, the clearing residual as certificate — Tab 06's
machinery with a nonlinear clearing root-find inserted.

---

## 6. Theorem targets

**T1 (existence & uniqueness).** Under: a(·) bounded above/below, C_th
convex increasing, η, κ, σ > 0 — the SIN-MFG equilibrium exists and is
unique. *Strategy:* the coupling acts only through ϖ; the excess-demand map
is strictly decreasing in ϖ and the fleet response is monotone in the GS
sense; assemble Lasry–Lions monotonicity for the (u,m) pair given the
planner layer, then a fixed point in h. The Stackelberg layer is where the
argument must be genuinely new — uniqueness of the planner's best response
given the field's reaction map.

**T2 (decentralization / first welfare theorem).** The equilibrium of §4
implements the planner's full-information optimum: the price system
{ϖ_t = w_t on interior dispatch} decentralizes welfare-optimal behavior of
the continuum. *Corollary (the policy weapon):* any **posted** tariff
τ(t) ≠ ϖ_t induces a welfare gap

  G(τ) = J* − J(τ) ≥ 0,

computable in closed-ish form under the LQ+CD structure — the Tab 05
rebound (+44% / +81%; this draft originally quoted +119%, corrected to the
measured battery figure) becomes a *quantified welfare loss in R$*, and G is
an exploitability-type certificate (G = 0 iff the signal is the
equilibrium price).

**T3 (comparative statics that make economists cry).** Signs and, in the
LQ+CD case, formulas for: ∂w/∂(fleet size) < 0 in scarcity states (storage
substitutes for water — batteries change the *water value*, i.e., the
LRCAP auction feeds back into NEWAVE's central number); ∂Var(ϖ)/∂(fleet
size) < 0 (volatility compression); the deadweight loss of TOU tariffs as
a function of VRE penetration.

**Open question O1 (the invariant).** GGR's exact pathwise conservation
law ϖ + Π + cQ (Tab 06, ~5e−15) is a child of the linear-quadratic
structure. Does a deformed invariant survive CD demand — e.g., is
ϖ_t c*_t + (martingale term) = a(t) an identity along paths (the
expenditure-share property suggests yes in some form)? If found, it is
both a small original lemma and the model's machine-precision certificate.
If provably absent, that is a publishable structural remark about what LQ
linearity buys.

---

## 7. Network extension: the four-submarket layer

Brazil clears in four submarkets (N, NE, SE/CO, S) with interchange limits
F̄_ij on a 4-node graph. Extension: one copy of (HJB)–(FP)–(CLEAR) per
node z, plus interchange flows F_ij with |F_ij| ≤ F̄_ij chosen by the
planner; at the optimum, uncongested lines equalize prices and congested
lines carry the price spread as the constraint multiplier — a
Wardrop-type condition on a graph the **Tab 07 HRF machinery solves
directly** (Kirchhoff per node = local clearing; the "cost" on an edge =
price spread). Certificates: per-node clearing residual + interchange
complementarity (spread·slack = 0). This section is deliberately modular:
the single-node model stands alone; the network layer is the second paper
or §7 of the first.

---

## 8. Calibration map (every symbol → a public dataset)

| Object | Source |
|---|---|
| Ī(t), θ_I, σ_I (inflows/ENA) | ONS Dados Abertos, ENA series by subsystem |
| S̄(t), σ_S (VRE profile & vol) | ONS hourly generation by source, NE focus |
| L_t (inflexible load) | ONS hourly load minus estimated flexible share |
| C_th (thermal merit curve) | CCEE CVU declarations (unit variable costs) |
| R̄, h̄ (reservoir & hydro caps) | ONS reservoir/plant registry |
| ā(t) (CD expenditure shares) | hourly load shape × tariff-elasticity literature; free-market migration data post-Lei 15.269 |
| η, x̄, m_0 (fleet) | LRCAP 2026 contracted capacity & duration (~4h systems) |
| ϖ^def | regulated deficit cost / PLD cap |
| **Validation targets** | hourly PLD by submarket; observed curtailment; submarket spreads |

Weakest empirical link, stated in advance: ā(t) and the demand elasticity
— defensible only after the first aggregator/pilot dataset; until then the
demand side is "calibrated to literature, stress-tested over a range."

## 9. Certificates (the lab standard, applied)

Mass of m (flux form, ~1e−14) · positivity of m (M-matrix) · pre-update
clearing residual per time slice (the market closes to tolerance — the GS
identity: fixed-point residual = physical imbalance) · water-value
consistency w = −∂_R V by two independent computations (adjoint vs
finite-difference of V) · welfare-gap positivity G(τ) ≥ 0 with G(ϖ*) = 0
at machine level · under P1, FBSDE residuals pathwise; if O1 resolves
positively, its invariant at ~1e−15 becomes the flagship receipt.

## 10. Model variants

**B — strategic hydro:** the major maximizes profit ϖh − 0; equilibrium
concept becomes a true major–minor game (Carmona–Zhu); comparing A vs B
prices *quantifies the cost-based vs price-bid debate* — a reform question
with a number attached. **C — heterogeneous fleets:** μ over (η, x̄, a(·));
only mixture aggregates enter clearing, so tractability survives.
**D — CES demand:** c* = (a/ϖ)^{1/(1+ε)}, ε ≠ 0; CD is ε = 0; lets the
data choose the elasticity.

## 11. Honest limitations

Reflecting ≠ hard SoC constraints (as in the lab; disclosed). Aggregate
reservoir ≠ cascades (the seasonal seam V_T imports that complexity as a
boundary condition rather than resolving it). Quasi-linear utility ≠
income effects (full CD-with-budget is the stated extension, adds wealth
as a state). Price-taking continuum ≠ market power (defensible for the
low-voltage mass; not for large gencos — Model B's territory). No unit
commitment, no AC network, no intra-submarket congestion: this model does
not compete with DESSEM and must never claim to — it models the layer
DESSEM cannot see.

## 12. Mapping to the KAUST corpus (the collaboration table)

| Model component | Their result it builds on |
|---|---|
| Price as clearing multiplier; residual = imbalance | Gomes–Saúde 2021 |
| Common noise, adapted price, FBSDE reduction | GGR 2021 / GGR–SIAM 2023 |
| Uniqueness via monotonicity of the coupling | Lasry–Lions + GS argument |
| Network/submarket layer | Bakaryan–…–Ribeiro–Gomes 2025 (HRF) |
| What is new here | CD demand with exact clearing interiority; the benevolent-major (planner ⊗ mean field) Stackelberg layer with endogenous water value; T2's tariff welfare gap; the national-scale certified calibration |

Three questions for the group (the memo's closing): (1) does the GS
uniqueness argument survive the ā/ϖ clearing nonlinearity as expected, or
is displacement monotonicity needed? (2) is there a GGR-type pathwise
invariant under CD demand (O1)? (3) is the planner-⊗-mean-field layer
better attacked via the master equation or via the FBSDE reduction P1?
