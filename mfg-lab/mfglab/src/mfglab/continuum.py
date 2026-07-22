"""SIN-MFG continuum kernel — the FD-monotone port (roadmap step: port the
continuum kernel to Python, batteries → pytest, cross-language differential).

Faithful Python port of the kernel shipped in ``sin-mfg/sin-mfg.html``
(the code of record): the coupled HJB/Fokker–Planck field solve, the
band-clearing case analysis, the hydro dispatch with its water-value
bisection (spill and cap-mixed regimes included), the damped Picard
driver, and the independent DP exploitability audit. The port is
statement-for-statement — explicit loops in the JS accumulation order,
NOT vectorized — so the cross-language differential
(``tests/test_crosslang_continuum.py``) can hold Python against the
shipped artifact at machine-ish precision. The JS artifact remains the
deployed reference; this module is the package's source of truth going
forward (same convention as ``wardrop.py``).

Two schemes:

* ``solve_field``  — the SHIPPED scheme: centered HJB gradient (explicit,
  operator-split, NSUB=4) against an upwind conservative FP with CFL
  sub-stepping.  Deliberately NOT adjoint-matched (measured defect ~1.0);
  conservation comes from the flux form.  This is what the note runs and
  what the differential validates.
* ``solve_field_upwind`` — the Achdou adjoint-matched pair for the same
  Hamiltonian (port of ``sin-mfg/tools/continuum_reference.js``): shared
  frozen interface velocities, FP = HJBᵀ exactly (including at clamped
  interfaces), symmetric reflecting diffusion folded into one implicit
  tridiagonal per slice — strict M-matrix, so positivity and exact mass
  conservation hold with no CFL sub-stepping.  Its equilibria differ
  numerically from the shipped scheme's (upwinding adds numerical
  diffusion); its certificates are structural, certified in
  ``tests/test_continuum.py``.  The system-level exact-discrete-KKT
  statement at a solved equilibrium is future work and is not claimed.

Aggregate read-outs for the upwind scheme (``Ux``, ``A``) use the same
m-weighted centered-gradient convention as the shipped kernel, so the
clearing layer sees both schemes through one interface; this is a
declared read-out convention, not part of the transpose certificate.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field as dfield

import numpy as np

# ---- constants: mirrors of sin-mfg.html:333-341 ----
NT, DT, NX, XBAR = 24, 1.0, 16, 4.0
HX = XBAR / NX
SIG, ETA, AMAX = 0.10, 8.0, 0.35
KAPT, XSTAR, GAM, QBAR, HBAR, CBAR = 0.6, 2.0, 2.5, 0.42, 0.30, 0.5
XS = [(i + 0.5) * HX for i in range(NX)]
NU = 0.5 * SIG * SIG


def bump(t: float, c: float, s: float) -> float:
    return math.exp(-0.5 * ((t - c) / s) ** 2)


@dataclass
class Params:
    """The slider box P of the artifact (sin-mfg.html:338)."""
    sol: float = 1.25
    pk: float = 0.50
    phi: float = 1.0
    EHYD: float = 3.2
    PMIN: float = 0.05
    PMAX: float = 3.0


def Lt(t: float, P: Params) -> float:
    return 0.42 + P.pk * bump(t, 19, 1.8)


def St(t: float, P: Params) -> float:
    return P.sol * bump(t, 12.5, 2.6)


def At_(t: float) -> float:
    return 0.30 + 0.22 * bump(t, 19.5, 2.4)


def thomas(a, b, c, d):
    """Tridiagonal solve — verbatim algorithm of sin-mfg.html:343-350."""
    n = len(d)
    cp = [0.0] * n
    dp = [0.0] * n
    x = [0.0] * n
    cp[0] = c[0] / b[0]
    dp[0] = d[0] / b[0]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / m
        dp[i] = (d[i] - a[i] * dp[i - 1]) / m
    x[n - 1] = dp[n - 1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


def _diffuse(v, dtf):
    r = NU * dtf / (HX * HX)
    a = [-r] * NX
    b = [1 + 2 * r] * NX
    c = [-r] * NX
    b[0] = 1 + r
    b[NX - 1] = 1 + r
    a[0] = 0.0
    c[NX - 1] = 0.0
    return thomas(a, b, c, list(v))


def _clamp(v):
    return max(-AMAX, min(AMAX, v))


def _m0():
    sd = 0.7
    m0 = [math.exp(-0.5 * ((XS[i] - 1.2) / sd) ** 2) for i in range(NX)]
    Z = sum(mi * HX for mi in m0)
    return [mi / Z for mi in m0]


def solve_field(price):
    """The shipped centered/upwind-split scheme — sin-mfg.html:351-412."""
    u = [[0.0] * NX for _ in range(NT + 1)]
    u[NT] = [-KAPT * (XS[i] - XSTAR) ** 2 for i in range(NX)]
    NSUB = 4
    dtf = DT / NSUB
    for t in range(NT - 1, -1, -1):
        v = list(u[t + 1])
        for _ in range(NSUB):
            w = [0.0] * NX
            for i in range(NX):
                uxp = (v[i + 1] - v[i]) / HX if i < NX - 1 else 0.0
                uxm = (v[i] - v[i - 1]) / HX if i > 0 else 0.0
                ux = 0.5 * (uxp + uxm)
                ac = _clamp((ux - price[t]) / ETA)
                w[i] = v[i] + dtf * (ac * (ux - price[t]) - 0.5 * ETA * ac * ac)
            v = _diffuse(w, dtf)
        u[t] = list(v)
    m = [[0.0] * NX for _ in range(NT + 1)]
    m[0] = _m0()
    A = [0.0] * NT
    Ux = [0.0] * NT
    for t in range(NT):
        al = [0.0] * NX
        uxi = 0.0
        for i in range(NX):
            uxp = (u[t][i + 1] - u[t][i]) / HX if i < NX - 1 else 0.0
            uxm = (u[t][i] - u[t][i - 1]) / HX if i > 0 else 0.0
            ux = 0.5 * (uxp + uxm)
            al[i] = _clamp((ux - price[t]) / ETA)
            uxi += ux * m[t][i] * HX
        Ux[t] = uxi
        mv = list(m[t])
        amax = max(abs(x) for x in al)
        ns = min(64, max(NSUB, math.ceil(amax * DT / (0.8 * HX))))
        dts = DT / ns
        for _ in range(ns):
            flux = [0.0] * (NX + 1)
            for f in range(1, NX):
                a = 0.5 * (al[f - 1] + al[f])
                flux[f] = a * mv[f - 1] if a > 0 else a * mv[f]
            w = [mv[i] - dts * (flux[i + 1] - flux[i]) / HX for i in range(NX)]
            mv = _diffuse(w, dts)
        m[t + 1] = list(mv)
        A[t] = sum(al[i] * m[t][i] * HX for i in range(NX))
    return {"u": u, "m": m, "A": A, "Ux": Ux}


# ---------------- clearing and dispatch (sin-mfg.html:413-520) ----------------

def make_n(t, Ux, P: Params):
    ab, L, S = At_(t), Lt(t, P), St(t, P)

    def N(p):
        fleet = P.phi * _clamp((Ux - p) / ETA)
        return min(ab / p, CBAR) + L + fleet - min(p / GAM, QBAR) - S

    return N


def bisect(f, lo, hi):
    flo = f(lo)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if flo * fm <= 0:
            hi = mid
        else:
            lo = mid
            flo = fm
    return 0.5 * (lo + hi)


def clear_slice(t, Ux, w, P: Params):
    """Complete case analysis — branch-for-branch port; ORDER IS LOAD-BEARING
    (withholding before scarcity — see the artifact's comment and
    FINDINGS_SIN Defect 1)."""
    N = make_n(t, Ux, P)
    h = k = d = 0.0
    if N(P.PMIN) <= 0:
        p = P.PMIN
        k = -N(P.PMIN)
    elif w > P.PMAX:
        if N(P.PMAX) >= 0:
            p = P.PMAX
            d = N(P.PMAX)
        else:
            p = bisect(N, P.PMIN, P.PMAX)
    elif N(P.PMAX) >= HBAR:
        p = P.PMAX
        h = HBAR
        d = N(P.PMAX) - HBAR
    else:
        wc = max(w, P.PMIN)
        Nw = N(wc)
        if 0 <= Nw <= HBAR:
            p = wc
            h = Nw
        elif Nw < 0:
            h = 0.0
            p = bisect(N, P.PMIN, P.PMAX)
        else:
            h = HBAR
            p = bisect(lambda x: N(x) - HBAR, wc, P.PMAX)
    q = min(p / GAM, QBAR)
    return {"p": p, "h": h, "k": k, "d": d, "q": q}


def dispatch(Ux, P: Params):
    def tot(w):
        return sum(clear_slice(t, Ux[t], w, P)["h"] * DT for t in range(NT))

    lo, hi = 1e-4, P.PMAX + 5
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        if tot(mid) > P.EHYD:
            lo = mid
        else:
            hi = mid
    w = 0.5 * (lo + hi)
    spill, mix = 0.0, None
    totW = tot(w)
    if totW < P.EHYD - 1e-6 and w <= P.PMIN + 1e-3:
        spill = P.EHYD - totW
        w = P.PMIN
    elif abs(totW - P.EHYD) > 1e-6 and abs(w - P.PMAX) < 1e-3:
        # dual kink at the cap: MIXED dispatch, pooled uniformly (A2 cap-mixed)
        w = P.PMAX
        sl = [None] * NT
        pool = []
        for t in range(NT):
            N = make_n(t, Ux[t], P)
            if N(P.PMIN) <= 0:
                sl[t] = {"p": P.PMIN, "h": 0.0, "k": -N(P.PMIN), "d": 0.0,
                         "q": min(P.PMIN / GAM, QBAR)}
            elif N(P.PMAX) < 0:
                sl[t] = clear_slice(t, Ux[t], P.PMAX, P)
            else:
                pool.append({"t": t, "cap": min(HBAR, N(P.PMAX)), "nd": N(P.PMAX)})
        avail = sum(x["cap"] for x in pool)
        th = min(1.0, max(0.0, (P.EHYD / DT) / max(avail, 1e-12)))
        for x in pool:
            hh = th * x["cap"]
            sl[x["t"]] = {"p": P.PMAX, "h": hh, "k": 0.0, "d": x["nd"] - hh,
                          "q": min(P.PMAX / GAM, QBAR)}
        return {"w": w, "sl": sl, "spill": 0.0, "mix": th}
    sl = [clear_slice(t, Ux[t], w, P) for t in range(NT)]
    return {"w": w, "sl": sl, "spill": spill, "mix": mix}


def picard(P: Params | None = None, max_it: int = 250, tol: float = 1e-10,
           field_solver=solve_field):
    """Damped fixed point exactly as the artifact drives it (theta = 0.5,
    residual measured PRE-update)."""
    P = P or Params()
    price = [0.8] * NT
    fld = disp = None
    res, it = 1.0, 0
    for _ in range(max_it):
        fld = field_solver(price)
        disp = dispatch(fld["Ux"], P)
        p_new = [s["p"] for s in disp["sl"]]
        res = max(abs(p_new[t] - price[t]) for t in range(NT))
        it += 1
        if res < tol:
            break
        price = [0.5 * price[t] + 0.5 * p_new[t] for t in range(NT)]
    return {"price": price, "field": fld, "disp": disp, "res": res, "it": it,
            "conv": res < tol, "P": P}


# ---------------- independent audits (sin-mfg.html:521-605) ----------------

def dp_audit(price, fld):
    """Semi-Lagrangian DP best-response exploitability — deliberately a
    DIFFERENT scheme from the field solve (its value is independence)."""
    NC = 41
    acts = [-AMAX + 2 * AMAX * j / (NC - 1) for j in range(NC)]
    pdif = NU * DT / (HX * HX)
    Psi = [-KAPT * (XS[i] - XSTAR) ** 2 for i in range(NX)]

    def ev(V, i, a):
        xn = min(max(XS[i] + a * DT, XS[0]), XS[NX - 1])
        f = (xn - XS[0]) / HX
        i0 = min(NX - 2, math.floor(f))
        th = f - i0
        e = (1 - th) * V[i0] + th * V[i0 + 1]
        iu, idn = min(NX - 1, i + 1), max(0, i - 1)
        return (1 - 2 * pdif) * e + pdif * (V[iu] + V[idn])

    Vbr, Vpi = list(Psi), list(Psi)
    for t in range(NT - 1, -1, -1):
        u = fld["u"][t]
        nb, npi = [0.0] * NX, [0.0] * NX
        for i in range(NX):
            uxp = (u[i + 1] - u[i]) / HX if i < NX - 1 else 0.0
            uxm = (u[i] - u[i - 1]) / HX if i > 0 else 0.0
            pol = _clamp((0.5 * (uxp + uxm) - price[t]) / ETA)
            best = -1e18
            for a in acts:
                v = (-price[t] * a - 0.5 * ETA * a * a) * DT + ev(Vbr, i, a)
                if v > best:
                    best = v
            nb[i] = best
            npi[i] = (-price[t] * pol - 0.5 * ETA * pol * pol) * DT + ev(Vpi, i, pol)
        Vbr, Vpi = nb, npi
    eps = sum((Vbr[i] - Vpi[i]) * fld["m"][0][i] * HX for i in range(NX))
    return {"eps": eps}


def welfare_of(price, fld, disp, P: Params):
    J = 0.0
    for t in range(NT):
        p = disp["sl"][t]["p"]
        ab = At_(t)
        c = min(ab / p, CBAR)
        stor = 0.0
        u = fld["u"][t]
        for i in range(NX):
            uxp = (u[i + 1] - u[i]) / HX if i < NX - 1 else 0.0
            uxm = (u[i] - u[i - 1]) / HX if i > 0 else 0.0
            a = _clamp((0.5 * (uxp + uxm) - price[t]) / ETA)
            stor += 0.5 * ETA * a * a * fld["m"][t][i] * HX
        q, d = disp["sl"][t]["q"], disp["sl"][t]["d"]
        J += DT * (ab * math.log(c) - P.phi * stor - 0.5 * GAM * q * q - P.PMAX * d)
    for i in range(NX):
        J += (-KAPT * (XS[i] - XSTAR) ** 2) * fld["m"][NT][i] * HX
    return J


# ---------------- the adjoint-matched (Achdou) scheme ----------------
# Port of sin-mfg/tools/continuum_reference.js: FP = HJBᵀ exactly.

def interface_alpha(u, pt):
    al = [0.0] * (NX + 1)
    for f in range(1, NX):
        s = (u[f] - u[f - 1]) / HX
        al[f] = _clamp((s - pt) / ETA)
    return al


def _hjb_coeffs(al):
    rd = NU * DT / (HX * HX)
    rh = DT / HX
    A = [0.0] * NX
    B = [0.0] * NX
    C = [0.0] * NX
    for i in range(NX):
        fL = 1 if i > 0 else 0
        fR = 1 if i < NX - 1 else 0
        aLm = min(al[i], 0.0)
        aRp = max(al[i + 1], 0.0)
        A[i] = -rd * fL + rh * aLm
        C[i] = -rd * fR - rh * aRp
        B[i] = 1 + rd * (fL + fR) + rh * (aRp - aLm)
    return A, B, C


def _fp_coeffs(al):
    rd = NU * DT / (HX * HX)
    rh = DT / HX
    A = [0.0] * NX
    B = [0.0] * NX
    C = [0.0] * NX
    for i in range(NX):
        fL = 1 if i > 0 else 0
        fR = 1 if i < NX - 1 else 0
        A[i] = -rd * fL - rh * max(al[i], 0.0)
        C[i] = -rd * fR + rh * min(al[i + 1], 0.0)
        B[i] = 1 + rd * (fL + fR) + rh * (max(al[i + 1], 0.0) - min(al[i], 0.0))
    return A, B, C


def mat_hjb(u, pt):
    A, B, C = _hjb_coeffs(interface_alpha(u, pt))
    return _tri_to_dense(A, B, C)


def mat_fp(u, pt):
    A, B, C = _fp_coeffs(interface_alpha(u, pt))
    return _tri_to_dense(A, B, C)


def _tri_to_dense(A, B, C):
    M = np.zeros((NX, NX))
    for i in range(NX):
        if i > 0:
            M[i, i - 1] = A[i]
        M[i, i] = B[i]
        if i < NX - 1:
            M[i, i + 1] = C[i]
    return M


def transpose_defect(u, pt):
    """|M_FP − M_HJBᵀ| / scale — 0 exactly for this pair (the certificate)."""
    F, H = mat_fp(u, pt), mat_hjb(u, pt)
    return float(np.abs(F - H.T).max() / np.abs(F).max())


def solve_field_upwind(price):
    """Adjoint-matched field solve: single implicit tridiagonal per slice,
    HJB freezing alpha from u^{t+1}, FP from u^t (lab convention)."""
    u = [[0.0] * NX for _ in range(NT + 1)]
    u[NT] = [-KAPT * (XS[i] - XSTAR) ** 2 for i in range(NX)]
    for t in range(NT - 1, -1, -1):
        al = interface_alpha(u[t + 1], price[t])
        A, B, C = _hjb_coeffs(al)
        D = [0.0] * NX
        for i in range(NX):
            aLm = min(al[i], 0.0)
            aRp = max(al[i + 1], 0.0)
            D[i] = u[t + 1][i] + DT * (-(aRp + aLm) * price[t]
                                       - 0.5 * ETA * (aRp * aRp + aLm * aLm))
        u[t] = thomas(A, B, C, D)
    m = [[0.0] * NX for _ in range(NT + 1)]
    m[0] = _m0()
    A_out = [0.0] * NT
    Ux = [0.0] * NT
    for t in range(NT):
        al = interface_alpha(u[t], price[t])
        a, b, c = _fp_coeffs(al)
        m[t + 1] = thomas(a, b, c, list(m[t]))
        # read-out convention: same m-weighted centered gradient as shipped
        uxi = 0.0
        Ai = 0.0
        for i in range(NX):
            uxp = (u[t][i + 1] - u[t][i]) / HX if i < NX - 1 else 0.0
            uxm = (u[t][i] - u[t][i - 1]) / HX if i > 0 else 0.0
            ux = 0.5 * (uxp + uxm)
            uxi += ux * m[t][i] * HX
            Ai += 0.5 * (al[i] + al[i + 1]) * m[t][i] * HX
        Ux[t] = uxi
        A_out[t] = Ai
    return {"u": u, "m": m, "A": A_out, "Ux": Ux}


def solve_field_implicit(price, inner: int = 30, tol: float = 1e-14):
    """Fully-implicit Achdou variant: within each backward slice the interface
    controls are iterated to self-consistency (alpha = alpha(u^t), the SOLVED
    slice), and the FP step uses the SAME controls.

    This is the variant for which the LITERAL discrete-KKT statement holds and
    is certified (``kkt_point_residual``): the semi-implicit staggering of
    ``solve_field_upwind`` (HJB freezing from u^{t+1}, FP from u^t) breaks the
    discrete duality pairing at O(dt) — measured: telescoping 5.4e-3, control
    stationarity ~1e-3 — while the consistent within-slice iteration restores
    both to machine zero (5.6e-17 / FD floor)."""
    u = [[0.0] * NX for _ in range(NT + 1)]
    u[NT] = [-KAPT * (XS[i] - XSTAR) ** 2 for i in range(NX)]
    alphas = [None] * NT
    for t in range(NT - 1, -1, -1):
        al = interface_alpha(u[t + 1], price[t])          # warm start
        ut = u[t + 1]
        for _ in range(inner):
            A, B, C = _hjb_coeffs(al)
            D = [0.0] * NX
            for i in range(NX):
                aL = min(al[i], 0.0)
                aR = max(al[i + 1], 0.0)
                D[i] = u[t + 1][i] + DT * (-(aR + aL) * price[t]
                                           - 0.5 * ETA * (aR * aR + aL * aL))
            ut = thomas(A, B, C, D)
            al2 = interface_alpha(ut, price[t])
            dev = max(abs(al2[f] - al[f]) for f in range(NX + 1))
            al = al2
            if dev < tol:
                break
        u[t] = ut
        alphas[t] = al
    m = [[0.0] * NX for _ in range(NT + 1)]
    m[0] = _m0()
    A_out = [0.0] * NT
    Ux = [0.0] * NT
    for t in range(NT):
        a, b, c = _fp_coeffs(alphas[t])
        m[t + 1] = thomas(a, b, c, list(m[t]))
        uxi = 0.0
        for i in range(NX):
            uxp = (u[t][i + 1] - u[t][i]) / HX if i < NX - 1 else 0.0
            uxm = (u[t][i] - u[t][i - 1]) / HX if i > 0 else 0.0
            uxi += 0.5 * (uxp + uxm) * m[t][i] * HX
        Ux[t] = uxi
        A_out[t] = sum(0.5 * (alphas[t][i] + alphas[t][i + 1]) * m[t][i] * HX
                       for i in range(NX))
    return {"u": u, "m": m, "A": A_out, "Ux": Ux, "alphas": alphas}


def _src_cell(al, pt):
    """Cell running reward at split interface controls — the source term the
    matched HJB uses, paired with the POST-step density in the objective."""
    out = [0.0] * NX
    for i in range(NX):
        aL = min(al[i], 0.0)
        aR = max(al[i + 1], 0.0)
        out[i] = -(aR + aL) * pt - 0.5 * ETA * (aR * aR + aL * aL)
    return out


def discrete_objective(alphas, price):
    """The discrete control objective J of the agent problem under the matched
    FP dynamics: J = sum_t dt.<src_t, m^{t+1}> hx + <Psi, m^{NT}> hx."""
    mv = list(_m0())
    total = 0.0
    for t in range(NT):
        a, b, c = _fp_coeffs(alphas[t])
        mv = thomas(a, b, c, list(mv))
        sc = _src_cell(alphas[t], price[t])
        total += DT * HX * sum(sc[i] * mv[i] for i in range(NX))
    total += HX * sum((-KAPT * (XS[i] - XSTAR) ** 2) * mv[i] for i in range(NX))
    return total


def kkt_point_residual(res, fd_h: float = 1e-6):
    """The literal discrete-KKT certificate at a solved equilibrium of the
    fully-implicit matched scheme (``solve_field_implicit``):

    * ``telescoping`` — |J(alpha*) − <u^0, m^0>|: the exact discrete duality
      identity of the matched pair (FP = HJBᵀ makes it algebraic; any
      staggering breaks it at O(dt)).
    * ``stationarity`` — max |dJ/d alpha_f| by central differences over ALL
      interior (unclamped) interfaces; bounded below by the FD truncation
      floor ~1e-9, NOT by the scheme (the true gradient is zero).
    * ``clamp_sign_violations`` — KKT inequality side at clamped interfaces.
    """
    price = res["price"]
    fld = res["field"]
    if "alphas" not in fld:
        raise ValueError("kkt_point_residual needs a solve_field_implicit field")
    alphas = fld["alphas"]
    J0 = discrete_objective(alphas, price)
    u0m0 = HX * sum(fld["u"][0][i] * fld["m"][0][i] for i in range(NX))
    worst, n_int, n_cl, bad = 0.0, 0, 0, 0
    for t in range(NT):
        for f in range(1, NX):
            a0 = alphas[t][f]
            hi_cl = a0 >= AMAX - 1e-12
            lo_cl = a0 <= -AMAX + 1e-12
            ap = [row[:] for row in alphas]
            ap[t][f] = a0 + fd_h
            am = [row[:] for row in alphas]
            am[t][f] = a0 - fd_h
            g = (discrete_objective(ap, price) - discrete_objective(am, price)) / (2 * fd_h)
            if hi_cl:
                n_cl += 1
                bad += g < -1e-6
            elif lo_cl:
                n_cl += 1
                bad += g > 1e-6
            else:
                n_int += 1
                worst = max(worst, abs(g))
    return {"telescoping": abs(J0 - u0m0), "stationarity": worst,
            "n_interior": n_int, "n_clamped": n_cl, "clamp_sign_violations": bad}


# ---------------- certificate helpers ----------------

def mass_drift(fld):
    worst = 0.0
    for t in range(NT + 1):
        s = sum(fld["m"][t][i] * HX for i in range(NX))
        worst = max(worst, abs(s - 1.0))
    return worst


def min_density(fld):
    return min(min(row) for row in fld["m"])


def clearing_worst(res):
    worst = 0.0
    for t in range(NT):
        s = res["disp"]["sl"][t]
        N = make_n(t, res["field"]["Ux"][t], res["P"])
        worst = max(worst, abs(N(s["p"]) - s["h"] + s["k"] - s["d"]))
    return worst


def budget_error(res):
    P = res["P"]
    tot = sum(s["h"] * DT for s in res["disp"]["sl"])
    if res["disp"]["spill"] > 0:
        return abs(tot + res["disp"]["spill"] - P.EHYD)
    return abs(tot - P.EHYD)


def t3_flatness(res):
    """max |p − w| over hydro-marginal hours (0 < h < HBAR)."""
    worst, nmarg = 0.0, 0
    for s in res["disp"]["sl"]:
        if 1e-9 < s["h"] < HBAR - 1e-9:
            nmarg += 1
            worst = max(worst, abs(s["p"] - res["disp"]["w"]))
    return worst, nmarg
