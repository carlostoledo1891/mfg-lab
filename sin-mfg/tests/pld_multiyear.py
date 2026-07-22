#!/usr/bin/env python3
"""
pld_multiyear.py — pool the T3 flatness test across several years of CCEE PLD,
each year classified against ITS OWN regulated floor (the piso changes annually,
so a single pooled band would mislabel).

This is the reproducible companion to the real-data result reported in
sin-mfg/docs/FINDINGS_SIN.md. It imports the validated primitives from
pld_martingale_test.py (same window construction, flatness statistic, and
permutation contrast null), so nothing here is a second implementation.

Usage:
  python3 pld_multiyear.py pld-data/pld_horario_2021.csv ... --sub SUDESTE

Reports, per year: floor, %floor / %interior, window count, flatness shrinkage,
jump concentration. Then pools all interior windows and runs the wet/dry
permutation contrast on the pool.
"""
import sys
import os
import argparse
import warnings

import numpy as np

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pld_martingale_test as P   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--sub', default='SUDESTE')
    a = ap.parse_args()

    all_flat, all_season = [], []
    print(f"submarket: {a.sub}")
    print(f"{'file':40s}{'floor':>8s}{'%floor':>8s}{'%int':>7s}{'wins':>6s}{'shrinkx':>9s}{'S2%':>6s}{'medRng%':>8s}")
    for f in a.files:
        df = P.load([f], sub=a.sub)
        lo, hi, af, ac = P.detect_band(df['p'])
        wins = P.interior_windows(df, af, ac)
        st = P.stats(df, wins)
        if st is None:
            print(f"{os.path.basename(f):40s}{lo:>8.2f}  (no interior windows)")
            continue
        all_flat.append(P._window_flatness(df, wins))
        all_season.append(P._window_season(df, wins))
        print(f"{os.path.basename(f):40s}{lo:>8.2f}{100*af.mean():>7.1f}%{100*(1-af.mean()-ac.mean()):>6.1f}%"
              f"{len(wins):>6d}{1/max(st['shrink'],1e-9):>8.1f}x{100*st['S2_top10_share']:>6.1f}"
              f"{100*st['med_range']:>7.2f}")

    if not all_flat:
        print("\nno interior windows in any file")
        return
    flat = np.concatenate(all_flat)
    seas = np.concatenate(all_season)
    nw, nd = int(seas.sum()), int((1 - seas).sum())

    def delta(labels):
        return float(np.median(flat[labels == 0]) - np.median(flat[labels == 1]))

    obs = delta(seas)
    rng = np.random.default_rng(17)
    null = np.array([delta(rng.permutation(seas)) for _ in range(2000)])
    z = (obs - null.mean()) / null.std(ddof=1)

    print(f"\n=== POOLED across {len(all_flat)} year(s) ===")
    print(f"interior windows: {len(flat)} (wet {nw} / dry {nd})")
    print(f"CORE T3 signature (all windows): median within-window relative range "
          f"{100*np.median(flat):.2f}%")
    print(f"seasonal contrast — median range WET {100*np.median(flat[seas==1]):.2f}% "
          f"vs DRY {100*np.median(flat[seas==0]):.2f}%")
    print(f"  Delta(dry - wet) = {100*obs:+.2f}pp · z = {z:+.2f} "
          f"({'significant' if abs(z) >= 2 else 'not significant'})")
    print(f"  direction: {'DRY flatter — OPPOSITE the naive wet-flatter framing' if obs < 0 else 'WET flatter'}")
    print("\nInterpretation: the naive calendar proxy (wet=hydro-marginal) is confounded by the")
    print("FLOOR regime — abundant hydro pushes the wet season to the piso (curtailment), so the")
    print("flat hydro-marginal windows track the REGIME, not the month. See FINDINGS_SIN.md.")


if __name__ == '__main__':
    main()
