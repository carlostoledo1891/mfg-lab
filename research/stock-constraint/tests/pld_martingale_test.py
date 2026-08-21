#!/usr/bin/env python3
"""
pld_martingale_test.py — empirical test of SIN-MFG Proposition B1 (T3)
=======================================================================
PREDICTION (deterministic form): within hydro-marginal windows — contiguous
hours strictly inside the administrative band — the price is pinned to the
water value: flat within windows, jumping only at constraint/regime events;
day-over-day window levels move as (approximately) driftless innovations.

DATA: CCEE Dados Abertos, dataset PLD_HORARIO
      https://dadosabertos.ccee.org.br/dataset/pld_horario
      (hourly PLD per submercado; hourly mean of DESSEM semi-hourly CMO,
      bounded by the yearly floor/cap). Download the CSV(s), pass path(s).

USAGE:
  python3 pld_martingale_test.py --selftest             # validate the pipeline
  python3 pld_martingale_test.py data.csv --sub SE      # run on real data
  python3 pld_martingale_test.py data.csv --pldx-level 180   # anchor w-level

SHARPER PREDICTION, AND WHY IT NEEDS A NULL (B1 rebuild, 2026-07-20)
-------------------------------------------------------------------
Interior-of-band hours are not all hydro-marginal, so a seasonal CONTRAST was
proposed as a sharper test. NOTE (corrected by real data, 2026-07-20): the naive
direction — "wet flatter than dry" — is NOT what the CCEE data shows. Abundant
hydro pushes the WET season to the price FLOOR (curtailment), so genuine
hydro-marginal windows are scarce there; the flat windows track the hydro-
marginal REGIME, not the calendar (the flattest year was the 2021 water crisis).
The contrast machinery below is kept — with its permutation null — but read its
z as measuring a confounded proxy, not a clean seasonal law. See FINDINGS_SIN.md.

The previous version printed a wet/dry table but had NO null for the contrast,
so a wet-vs-dry difference could be neither confirmed nor dismissed — and its
one "seasonal" assertion only checked that the code RAN, not that the prediction
held. (On structureless synthetic data it printed "DRY flatter than WET",
opposite the header, under ALL PASS.) This version adds a PERMUTATION CONTRAST
NULL: window season-labels are shuffled to build a null band for the flatness
difference, giving the wet-vs-dry comparison a z-score. On real data a positive
significant z supports T3; a null or negative z is reported honestly.

The self-test is TWO-ARMED so it validates the pipeline, not a tautology:
  - POWER:       synthetic data with a genuinely noisier dry season must be
                 DETECTED as wet-flatter, in the right direction, z > 2.
  - SPECIFICITY: structureless synthetic data (no seasonal signal) must report
                 NO significant contrast, |z| < 2.
Making the dry season noisier and then asserting wet-flatter would only test the
generator; the specificity arm is what makes the power arm meaningful.

HONESTY NOTES (read before quoting results):
- DESSEM includes unit-commitment, network and ramp constraints the model
  abstracts away: T3 predicts *approximate* flatness with attributable jumps,
  not exactness. The test reports effect sizes against nulls, not a binary.
- The floor/cap are detected empirically (mass points at the extremes); yearly
  regulated values can be passed with --floor/--cap.
- --pldx-level anchors the water-value LEVEL (CCEE PLDx = hydro opportunity
  cost). Pass a scalar reference; the report shows how tightly window levels sit
  around it. A per-day PLDx series (path form) is a documented extension.
"""
import sys
import re
import argparse
import numpy as np
import pandas as pd

# ---------------- loading ----------------
PATTERNS = dict(
    sub=['submercado', 'submarket', 'sub'],
    hour=['hora', 'periodo_comercializacao', 'periodo', 'hour'],
    price=['pld', 'valor', 'preco', 'price'],
    date=['din_instante', 'data', 'dia', 'date', 'mes_referencia'],
)


def find_col(cols, keys):
    low = {c.lower(): c for c in cols}
    for k in keys:
        for cl, orig in low.items():
            if k in cl:
                return orig
    return None


def parse_dates(series):
    """Parse a date/timestamp column, choosing dayfirst by the actual format.

    Hardcoding dayfirst=True (as the previous version did) CORRUPTS ISO
    timestamps — pandas reads '2024-05-01' as day=05/month=01 (Jan 5) and
    '2024-06-29' as NaT. CCEE's din_instante is ISO, so that silently scrambled
    every date. Detect ISO (YYYY-MM-DD…) → dayfirst=False; otherwise assume
    Brazilian DD/MM/YYYY → dayfirst=True; fall back on the NaT rate if the guess
    is wrong."""
    s = series.astype(str).str.strip()
    nonnull = s[s.str.len() > 0]
    sample = nonnull.iloc[0] if len(nonnull) else ''
    iso = bool(re.match(r'^\d{4}-\d{2}-\d{2}', sample))
    dt = pd.to_datetime(s, errors='coerce', dayfirst=not iso)
    if dt.notna().mean() < 0.5:                       # guess was wrong; try the other
        dt = pd.to_datetime(s, errors='coerce', dayfirst=iso)
    return dt


def _read_raw(paths):
    frames = []
    for p in paths:
        df = pd.read_csv(p, sep=None, engine='python', decimal=',')
        if df.shape[1] == 1:   # wrong decimal guess; retry
            df = pd.read_csv(p, sep=None, engine='python')
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _detect(cols):
    return dict(sub=find_col(cols, PATTERNS['sub']), hour=find_col(cols, PATTERNS['hour']),
                price=find_col(cols, PATTERNS['price']), date=find_col(cols, PATTERNS['date']))


def _ccee_cols(cols):
    """Detect CCEE's PLD_HORARIO layout, where the timestamp is SPLIT across
    columns: MES_REFERENCIA (YYYYMM) + DIA (day) + HORA (hour), with the price in
    PLD_HORA. Returns (mes, dia, hora, price) or None. This layout has no single
    date column — the generic detector would wrongly pick DIA (day-of-month) — so
    it needs its own reconstruction path."""
    low = {c.lower(): c for c in cols}
    mes = next((low[c] for c in low if 'mes_referencia' in c or c == 'mes_ref'), None)
    dia = low.get('dia')
    hora = low.get('hora')
    price = next((low[c] for c in low if c in ('pld_hora', 'pld', 'val_pld', 'valor')), None)
    if mes and dia and hora and price:
        return mes, dia, hora, price
    return None


def _ccee_datetime(df, mes, dia, hora):
    base = pd.to_datetime(df[mes].astype(int).astype(str), format='%Y%m')
    return (base + pd.to_timedelta(pd.to_numeric(df[dia]) - 1, unit='D')
                 + pd.to_timedelta(pd.to_numeric(df[hora]), unit='h'))


def inspect(paths, sub=None):
    """Print the CSV schema and the detected column mapping WITHOUT running the
    test. Run this FIRST on real CCEE data: if the four columns are not detected,
    the mapping is wrong and the full run would fail (or worse, mis-parse). Paste
    this output back and the PATTERNS / --floor / --cap can be adjusted before the
    real run — no format mismatch can then fail silently."""
    df = _read_raw(paths)
    m = _detect(df.columns)
    print("=== CSV inspection ===")
    print(f"rows: {len(df)} · columns: {list(df.columns)}")
    print("dtypes:")
    for c in df.columns:
        print(f"    {c}: {df[c].dtype}")
    ccee = _ccee_cols(df.columns)
    if ccee:
        mes, dia, hora, price = ccee
        print(f"\nCCEE PLD_HORARIO layout detected: timestamp = {mes} (YYYYMM) + {dia} + {hora}, "
              f"price = {price}. (Reconstructed timestamp, not a single date column.)")
    print("\ndetected column mapping (must have price + a date/timestamp source):")
    for k, v in m.items():
        print(f"    {k:6s} -> {v if v else ('(CCEE split timestamp)' if ccee else '*** NOT FOUND — adjust PATTERNS ***')}")
    print("\nfirst 3 rows:")
    print(df.head(3).to_string(max_cols=12))
    if m['sub']:
        vals = df[m['sub']].astype(str).str.strip().unique()[:12]
        print(f"\nsubmercado values present: {list(vals)}  (pass the SE/SUDESTE one via --sub)")
    if ccee or (m['price'] and m['date']):
        try:
            out = load(paths, sub)
            print(f"\nparsed OK: {len(out)} hourly rows · "
                  f"{out['t'].min()} .. {out['t'].max()} · "
                  f"price range {out['p'].min():.2f} .. {out['p'].max():.2f}")
            lo, hi, af, ac = detect_band(out['p'])
            print(f"detected band: floor {lo:.2f} · cap {hi:.2f} · "
                  f"at-floor {100*af.mean():.1f}% · at-cap {100*ac.mean():.1f}% "
                  f"(override with --floor/--cap using the year's regulated values)")
        except Exception as e:
            print(f"\nparse FAILED after detection: {e}")
    else:
        print("\n*** price and/or date column not detected — cannot parse. "
              "Add the real column name to PATTERNS at the top of this file. ***")


def load(paths, sub=None, verbose=False):
    df = _read_raw(paths)
    c_sub = find_col(df.columns, PATTERNS['sub'])
    if c_sub and sub:
        df = df[df[c_sub].astype(str).str.upper().str.contains(sub.upper())].copy()

    ccee = _ccee_cols(df.columns)
    if ccee:                                          # CCEE split-timestamp layout
        mes, dia, hora, c_pr = ccee
        if verbose:
            print(f"CCEE PLD_HORARIO layout: date = {mes}+{dia}+{hora}, price = {c_pr}, sub = {c_sub}")
        dt = _ccee_datetime(df, mes, dia, hora)
        pr = pd.to_numeric(df[c_pr], errors='coerce')
    else:
        m = _detect(df.columns)
        c_hr, c_pr, c_dt = m['hour'], m['price'], m['date']
        if verbose:
            print(f"columns detected: sub={c_sub} hour={c_hr} price={c_pr} date={c_dt}")
        if not all([c_pr, c_dt]):
            raise SystemExit(
                "could not find price/date columns.\n"
                f"  columns present: {list(df.columns)}\n"
                f"  detected: {m}\n"
                "  fix: run with --inspect to see the schema, then add the real\n"
                "  column name(s) to PATTERNS at the top of this file.")
        dt = parse_dates(df[c_dt])
        if c_hr is not None and dt.dt.hour.nunique() <= 1:
            hr = pd.to_numeric(df[c_hr], errors='coerce').fillna(0).astype(int)
            dt = dt.dt.normalize() + pd.to_timedelta(hr % 24, unit='h')
        pr = pd.to_numeric(df[c_pr], errors='coerce')

    out = pd.DataFrame({'t': dt, 'p': pr}).dropna().sort_values('t').reset_index(drop=True)
    out = out.groupby('t', as_index=False)['p'].mean()
    return out


# ---------------- band detection ----------------
def detect_band(p, floor=None, cap=None, tol_frac=1e-3):
    lo = floor if floor is not None else np.round(p.min(), 2)
    hi = cap if cap is not None else np.round(p.max(), 2)
    tol = max(tol_frac * hi, 0.02)
    at_floor = p <= lo + tol
    at_cap = p >= hi - tol
    return lo, hi, at_floor, at_cap


# ---------------- window construction ----------------
def interior_windows(df, at_floor, at_cap, min_len=4, event_k=5.0):
    """Contiguous interior hours per day, SPLIT at event-size jumps. T3 predicts
    flat-between-events: an 'event' is an hourly increment larger than
    event_k x the median interior |increment| (principled by the proposition
    itself: jumps occur only at constraint events)."""
    interior = ~(at_floor | at_cap)
    p = df['p'].values
    med_inc = np.median(np.abs(np.diff(p[interior.values]))) if interior.sum() > 3 else 0
    cut = max(event_k * med_inc, 1e-9)
    days = df['t'].dt.normalize()
    wins = []
    for _, idx in df.groupby(days).groups.items():
        idx = np.asarray(idx)
        mask = interior.values[idx]
        start = None
        for j in range(len(idx) + 1):
            ok = j < len(idx) and mask[j] and not (j > 0 and mask[j - 1] and abs(p[idx[j]] - p[idx[j - 1]]) > cut)
            if ok and start is None:
                start = j
            if not ok and start is not None:
                if j - start >= min_len:
                    wins.append(idx[start:j])
                start = j if (j < len(idx) and mask[j]) else None
        if start is not None and len(idx) - start >= min_len:
            wins.append(idx[start:len(idx)])
    return wins


def stats(df, wins):
    p = df['p'].values
    within = [p[w] for w in wins]
    if not within:
        return None
    all_int = np.concatenate(within)
    tot_sd = all_int.std(ddof=1)
    w_sd = np.array([x.std(ddof=1) for x in within])
    w_rng = np.array([(x.max() - x.min()) / max(x.mean(), 1e-9) for x in within])
    R_flat = np.sqrt(np.mean(w_sd ** 2)) / max(tot_sd, 1e-12)
    incs_all = np.abs(np.diff(all_int))
    S1 = np.median(incs_all) / max(np.median(all_int), 1e-9)
    srt = np.sort(incs_all)[::-1]
    k10 = max(1, len(srt) // 10)
    S2 = srt[:k10].sum() / max(srt.sum(), 1e-12)
    incs = np.concatenate([np.diff(x) for x in within if len(x) > 1])
    tdrift = incs.mean() / (incs.std(ddof=1) / np.sqrt(len(incs))) if len(incs) > 3 else np.nan
    means = np.array([x.mean() for x in within])
    dmw = np.diff(means)
    tlevel = dmw.mean() / (dmw.std(ddof=1) / np.sqrt(len(dmw))) if len(dmw) > 3 else np.nan
    rng = np.random.default_rng(42)
    null = []
    for _ in range(200):
        perm = rng.permutation(all_int)
        pos = 0
        ws = []
        for x in within:
            ws.append(perm[pos:pos + len(x)].std(ddof=1))
            pos += len(x)
        null.append(np.sqrt(np.mean(np.array(ws) ** 2)) / tot_sd)
    R_null = float(np.mean(null))
    return dict(n_windows=len(wins), n_hours=len(all_int),
                R_flat=float(R_flat), R_null=R_null,
                shrink=float(R_flat / R_null) if R_null > 0 else np.nan,
                med_range=float(np.median(w_rng)),
                S1_med_inc=float(S1), S2_top10_share=float(S2),
                t_drift_hourly=float(tdrift), t_drift_level=float(tlevel))


def regime_shares(at_floor, at_cap):
    n = len(at_floor)
    return dict(floor=float(at_floor.mean()), cap=float(at_cap.mean()),
                interior=float(1 - at_floor.mean() - at_cap.mean()), n_hours=n)


def report(name, sh, st, pldx_level=None):
    print(f"\n===== {name} =====")
    print(f"hours: {sh['n_hours']} · at floor {100*sh['floor']:.1f}% · interior {100*sh['interior']:.1f}% · at cap {100*sh['cap']:.1f}%")
    if st is None:
        print("no interior windows of sufficient length")
        return
    print(f"windows(>=4h): {st['n_windows']}  covering {st['n_hours']} hours")
    print(f"flatness ratio R = within-sd/total-sd = {st['R_flat']:.3f}   (permutation null: {st['R_null']:.3f}; shrinkage x{1/max(st['shrink'],1e-9):.1f})")
    print(f"median within-window relative range   = {100*st['med_range']:.2f}%")
    print(f"typical hourly move (median|dP|/P)    = {100*st['S1_med_inc']:.2f}%")
    print(f"variation carried by top-10% jumps    = {100*st['S2_top10_share']:.1f}%   (flat-with-jumps signature)")
    print(f"hourly-increment drift t-stat         = {st['t_drift_hourly']:+.2f}   (|t|<2 ~ driftless)")
    print(f"window-level day-over-day drift t     = {st['t_drift_level']:+.2f}")
    verdict = "CONSISTENT with T3" if (st['shrink'] < 0.5 and st['S2_top10_share'] > 0.45 and abs(st['t_drift_hourly']) < 3) else \
              "NOT consistent with T3 (flat-window structure absent)"
    print(f"reading: {verdict}  [effect sizes above; this is not a binary test]")


# ---------------- seasonal contrast with a permutation null ----------------
WET_MONTHS = (12, 1, 2, 3, 4)   # Dec-Apr, southeastern-Brazil wet season


def _window_flatness(df, wins):
    """Per-window relative range (flat = small). The contrast statistic operates
    on these, so permuting the season labels re-uses exactly the same windows."""
    p = df['p'].values
    return np.array([(p[w].max() - p[w].min()) / max(p[w].mean(), 1e-9) for w in wins])


def _window_season(df, wins):
    """1 if a window is in the wet season (by its dominant month), else 0."""
    months = df['t'].dt.month.values
    out = np.zeros(len(wins), dtype=int)
    for i, w in enumerate(wins):
        mo = np.bincount(months[w]).argmax()
        out[i] = 1 if mo in WET_MONTHS else 0
    return out


def seasonal_contrast(df, floor=None, cap=None, event_k=5.0, nperm=500, seed=17):
    """Test the sharper prediction — wet windows flatter than dry — WITH a null.

    Statistic: Delta = median(dry flatness) - median(wet flatness). T3 predicts
    Delta > 0 (dry less flat). The null shuffles the wet/dry labels across
    windows (holding window structure fixed), so it controls for window length
    and count. Returns Delta, z = (Delta - mean_null)/sd_null, and the counts.
    """
    lo, hi, af, ac = detect_band(df['p'], floor, cap)
    wins = interior_windows(df, af, ac, event_k=event_k)
    if len(wins) < 8:
        return None
    flat = _window_flatness(df, wins)
    wet = _window_season(df, wins)
    n_wet, n_dry = int(wet.sum()), int((1 - wet).sum())
    if n_wet < 3 or n_dry < 3:
        return None

    def delta(labels):
        w = flat[labels == 1]
        d = flat[labels == 0]
        return float(np.median(d) - np.median(w))

    obs = delta(wet)
    rng = np.random.default_rng(seed)
    null = np.array([delta(rng.permutation(wet)) for _ in range(nperm)])
    mu, sd = float(null.mean()), float(null.std(ddof=1))
    z = (obs - mu) / sd if sd > 0 else 0.0
    return dict(delta=obs, z=float(z), n_wet=n_wet, n_dry=n_dry,
                wet_flat=float(np.median(flat[wet == 1])),
                dry_flat=float(np.median(flat[wet == 0])))


def stratified(df, floor=None, cap=None):
    """Descriptive wet/dry table + event-threshold sensitivity + the contrast
    null. The header no longer asserts a direction the data may lack; the z-score
    below it is what decides."""
    lo, hi, af, ac = detect_band(df['p'], floor, cap)
    month = df['t'].dt.month
    WET = month.isin(list(WET_MONTHS))
    rows = []
    for name, mask in [('ALL', month > 0), ('WET (Dec-Apr)', WET), ('DRY (May-Nov)', ~WET)]:
        sub = df[mask.values].reset_index(drop=True)
        if len(sub) < 24 * 20:
            rows.append((name, None, None))
            continue
        _, _, af2, ac2 = detect_band(sub['p'], lo, hi)
        st = stats(sub, interior_windows(sub, af2, ac2))
        rows.append((name, regime_shares(af2, ac2), st))
    print("\n--- seasonal stratification (T3 predicts wet flatter than dry — tested by the z below, not asserted) ---")
    print(f"{'stratum':16s} {'hours':>7s} {'floor%':>7s} {'shrinkx':>8s} {'S1':>7s} {'S2':>7s} {'medRange':>9s}")
    for name, sh, st in rows:
        if st is None:
            print(f"{name:16s}  (insufficient data)")
            continue
        print(f"{name:16s} {sh['n_hours']:7d} {100*sh['floor']:6.1f}% "
              f"{1/max(st['shrink'],1e-9):7.1f}x {100*st['S1_med_inc']:6.2f}% "
              f"{100*st['S2_top10_share']:6.1f}% {100*st['med_range']:8.2f}%")
    sc = seasonal_contrast(df, floor, cap)
    if sc is None:
        print("seasonal contrast: insufficient windows in one season")
    else:
        direction = "wet flatter (supports T3)" if sc['delta'] > 0 else "dry flatter (against T3)"
        sig = "SIGNIFICANT" if abs(sc['z']) >= 2 else "not significant"
        print(f"seasonal contrast (permutation null): median-range dry−wet = "
              f"{100*sc['delta']:+.2f}pp · z = {sc['z']:+.2f} ({sig}) · {direction} "
              f"· n_wet {sc['n_wet']} / n_dry {sc['n_dry']}")
    print("\n--- event-threshold sensitivity (pooled) ---")
    print(f"{'k':>4s} {'windows':>8s} {'shrinkx':>8s} {'S2':>7s}")
    for k in (3.0, 5.0, 8.0):
        st = stats(df, interior_windows(df, af, ac, event_k=k))
        print(f"{k:4.0f} {st['n_windows']:8d} {1/max(st['shrink'],1e-9):7.1f}x {100*st['S2_top10_share']:6.1f}%")
    return rows, sc


def pldx_level_report(df, wins, pldx_level):
    """Anchor the water-value LEVEL: how tightly do window means sit around the
    PLDx reference? T3 says window levels approximate the water value, of which
    PLDx (hydro opportunity cost) is CCEE's published proxy."""
    p = df['p'].values
    means = np.array([p[w].mean() for w in wins]) if wins else np.array([])
    if means.size == 0:
        print("pldx-level: no windows")
        return
    rel = np.abs(means - pldx_level) / max(pldx_level, 1e-9)
    within10 = float((rel <= 0.10).mean())
    med_rel = float(np.median(rel))
    print(f"\n--- water-value level anchor (PLDx = {pldx_level:.2f}) ---")
    print(f"window means: median {np.median(means):.2f} · "
          f"median |level−PLDx|/PLDx = {100*med_rel:.1f}% · "
          f"{100*within10:.0f}% of windows within ±10% of PLDx")
    # The median is the honest summary: T3 pins the price to the water value on
    # HYDRO-MARGINAL windows, but evening-peak windows legitimately sit above it,
    # so a minority of windows are far from PLDx by design. The median tracks the
    # hydro-marginal bulk.
    return dict(median_rel=med_rel, within10=within10, n=int(means.size))


# ---------------- synthetic self-test ----------------
def synth(model=True, days=300, seed=7, seasonal=False, w_walk=6.0):
    """Generate a synthetic hourly price series.

    model=True builds the T3-consistent structure (midday floor, rare cap,
    evening ramp = event, flat hydro-marginal). seasonal=True makes the DRY
    season's hydro-marginal genuinely noisier (thermal-margin dilution), so a
    correct pipeline must DETECT wet-flatter; seasonal=False leaves the flat
    part season-independent, so a correct pipeline must find NO contrast.
    w_walk is the daily std of the water-value random walk; w_walk=0 pins the
    water value (used to exercise the --pldx-level anchor, where tracking a
    single reference is only meaningful for a ~stationary water value).
    model=False is the AR(1) negative control (no flat-window structure)."""
    rng = np.random.default_rng(seed)
    rows = []
    w = 150.0
    FLOOR, CAP = 61.07, 816.11
    t0 = pd.Timestamp('2025-01-01')
    for d in range(days):
        w = max(FLOOR + 20, w + rng.normal(0, w_walk))
        month = (t0 + pd.Timedelta(days=d)).month
        is_dry = month not in WET_MONTHS
        # flat-part noise: constant unless seasonal, then dry is ~3x noisier
        sig = (2.4 if is_dry else 0.8) if seasonal else 0.8
        for h in range(24):
            if model:
                if 11 <= h <= 14 and rng.random() < 0.7:
                    p = FLOOR
                elif h in (19, 20) and rng.random() < 0.08:
                    p = CAP
                elif 18 <= h <= 21:
                    p = w * (1.25 + 0.1 * rng.random())
                else:
                    p = w + rng.normal(0, sig)          # hydro-marginal: FLAT
            else:
                p = 0 if (d == 0 and h == 0) else rows[-1][1]
                p = FLOOR + 80 + 0.95 * (p - (FLOOR + 80)) + rng.normal(0, 12)
                p = min(max(p, FLOOR), CAP)
            rows.append((t0 + pd.Timedelta(days=d, hours=h), p))
    return pd.DataFrame(rows, columns=['t', 'p'])


def selftest():
    fails = 0

    def check(name, cond, detail=""):
        nonlocal fails
        print(("PASS  " if cond else "FAIL  ") + name + (f"   [{detail}]" if detail else ""))
        if not cond:
            fails += 1

    # --- positive: T3-structured data must confirm (pooled) ---
    df = synth(model=True, days=300)
    lo, hi, af, ac = detect_band(df['p'])
    st = stats(df, interior_windows(df, af, ac))
    sh = regime_shares(af, ac)
    report("SELF-TEST · model-generated", sh, st)
    check("detects flat-window structure (shrink<0.35)", st['shrink'] < 0.35, f"{st['shrink']:.3f}")
    check("typical move small (S1<2%)", st['S1_med_inc'] < 0.02, f"{100*st['S1_med_inc']:.2f}%")
    check("variation concentrated in jumps (S2>0.5)", st['S2_top10_share'] > 0.5, f"{100*st['S2_top10_share']:.1f}%")
    check("driftless increments (|t|<3)", abs(st['t_drift_hourly']) < 3, f"{st['t_drift_hourly']:+.2f}")
    check("level walk driftless (|t|<3)", abs(st['t_drift_level']) < 3, f"{st['t_drift_level']:+.2f}")
    check("floor regime detected (>5%)", sh['floor'] > 0.05, f"{100*sh['floor']:.1f}%")
    ks = [stats(df, interior_windows(df, af, ac, event_k=k))['shrink'] for k in (3.0, 5.0, 8.0)]
    check("event-threshold robustness (all k confirm, shrink<0.35)", all(x < 0.35 for x in ks),
          " / ".join(f"{x:.3f}" for x in ks))

    # --- seasonal contrast: POWER then SPECIFICITY (the B1 rebuild) ---
    print("\n--- seasonal contrast · POWER (dry genuinely noisier: must detect wet-flatter) ---")
    df_seas = synth(model=True, days=300, seasonal=True)
    sc = seasonal_contrast(df_seas)
    print(f"  Delta(median range, dry−wet) = {100*sc['delta']:+.2f}pp · z = {sc['z']:+.2f} "
          f"· wet {100*sc['wet_flat']:.2f}% vs dry {100*sc['dry_flat']:.2f}%")
    check("POWER: seasonal signal detected in the right direction (Delta>0)", sc['delta'] > 0, f"{100*sc['delta']:+.2f}pp")
    check("POWER: contrast is significant vs the permutation null (z>2)", sc['z'] > 2, f"z={sc['z']:+.2f}")

    print("\n--- seasonal contrast · SPECIFICITY (no seasonal signal: must find none) ---")
    df_flat = synth(model=True, days=300, seasonal=False)
    sc0 = seasonal_contrast(df_flat)
    print(f"  Delta(median range, dry−wet) = {100*sc0['delta']:+.2f}pp · z = {sc0['z']:+.2f}")
    check("SPECIFICITY: no significant contrast when none exists (|z|<2)", abs(sc0['z']) < 2, f"z={sc0['z']:+.2f}")

    # --- pldx-level anchor: exercise it where tracking SHOULD hold (constant
    #     water value). With a walking w the levels are a martingale and do NOT
    #     cluster around one scalar — that is T3, not a failure — so the anchor
    #     is only meaningful over a ~stationary period. This arm checks the
    #     readout detects tight tracking when it exists. ---
    df_stat = synth(model=True, days=120, w_walk=0.0)
    lo2, hi2, af2, ac2 = detect_band(df_stat['p'])
    wins2 = interior_windows(df_stat, af2, ac2)
    means2 = np.array([df_stat['p'].values[w].mean() for w in wins2])
    anchor = float(np.median(means2))
    px = pldx_level_report(df_stat, wins2, anchor)
    check("pldx-level anchor: hydro-marginal windows track a stationary water value (median dev < 5%)",
          px["median_rel"] < 0.05, f"median dev {100*px['median_rel']:.1f}% of anchor {anchor:.1f}")

    # --- negative control: AR(1) must NOT confirm ---
    dfn = synth(model=False)
    lo, hi, af, ac = detect_band(dfn['p'], floor=61.07, cap=816.11)
    stn = stats(dfn, interior_windows(dfn, af, ac))
    report("SELF-TEST · AR(1) negative control", regime_shares(af, ac), stn)
    check("negative control shrink stays moderate (>0.45)", stn['shrink'] > 0.45, f"{stn['shrink']:.3f}")
    check("negative control not jump-concentrated (S2<0.4)", stn['S2_top10_share'] < 0.4, f"{100*stn['S2_top10_share']:.1f}%")

    # --- date-parsing regression: load() must not corrupt ISO timestamps ---
    # (the previous dayfirst=True read '2024-05-01' as Jan 5 and '2024-06-29' as
    # NaT — CCEE's din_instante is ISO, so this would have scrambled the real run)
    iso = parse_dates(pd.Series(['2024-05-01 00:00:00', '2024-06-29 23:00:00']))
    br = parse_dates(pd.Series(['01/05/2024', '29/06/2024']))   # Brazilian DD/MM/YYYY
    check("ISO timestamps parse correctly (2024-05-01 -> May, not Jan)",
          iso.iloc[0].month == 5 and iso.iloc[1].month == 6 and iso.notna().all(),
          str(list(iso.dt.date)))
    check("Brazilian DD/MM/YYYY parses correctly (01/05 -> May)",
          br.iloc[0].month == 5 and br.iloc[1].month == 6 and br.notna().all(),
          str(list(br.dt.date)))

    print(f"\nself-test: {'ALL PASS' if fails == 0 else str(fails) + ' FAILURES'}")
    return fails


# ---------------- main ----------------
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--sub', default='SE')
    ap.add_argument('--floor', type=float)
    ap.add_argument('--cap', type=float)
    ap.add_argument('--pldx-level', type=float, dest='pldx_level',
                    help='water-value anchor (CCEE PLDx / hydro opportunity cost)')
    ap.add_argument('--inspect', action='store_true',
                    help='print the CSV schema + detected column mapping, then exit (run this FIRST on real data)')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest or (not a.files and not a.inspect):
        sys.exit(1 if selftest() else 0)
    if a.inspect:
        inspect(a.files, a.sub)
        sys.exit(0)
    df = load(a.files, a.sub, verbose=True)
    lo, hi, af, ac = detect_band(df['p'], a.floor, a.cap)
    print(f"band detected/used: floor {lo:.2f} · cap {hi:.2f}")
    wins = interior_windows(df, af, ac)
    st = stats(df, wins)
    report(f"PLD_HORARIO · {a.sub}", regime_shares(af, ac), st)
    stratified(df, a.floor, a.cap)
    if a.pldx_level is not None:
        pldx_level_report(df, wins, a.pldx_level)
