"""pld_regime_test.py — the regime-conditioned PLD test (A2's regime map
against real data).

The model's claim (Prop. A2 / the certificate structure): the price sits at
the band FLOOR exactly when the system is in the curtailment regime
(kappa > 0 <=> energy is being cut). ONS supplies the real regime state
(hourly NE constrained-off energy, COFF); CCEE supplies the real
hourly PLD. This tests the COINCIDENCE — a far sharper falsifiable claim
than the martingale non-rejection, though still under the administered-price
caveat (PLD is the capped CMO of the official model, not a market price).

Data: pld-data/pld_horario_2025.csv (CCEE, ';', MES_REFERENCIA+DIA+HORA —
inspected before parsing) and pld-data/ons/coff_index.json (built from the
ONS COFF series: hourly NE COFF, GWh, for months 01/05/06/09 of 2025).

Usage: python3 sin-mfg/tests/pld_regime_test.py
Prints the contingency table and rates; exits 1 if data files are absent
(a skipped test is not a pass — but this is an analysis script, its numbers
are recorded in FINDINGS_SIN, not gated in make check).
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLD = ROOT / "pld-data" / "pld_horario_2025.csv"
COFF = ROOT / "pld-data" / "ons" / "coff_index.json"
MONTHS = {"01", "05", "06", "09"}          # the months the COFF index covers
COFF_EPS = 0.05                            # GWh/h — below this, "no cut" (noise floor)

if not PLD.exists() or not COFF.exists():
    print("DATA ABSENT — test DID NOT run (need CCEE pld_horario_2025 + ONS coff_index)")
    sys.exit(1)

pld = {}                                    # (date, hour) -> R$/MWh
with open(PLD, encoding="utf-8") as fh:
    for row in csv.DictReader(fh, delimiter=";"):
        if row["SUBMERCADO"] != "NORDESTE":
            continue
        mes = row["MES_REFERENCIA"]        # YYYYMM
        if mes[:4] != "2025" or mes[4:6] not in MONTHS:
            continue
        date = f"2025-{mes[4:6]}-{int(row['DIA']):02d}"
        pld[(date, int(row["HORA"]))] = float(row["PLD_HORA"])

floor = min(pld.values())
floor_hours = sum(1 for v in pld.values() if abs(v - floor) < 0.005)
print(f"NE hourly PLD, months {sorted(MONTHS)}: {len(pld)} hours · "
      f"floor detected R$ {floor:.2f} · at-floor hours {floor_hours} "
      f"({100*floor_hours/len(pld):.1f}%)")

coff = json.load(open(COFF))["hourly"]      # date -> [24] GWh
# FIRST RUN FINDING (kept): the binary regime is DEGENERATE — the NE cuts
# something in ~every hour of these months (base rate 1.000), so "any cut"
# carries no information. The honest test is MAGNITUDE-conditioned.
at_f, off_f = [], []
for (date, h), p in pld.items():
    c = coff.get(date, [0.0] * 24)[h]
    (at_f if abs(p - floor) < 0.005 else off_f).append(c)
at_f.sort(); off_f.sort()
med = lambda a: a[len(a) // 2] if a else 0.0
mean = lambda a: sum(a) / max(len(a), 1)
print(f"\nhourly COFF magnitude (GW avg):")
print(f"  at floor  (n={len(at_f)}):  mean {mean(at_f):.2f}  median {med(at_f):.2f}  p90 {at_f[int(.9*len(at_f))]:.2f}")
print(f"  off floor (n={len(off_f)}): mean {mean(off_f):.2f}  median {med(off_f):.2f}  p90 {off_f[int(.9*len(off_f))]:.2f}")
print(f"  ratio of means (floor/off): {mean(at_f)/max(mean(off_f),1e-9):.2f}x")
print("\nP(price at floor | hourly cut > x GW) — the model says this rises:")
base_floor = len(at_f) / (len(at_f) + len(off_f))
for x in (0.0, 0.5, 1.0, 2.0, 4.0, 6.0):
    nf = sum(1 for c in at_f if c > x)
    no = sum(1 for c in off_f if c > x)
    if nf + no == 0:
        break
    print(f"  x = {x:4.1f} GW:  {nf/(nf+no):.3f}   (n={nf+no})")
print(f"  base rate P(floor) = {base_floor:.3f}")
print("\nCaveats (stand in every use): PLD is the administered CMO (capped), "
      "not a market price; COFF covers 4 months; coincidence is not causation; "
      "the model's claim is directional (floor <=> curtailment regime), tested "
      "here as conditional rates, not as a calibrated fit.")
