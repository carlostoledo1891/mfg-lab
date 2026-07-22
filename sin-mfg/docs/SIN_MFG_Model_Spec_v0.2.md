# SIN-MFG v0.2 — Mean-Field Price Formation with an Intertemporal Resource Constraint

## Mathematical Specification — revision of v0.1 after internal referee report

> **Changelog from v0.1 (material changes only).**
> (1) "Major–minor game" reframed: benevolent hydro collapses to a planner
> problem (by our own T2), so Model A is now **an MFG with a
> Hotelling-type stock constraint** — hydro as a competitive resource with
> intertemporal opportunity cost; the game content lives in the
> tariff-disequilibrium analysis and in Model B.
> (2) CD demand **satiated**: c* = min(a/ϖ, c̄(t)). Pure CD makes
> curtailment impossible — the model must contain the phenomenon that
> motivates it. Clearing now has **three regimes** (curtailment / interior
> / scarcity) with free boundaries.
> (3) O1 replaced by the **water-value martingale certificate** (sharp,
> testable, machine-checkable).
> (4) Planner welfare integrand completed; discounting made consistent
> (ρ = 0 on the operational horizon); reflected-FBSDE caveat stated;
> clearing typo removed.
> (5) Related work extended; novelty claims narrowed to what survives it.

---

## 1. Primitives

Horizon t ∈ [0,T] (operational: 24h–168h; ρ = 0 — discounting is
irrelevant at this scale and its v0.1 half-presence was an error; the
seasonal model reintroduces ρ). Common noise B_t = (B^I, B^S):

- Inflows: dI_t = θ_I(Ī(t) − I_t)dt + σ_I dB^I_t (ENA-calibrated).
- VRE: dS_t = θ_S(S̄(t) − S_t)dt + σ_S(t)dB^S_t (GGR's random supply).
- Inflexible load L_t deterministic.

Idiosyncratic noises W_t i.i.d. across the continuum; aggregates adapted
to F^B (conditional McKean–Vlasov, GGR setting).

## 2. Minor agents

State x_t ∈ [0,x̄]: dx_t = α_t dt + σ dW_t, reflecting (disclosed
approximation of SoC constraints, lab convention). Flow objective

  a(t) log c − ϖ_t (c + α) − ½η α²,   terminal Ψ(x) = −κ(x − x*)².

**Satiated Cobb–Douglas demand.** c ∈ (0, c̄(t)] with c̄(t) the physical
service cap. FOC:

  c*(ϖ,t) = min( a(t)/ϖ , c̄(t) ),   with satiation price p̂(t) = a(t)/c̄(t).

Above p̂: CD regime, expenditure = a(t) (constant shares — the CD
signature, and the calibration handle: ā(t) is read off expenditure data).
Below p̂: demand caps — the regime where oversupply and curtailment become
possible. Aggregation: with heterogeneity μ over (a, c̄), aggregate demand
D(ϖ,t) = ∫ min(a/ϖ, c̄) dμ is **strictly decreasing in ϖ on the CD branch
and constant on the satiated branch** — monotone throughout, kinked at the
satiation frontier. (v0.1's "only ā matters" survives on the CD branch
only; the satiated branch needs the joint law of (a, c̄) — stated, not
hidden.)

**Storage side — verbatim GS/GGR.** Conditional on F^B:

  (HJB)  −∂_t u − ½σ²∂_xx u + (1/2η)(∂_x u + ϖ_t)² = 0,
         u(·,T) = Ψ, ∂_x u|_{0,x̄} = 0;   α* = −(∂_x u + ϖ_t)/η.

  (FP)   ∂_t m − ½σ²∂_xx m − (1/η)∂_x( m(∂_x u + ϖ_t) ) = 0,
         m(·,0)=m₀, zero-flux.

Fleet flow A_t = −(1/η)(∫∂_x u·m dx + ϖ_t); its contemporaneous price
sensitivity, **holding u fixed** (the object relevant for clearing
monotonicity), is −1/η.

## 3. Hydro as a constrained competitive resource (the reframing)

Reservoir dR_t = (I_t − h_t)dt − dU_t (spill at R̄), h_t ∈ [0,h̄]. Hydro is
**price-taking with zero marginal fuel cost and a stock constraint** — the
electricity version of Hotelling's exhaustible resource with
replenishment. Its equilibrium behavior is characterized by a water value
process w_t ≥ 0 (the stock constraint's multiplier):

  h_t = 0 on {ϖ_t < w_t},  h_t = h̄ on {ϖ_t > w_t},  ϖ_t = w_t on interior;

and w satisfies the complementarity/martingale dynamics of §6. The planner
formulation is now what it truly is — the **welfare benchmark** whose
decentralization is Theorem T2 — not a second player. Thermal: convex
C_th, supply q*(ϖ) = (C_th′)^{-1}(ϖ) from the CVU merit curve; deficit at
cap ϖ^def.

## 4. Three-regime clearing

Balance conditional on F^B:

  D(ϖ_t,t) + L_t + A_t = h_t + q*(ϖ_t) + (S_t − κ_t) + d_t,

κ_t ≥ 0 curtailed VRE, d_t ≥ 0 unserved energy, with complementarity

  κ_t ≥ 0 ⟂ ϖ_t ≥ ϖ^floor,   d_t ≥ 0 ⟂ ϖ_t ≤ ϖ^def.

Three regimes, free boundaries between them:

- **C (curtailment):** ϖ = ϖ^floor, demand satiated, κ_t > 0 absorbs the
  residual — the NE constrained-off regime, now representable; the fleet's
  role in shrinking regime C is the coordinated-fleet question, posed inside
  the model.
- **I (interior):** excess-demand Φ(ϖ) = D(ϖ)+L+A−h−q*(ϖ)−S strictly
  decreasing ⇒ unique clearing price; pre-update |Φ(ϖ_t)| is the
  certificate (Tab 05 identity).
- **S (scarcity):** ϖ = ϖ^def, d_t > 0.

**Definition (equilibrium).** (u, m, ϖ, h, κ, d) adapted, with (i)–(ii)
the HJB/FP pair given ϖ; (iii) the regime-wise clearing with
complementarity at every t; (iv) hydro's Hotelling conditions; existence
of the multiplier formulation à la GS for the generalized balance
constraint is itself a stated research question (Q1′).

## 5. Coupled system and reduction

**Deterministic benchmark** (first implementation target): (HJB)–(FP) +
regime-wise clearing + the water-value ODE with complementarity — solved
by the validated kernel + a scalar monotone root-find with regime
detection per slice + a shooting/adjoint pass for w. Planner welfare (for
T2/G(τ)) now with the **complete integrand**:

  J = ∫_0^T [ ∫(a log c − ½ηα²) dμ dm − C_th(q) − ϖ^def d − 0·κ ] dt
      + ∫Ψ dm_T + V_T(R_T).

**Common noise.** LQ-storage ansatz u = ½Θx² + b_t x + κ̃_t reduces the
field to (X_t; b_t) as in GGR; the system becomes a **reflected FBSDE** in
(R, I, S, X; b, w): reflection enters through R ∈ [0,R̄], h ∈ [0,h̄] and the
regime complementarities — materially harder than v0.1 admitted; the
constrained-FBSDE literature (reflected BSDEs, Gegout-Petit–Pardoux
lineage) is the toolbox, and P1 is scoped to: *the reduction holds
regime-wise, with the regime boundaries as the pasting conditions.*

## 6. Theorem targets (revised)

**T1 (existence/uniqueness).** Via monotonicity: demand monotone (kinked),
supply monotone, fleet response GS-monotone; the new difficulty is
uniqueness across regime boundaries. Honest scope: prove for the interior
regime with GS's argument extended to nonlinear monotone clearing; treat
regime-crossing uniqueness as a stated open problem (this is where the
group's expertise is genuinely needed — question for them, not a hidden
gap).

**T2 (decentralization).** Equilibrium = planner optimum. Standard in
kind; the *content* is constructive: G(τ) = J* − J(τ) ≥ 0 computed
explicitly for posted tariffs under the LQ+CD structure — the Tab 05
rebound as deadweight loss in R$. (Novelty claimed for the computation and
calibration, not for the welfare theorem.)

**T3 (the water-value martingale — flagship structural result).** On the
interior-dispatch, slack-reservoir region:

  w_t is an F^B-martingale;  deterministically, w is **constant** —
  the price is pinned flat across hydro-marginal windows.

Three roles: (a) theorem (Hotelling-in-MFG; we have not found this
statement in the MFG literature); (b) **pathwise machine-precision
certificate** in simulation — the GGR-invariant role, inherited by the new
model; (c) **empirical prediction testable on hourly PLD**: within
hydro-marginal windows, price variation should be attributable to regime
switches and constraint events, not drift. A falsifiable claim about
Brazil, checkable from public data before any pilot.

**T4 (comparative statics).** ∂w/∂(fleet size) < 0 in scarcity states
(batteries lower the water value — LRCAP feeds back into the system's
central number); Var(ϖ) decreasing in fleet size; measure of regime C
(curtailed energy) decreasing in coordinated fleet size — *the
coordinated-fleet thesis as a theorem statement*.

## 7. Network layer (promoted from optional)

Curtailment in Brazil is substantially **constrained-off** — transmission,
not only oversupply — so the 4-submarket layer (N/NE/SE-CO/S, interchange
limits, HRF machinery of Tab 07) is now core to the curtailment story,
not an appendix: regime C is reached locally (NE) while regime I holds
system-wide. Per-node clearing + interchange complementarity
(spread·slack = 0) as certificates.

## 8. Calibration map — unchanged from v0.1 (§8) with one addition

c̄(t), and the joint law (a, c̄): from load decomposition + appliance
saturation studies; weakest link alongside elasticities, said in advance;
first aggregator dataset repairs both.

## 9. Related work and the surviving delta

MFG for electricity exists and is good: Alasseur–Ben Tahar–Matoussi
(storage MFG), Aïd–Basei–Pham (principal–agent demand response),
Féron–Tankov (intraday markets), Carmona et al. (regulator MFG),
Shrivats–Firoozi–Jaimungal (certificate markets); GS/GGR (price
formation, common noise). **Claimed delta, narrowed:** (i) the hydro
stock constraint inside MFG price formation and its martingale water
value (T3); (ii) three-regime clearing with satiated-CD demand,
containing curtailment; (iii) the welfare gap G(τ) computed and
calibrated; (iv) a certified, reproducible national-scale implementation
— which no paper in this literature ships. Everything else is
acknowledged inheritance.

## 10. Variants

B — strategic hydro with price impact (the cost-based vs price-bid
counterfactual; requires a price-impact formulation, flagged as nontrivial).
C — heterogeneous fleets. D — CES demand c* = (a/ϖ)^{1/(1+ε)} ∧ c̄, data
chooses ε.

## 11. Limitations (v0.1 list, plus)

Reflected FBSDE hardness now stated; regime-boundary uniqueness open;
aggregate reservoir ≠ cascades; quasi-linearity ≠ income effects;
price-taking ≠ market power (Model B); no unit commitment / AC network —
this is the layer DESSEM cannot see, never a DESSEM substitute.

## 12. Questions for the group (revised)

(1) Does the GS multiplier formulation of price formation extend to the
generalized balance with elastic demand and complementarity regimes (Q1′)?
(2) T3: is the water-value martingale known to you in the MFG setting, and
what is the right proof architecture — master equation or reflected FBSDE?
(3) Regime-crossing uniqueness: monotonicity methods or a viscosity/free-
boundary argument?
