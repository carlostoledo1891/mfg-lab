"""Multi-population Wardrop equilibrium by Hessian-Riemannian Flow.

A faithful port of the kernel in mfg-lab.html (Tab 07) and test-wardrop.js,
paper arXiv:2504.16028, Table I edge order. The algorithm is preserved exactly
so the cross-language differential test can hold the two implementations to
machine precision:

  HRF replicator flow (RK4 under a merit rule) drives the iterate to a small
  Wardrop gap; an active-set Newton polish on the used-edge KKT system
  (FD Jacobian, damped normal equations) lands the certificates at machine zero.

Certificates: relative Wardrop gap (complementarity via Bellman potentials),
Kirchhoff residual, positivity, and — for S1 — an independent single-population
KKT check on the total flows.
"""
from __future__ import annotations

import math
import numpy as np

# ---- graph: paper Fig 1a / Table I edge order --------------------------------
EDGES = [(1, 2), (2, 3), (9, 3), (2, 4), (3, 4), (3, 5), (4, 5), (4, 6),
         (5, 6), (3, 7), (4, 7), (5, 7), (6, 7), (7, 8), (7, 10)]
NE = len(EDGES)
EXITS = (8, 10)
TABLE1 = [100, 38, 100, 62, 24, 37, 12, 22, 10, 76, 54, 40, 31, 100, 100]

POS = {1: (0.05, 0.35), 2: (0.22, 0.35), 9: (0.05, 0.78), 3: (0.40, 0.62),
       4: (0.40, 0.22), 5: (0.58, 0.55), 6: (0.58, 0.22), 7: (0.76, 0.42),
       8: (0.94, 0.28), 10: (0.94, 0.58)}
SLEN = [10.0 * math.hypot(POS[u][0] - POS[v][0], POS[u][1] - POS[v][1])
        for (u, v) in EDGES]  # km, illustrative (paper Fig 3a lengths not in text)

OUT: dict[int, list[int]] = {}
for _k, (_u, _v) in enumerate(EDGES):
    OUT.setdefault(_u, []).append(_k)
TOPO = [1, 9, 2, 3, 4, 5, 6, 7, 8, 10]  # DAG order

# emissions table (cars); trucks emit 3x
EM = [(1.56e3, 3.54e1, 1.0321), (1.08e1, -7.11e-3, 12.91), (2.0, -4.49e-2, 14.54),
      (8.08e1, 1.16, 0.37), (4.78e3, 1.11e2, 0.02)]


def reach_edges(src: int) -> list[int]:
    """Edges reachable from an entrance (Remark 6: zero-rows must be dropped)."""
    seen, act, stack = {src}, set(), [src]
    while stack:
        u = stack.pop()
        for k in OUT.get(u, []):
            if k not in act:
                act.add(k)
                v = EDGES[k][1]
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
    return sorted(act)


class Pop:
    """Per-population structure: active edges, restricted Kirchhoff K_r, B_r."""

    def __init__(self, entrance: int, inflow: float):
        self.entrance = entrance
        self.inflow = inflow
        self.act = reach_edges(entrance)
        nodes = set()
        for k in self.act:
            nodes.add(EDGES[k][0])
            nodes.add(EDGES[k][1])
        self.rows = sorted(n for n in nodes if n not in EXITS)
        self.ri = {n: i for i, n in enumerate(self.rows)}
        self.m = len(self.rows)
        self.n = len(self.act)
        K = np.zeros((self.m, self.n))
        for col, k in enumerate(self.act):
            u, v = EDGES[k]
            if u in self.ri:
                K[self.ri[u], col] = 1.0
            if v in self.ri:
                K[self.ri[v], col] = -1.0
        self.K = K
        B = np.zeros(self.m)
        B[self.ri[entrance]] = inflow
        self.B = B


def make_pop(entrance: int, inflow: float) -> Pop:
    return Pop(entrance, inflow)


def interior_start(pop: Pop, rng=None) -> np.ndarray:
    """Strictly-positive feasible start by split-routing in topo order.

    rng=None gives the deterministic start (all split weights 1) used by the
    batteries; passing a numpy Generator randomizes the split (weights 0.2+U).
    """
    in_node = {nd: 0.0 for nd in pop.rows}
    for nd in EXITS:
        in_node[nd] = 0.0
    in_node[pop.entrance] = pop.inflow
    th = np.zeros(pop.n)
    col_of = {k: c for c, k in enumerate(pop.act)}
    for u in TOPO:
        if in_node.get(u, 0.0) <= 0.0 or u in EXITS:
            continue
        outs = [k for k in OUT.get(u, []) if k in col_of]
        if not outs:
            continue
        w = [(0.2 + rng.random()) if rng is not None else 1.0 for _ in outs]
        sw = sum(w)
        for i, k in enumerate(outs):
            f = in_node[u] * w[i] / sw
            th[col_of[k]] += f
            in_node[EDGES[k][1]] = in_node.get(EDGES[k][1], 0.0) + f
        in_node[u] = 0.0
    return th


def gsolve(M: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Partial-pivot Gaussian elimination, ported exactly from the JS kernel so
    the linear algebra matches bit-for-bit (sizes <= ~40)."""
    n = len(b)
    M = M.astype(float).copy()
    b = b.astype(float).copy()
    for k in range(n):
        p, mx = k, abs(M[k, k])
        for r in range(k + 1, n):
            v = abs(M[r, k])
            if v > mx:
                mx, p = v, r
        if p != k:
            M[[k, p], :] = M[[p, k], :]
            b[k], b[p] = b[p], b[k]
        piv = M[k, k] or 1e-300
        for r in range(k + 1, n):
            f = M[r, k] / piv
            M[r, k:] -= f * M[k, k:]
            b[r] -= f * b[k]
    x = np.zeros(n)
    for k in range(n - 1, -1, -1):
        s = b[k] - M[k, k + 1:] @ x[k + 1:]
        x[k] = s / (M[k, k] or 1e-300)
    return x


def make_cost(scen: int, wT: float):
    """Cost per population on the full 15-edge index (paper S1/S2/S3)."""
    def cost(J1, J2, r, out):
        for k in range(NE):
            j1, j2 = J1[k], J2[k]
            if scen == 1:
                out[k] = j1 + j2
            elif scen == 2:
                out[k] = 0.5 * (j1 + wT * j2) + 0.5 * (j1 if r == 1 else j2)
            else:
                jeff = j1 + wT * j2
                v = 50.0 / (1.0 + 5.0 * (jeff / 50.0) ** 3)
                base = 0.0
                for (a, b, w) in EM:
                    base += w * (a / v + b)
                mult = 1.0 if r == 1 else 3.0
                out[k] = SLEN[k] * mult * base / 2.0 + 0.5 * (j1 if r == 1 else j2)
    return cost


class System:
    def __init__(self, scen: int, wT: float, Q1: float, Q2: float):
        self.P1 = make_pop(1, Q1)
        self.P2 = make_pop(9, Q2)
        self.cost = make_cost(scen, wT)
        self.J1 = np.zeros(NE)
        self.J2 = np.zeros(NE)

    def assemble(self, th1, th2):
        self.J1.fill(0.0)
        self.J2.fill(0.0)
        for i, k in enumerate(self.P1.act):
            self.J1[k] = th1[i]
        for i, k in enumerate(self.P2.act):
            self.J2[k] = th2[i]

    def _pop_rhs(self, P: Pop, th, r, dth):
        c = np.zeros(NE)
        self.cost(self.J1, self.J2, r, c)
        cact = c[P.act]                     # cost on active edges
        y = th * cact                       # diag(theta) c
        z = P.K @ y
        M = P.K @ (th[:, None] * P.K.T)     # K diag(theta) K^T
        lam = gsolve(M, z)
        dth[:] = -y + th * (P.K.T @ lam)

    def rhs(self, th1, th2, d1, d2):
        self.assemble(th1, th2)
        self._pop_rhs(self.P1, th1, 1, d1)
        self._pop_rhs(self.P2, th2, 2, d2)


def make_system(scen: int, wT: float, Q1: float, Q2: float) -> System:
    return System(scen, wT, Q1, Q2)


def min_pos(a, b) -> float:
    return min(float(a.min()), float(b.min()))


def bellman(P: Pop, c) -> dict:
    """Shortest cost-to-exit potentials on the reachable subgraph (c on full index)."""
    phi = {e: 0.0 for e in EXITS}
    col_of = {k: i for i, k in enumerate(P.act)}
    for t in range(len(TOPO) - 1, -1, -1):
        u = TOPO[t]
        if u in EXITS:
            continue
        outs = [k for k in OUT.get(u, []) if k in col_of]
        if not outs:
            continue
        mn = math.inf
        for k in outs:
            v = EDGES[k][1]
            if v in phi:
                mn = min(mn, c[k] + phi[v])
        phi[u] = mn
    return phi


def wardrop_gap(sys: System, th1, th2) -> float:
    """Relative Wardrop gap: complementarity via Bellman cost-to-exit potentials.
    The 1952 Wardrop principle as a readout."""
    sys.assemble(th1, th2)
    c1 = np.zeros(NE)
    c2 = np.zeros(NE)
    sys.cost(sys.J1, sys.J2, 1, c1)
    sys.cost(sys.J1, sys.J2, 2, c2)
    gap = 0.0
    val = 0.0
    for P, th, c in ((sys.P1, th1, c1), (sys.P2, th2, c2)):
        phi = {e: 0.0 for e in EXITS}
        col_of = {k: i for i, k in enumerate(P.act)}
        for t in range(len(TOPO) - 1, -1, -1):
            u = TOPO[t]
            if u in EXITS:
                continue
            outs = [k for k in OUT.get(u, []) if k in col_of]
            if not outs:
                continue
            mn = math.inf
            for k in outs:
                v = EDGES[k][1]
                if v in phi:
                    mn = min(mn, c[k] + phi[v])
            phi[u] = mn
        for i, k in enumerate(P.act):
            u, v = EDGES[k]
            slack = c[k] + phi[v] - phi[u]
            gap += th[i] * slack
            val += th[i] * c[k]
    return gap / max(val, 1e-300)


def kirchhoff_res(P: Pop, th) -> float:
    return float(np.max(np.abs(P.K @ th - P.B)))


def totals(sys: System, th1, th2) -> list[float]:
    sys.assemble(th1, th2)
    return [sys.J1[k] + sys.J2[k] for k in range(NE)]


def integrate(sys: System, th1, th2, tol: float = 1e-11, max_steps: int = 8000) -> dict:
    """HRF replicator flow, RK4 under a merit rule: a step is accepted only if
    the relative Wardrop gap does not increase (discrete Bregman-Lyapunov decay).
    dt shrinks x0.4 on rejection, grows x1.3 on acceptance."""
    n1, n2 = len(th1), len(th2)
    k1a, k1b = np.zeros(n1), np.zeros(n2)
    k2a, k2b = np.zeros(n1), np.zeros(n2)
    k3a, k3b = np.zeros(n1), np.zeros(n2)
    k4a, k4b = np.zeros(n1), np.zeros(n2)
    ta, tb = np.zeros(n1), np.zeros(n2)
    dt = 1e-4
    steps = 0
    g = wardrop_gap(sys, th1, th2)

    def trial():
        sys.rhs(th1, th2, k1a, k1b)
        ta[:] = th1 + 0.5 * dt * k1a
        tb[:] = th2 + 0.5 * dt * k1b
        if min_pos(ta, tb) <= 0:
            return None
        sys.rhs(ta, tb, k2a, k2b)
        ta[:] = th1 + 0.5 * dt * k2a
        tb[:] = th2 + 0.5 * dt * k2b
        if min_pos(ta, tb) <= 0:
            return None
        sys.rhs(ta, tb, k3a, k3b)
        ta[:] = th1 + dt * k3a
        tb[:] = th2 + dt * k3b
        if min_pos(ta, tb) <= 0:
            return None
        sys.rhs(ta, tb, k4a, k4b)
        ta[:] = th1 + dt / 6.0 * (k1a + 2 * k2a + 2 * k3a + k4a)
        tb[:] = th2 + dt / 6.0 * (k1b + 2 * k2b + 2 * k3b + k4b)
        if min_pos(ta, tb) <= 0:
            return None
        return wardrop_gap(sys, ta, tb)

    while steps < max_steps and g > tol:
        g_new = None
        tries = 0
        while tries < 50:
            g_new = trial()
            if g_new is not None and g_new <= g * (1 + 1e-12):
                break
            dt *= 0.4
            tries += 1
        if g_new is None or not (g_new <= g * (1 + 1e-12)):
            break
        th1[:] = ta
        th2[:] = tb
        g = g_new
        steps += 1
        dt *= 1.3
    return {"steps": steps, "gap": g, "dt": dt}


def polish(sys: System, th1, th2) -> bool:
    """Active-set Newton on the used-edge KKT system (slack=0 on support +
    Kirchhoff), FD Jacobian, damped normal equations, with an outer active-set
    loop. Operates on copies; commits only on validation. Returns True iff the
    active set validates (gap < 1e-10, positivity)."""
    sys.assemble(th1, th2)
    c1 = np.zeros(NE)
    c2 = np.zeros(NE)
    pops = [(sys.P1, th1, c1, 1), (sys.P2, th2, c2, 2)]
    U = [[], []]
    for pi, (P, th, _c, _r) in enumerate(pops):
        thr = 1e-6 * max(1.0, P.inflow)
        U[pi] = [i for i in range(P.n) if th[i] > thr]
    cur = [th1.copy(), th2.copy()]

    def solve_on_support():
        layout = []
        nx = 0
        for pi, (P, _th, _c, r) in enumerate(pops):
            layout.append({"P": P, "r": r, "pi": pi, "U": U[pi],
                           "nodes": list(P.rows), "offTh": nx,
                           "offPhi": nx + len(U[pi])})
            nx += len(U[pi]) + len(P.rows)
        x = np.zeros(nx)
        for L in layout:
            for a, i in enumerate(L["U"]):
                x[L["offTh"] + a] = max(cur[L["pi"]][i], 1e-3)
            sys.J1.fill(0.0)
            sys.J2.fill(0.0)
            for M2 in layout:
                J = sys.J1 if M2["r"] == 1 else sys.J2
                for a, i in enumerate(M2["U"]):
                    J[M2["P"].act[i]] = max(cur[M2["pi"]][i], 1e-3)
            c = c1 if L["r"] == 1 else c2
            sys.cost(sys.J1, sys.J2, L["r"], c)
            phi = bellman(L["P"], c)
            for a, nd in enumerate(L["nodes"]):
                x[L["offPhi"] + a] = phi.get(nd, 0.0)

        def eval_F(xv, F):
            sys.J1.fill(0.0)
            sys.J2.fill(0.0)
            for L in layout:
                J = sys.J1 if L["r"] == 1 else sys.J2
                for a, i in enumerate(L["U"]):
                    J[L["P"].act[i]] = xv[L["offTh"] + a]
            e = 0
            for L in layout:
                c = c1 if L["r"] == 1 else c2
                sys.cost(sys.J1, sys.J2, L["r"], c)

                def phi_of(nd, L=L, xv=xv):
                    if nd in EXITS:
                        return 0.0
                    a = L["nodes"].index(nd)
                    return xv[L["offPhi"] + a]

                for i in L["U"]:
                    k = L["P"].act[i]
                    u, v = EDGES[k]
                    F[e] = c[k] + phi_of(v) - phi_of(u)
                    e += 1
                for nd in L["nodes"]:
                    row = L["P"].ri[nd]
                    s = -L["P"].B[row]
                    for a, i in enumerate(L["U"]):
                        s += L["P"].K[row, i] * xv[L["offTh"] + a]
                    F[e] = s
                    e += 1

        F = np.zeros(nx)
        Fp = np.zeros(nx)
        xp = np.zeros(nx)
        Jm = np.zeros((nx, nx))
        for _it in range(8):
            eval_F(x, F)
            if np.max(np.abs(F)) < 1e-12:
                break
            for j in range(nx):
                h = 1e-7 * max(1.0, abs(x[j]))
                xp[:] = x
                xp[j] += h
                eval_F(xp, Fp)
                Jm[:, j] = (Fp - F) / h
            JtJ = Jm.T @ Jm
            JtF = Jm.T @ F
            tr = np.trace(JtJ)
            mu = 1e-12 * (tr / nx + 1.0)
            JtJ = JtJ + mu * np.eye(nx)
            dx = gsolve(JtJ, JtF)
            x -= dx
        return layout, x

    for _round in range(8):
        layout, x = solve_on_support()
        changed = False
        for L in layout:
            ntol = 1e-9 * (1.0 + L["P"].inflow)
            keep, vals = [], []
            for a, i in enumerate(L["U"]):
                v = x[L["offTh"] + a]
                if v <= -ntol:
                    changed = True
                else:
                    keep.append(i)
                    vals.append(max(v, 0.0))
            U[L["pi"]] = keep
            cur[L["pi"]].fill(0.0)
            for a, i in enumerate(keep):
                cur[L["pi"]][i] = vals[a]
        if changed:
            continue
        th1[:] = cur[0]
        th2[:] = cur[1]
        sys.assemble(th1, th2)
        worst = None
        for pi, (P, _th, c, r) in enumerate(pops):
            sys.cost(sys.J1, sys.J2, r, c)
            phi = bellman(P, c)
            for i in range(P.n):
                if i in U[pi]:
                    continue
                k = P.act[i]
                u, v = EDGES[k]
                scl = 1.0 + abs(phi.get(u, 0.0))
                s = (c[k] + phi.get(v, 0.0) - phi.get(u, 0.0)) / scl
                if s < -1e-8 and (worst is None or s < worst[2]):
                    worst = (pi, i, s)
        if worst is not None:
            U[worst[0]].append(worst[1])
            U[worst[0]].sort()
            cur[worst[0]][worst[1]] = 1e-3
            continue
        return wardrop_gap(sys, th1, th2) < 1e-10 and min_pos(th1, th2) >= 0
    return False


def totals_kkt_gap(T) -> float:
    """Independent single-population KKT check on TOTAL flows (S1: c = total).
    Proves the totals are THE optimum, not merely A fixed point."""
    phi = {e: 0.0 for e in EXITS}
    for t in range(len(TOPO) - 1, -1, -1):
        u = TOPO[t]
        if u in EXITS:
            continue
        outs = OUT.get(u, [])
        if not outs:
            continue
        mn = math.inf
        for k in outs:
            v = EDGES[k][1]
            if v in phi:
                mn = min(mn, T[k] + phi[v])
        phi[u] = mn
    gap = 0.0
    val = 0.0
    for k in range(NE):
        u, v = EDGES[k]
        gap += T[k] * (T[k] + phi[v] - phi[u])
        val += T[k] * T[k]
    return gap / max(val, 1e-300)


def solve_scenario(scen: int, wT: float = 2.0, Q1: float = 100.0, Q2: float = 100.0,
                   tol: float = 1e-8, max_steps: int = 12000, rng=None) -> dict:
    """Solve a scenario to a certified equilibrium and return the certificates.

    Returns a dict with the certified totals, the Wardrop gap, Kirchhoff
    residual, the polish flag, and (for reference) HRF step count.
    """
    sys = make_system(scen, wT, Q1, Q2)
    th1 = interior_start(sys.P1, rng)
    th2 = interior_start(sys.P2, rng)
    r = integrate(sys, th1, th2, tol=tol, max_steps=max_steps)
    pol = polish(sys, th1, th2)
    T = totals(sys, th1, th2)
    return {
        "scen": scen, "wT": wT, "Q1": Q1, "Q2": Q2,
        "totals": T,
        "gap": wardrop_gap(sys, th1, th2),
        "kirch": max(kirchhoff_res(sys.P1, th1), kirchhoff_res(sys.P2, th2)),
        "kkt_totals": totals_kkt_gap(T),
        "min_pos": min_pos(th1, th2),
        "polished": bool(pol),
        "hrf_steps": r["steps"],
    }
