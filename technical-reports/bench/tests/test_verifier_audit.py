#!/usr/bin/env python3
"""test_verifier_audit.py — the three-direction audit's own battery, both directions.

THE ASSERTION THAT MATTERS is V6: run the audit against the real measurement and require the
D2-vs-D3 headline to reproduce a number known independently (103 perfect-D2 verifiers, 10 of
which fail D3). It exists because the first version of verifier_audit.py asked the sensitivity
records for 'mutants_killed'/'mutants_total'/'gold_failed' — fields that DO NOT EXIST; the real
keys are 'killed'/'mutants'/'gold_passes'. Every lookup returned None, D2 degraded to None for
all 164 items, and the audit still printed a complete, plausible, green-looking table driven
entirely by D3. Nothing failed. It was caught only because the headline said "0 verifiers with a
perfect D2 score" where 103 was the known answer.

That is this unit's own subject turned on itself: a measurement that silently degrades to
vacuous is worse than one that crashes, because it reads as a result. V6 is the control that
makes the degradation loud.

Run: python3 tests/test_verifier_audit.py     Exit 0 = all pass. Stdlib only."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import verifier_audit as va  # noqa: E402

FAILURES = []


def check(label, cond, detail=''):
    print(f'   {"ok  " if cond else "FAIL"}  {label}')
    if not cond:
        FAILURES.append(f'{label}{" — " + detail if detail else ""}')


print('== verifier-audit battery ==\n')

# ---- V1-V5: every verdict path fires, and the precedence between them is pinned ----------
r = va.audit_item(True, 10, 10, 1, 1)
check('V1  all three directions green -> ADEQUATE', r['verdict'] == 'ADEQUATE', repr(r))

r = va.audit_item(True, 10, 10, 0, 1)
check('V2  perfect D2 but accepts a plausibly-wrong answer -> FALSE-POSITIVE',
      r['verdict'] == 'FALSE-POSITIVE', repr(r))

r = va.audit_item(True, 1, 10, 1, 1)
check('V3  fails the cheap direction -> WEAK', r['verdict'] == 'WEAK', repr(r))

r = va.audit_item(True, 10, 10, 0, 0)
check('V4  D1/D2 green and D3 never asked -> UNAUDITED-D3, never ADEQUATE',
      r['verdict'] == 'UNAUDITED-D3', repr(r))

r = va.audit_item(False, 10, 10, 1, 1)
check('V5  rejects its own reference -> BROKEN, and BROKEN outranks everything',
      r['verdict'] == 'BROKEN', repr(r))

# The expensive failure must outrank the cheap one: an item that is both WEAK and accepts a
# wrong answer is reported as FALSE-POSITIVE, because that is the finding a reader must act on.
r = va.audit_item(True, 1, 10, 0, 1)
check('V5b a verifier that is both weak AND fooled reports FALSE-POSITIVE, not WEAK',
      r['verdict'] == 'FALSE-POSITIVE', repr(r))

# ---- the no-silent-zero rule ------------------------------------------------------------
r = va.audit_item(True, 0, 0, 0, 0)
check('V7  no evidence reports None, never 0.0 — "0 rejected of 0" is silence, not failure',
      r['d2_reject_rate'] is None and r['d3_reject_rate'] is None, repr(r))

# ---- V8: D2 and D3 are genuinely independent axes ---------------------------------------
hi_d2_lo_d3 = va.audit_item(True, 10, 10, 0, 1)
lo_d2_hi_d3 = va.audit_item(True, 1, 10, 1, 1)
check('V8  D2 and D3 are independent — a verifier can be perfect on one and fail the other',
      hi_d2_lo_d3['verdict'] != lo_d2_hi_d3['verdict'],
      'the two axes collapsed into one verdict, so D3 measures nothing D2 did not')

# ---- V6: THE REGRESSION. The real measurement must reproduce a known-in-advance number. --
sen_p = os.path.join(ROOT, 'data', 'sensitivity.json')
fp_p = os.path.join(ROOT, 'data', 'falsepass.json')
if not (os.path.exists(sen_p) and os.path.exists(fp_p)):
    check('V6  SKIPPED — measurements absent; run sensitivity.py and falsepass.py', True)
else:
    sen = json.load(open(sen_p))
    fp = json.load(open(fp_p))
    mask = {r['task_id']: r for r in sen['records']}

    # Recomputed here from the RAW records, deliberately not by importing the audit's own
    # loop — a regression test that reuses the buggy accessor cannot catch the bug.
    proven = [t for t, r in fp['records'].items()
              if r['outcome'] in ('CAUGHT', 'FALSE-PASS')]
    perfect = [t for t in proven if mask.get(t, {}).get('kill_rate') == 1.0]
    perfect_failed = [t for t in perfect if fp['records'][t]['outcome'] == 'FALSE-PASS']

    check('V6a the D2 axis is POPULATED — kill_rate resolves for most items, not None',
          len(perfect) > 0,
          'zero perfect-D2 items means the field lookup silently degraded again')
    check(f'V6b perfect-D2 cohort reproduces: {len(perfect)} items, {len(perfect_failed)} failed D3',
          len(perfect) == 103 and len(perfect_failed) == 10,
          f'expected 103/10, got {len(perfect)}/{len(perfect_failed)}')

    # And the audit's OWN accessor must agree with the independent recomputation above.
    rows = {}
    for tid, m in mask.items():
        r = fp['records'].get(tid)
        d3_n = 1 if (r and r['outcome'] in ('CAUGHT', 'FALSE-PASS')) else 0
        d3_rej = 1 if (r and r['outcome'] == 'CAUGHT') else 0
        rows[tid] = va.audit_item(m.get('gold_passes', False),
                                  m.get('killed') or 0, m.get('mutants') or 0, d3_rej, d3_n)
    audit_perfect = [t for t, x in rows.items()
                     if x['d3_n'] and x['d2_reject_rate'] == 1.0]
    check('V6c the audit\'s own field access AGREES with the independent recomputation',
          len(audit_perfect) == len(perfect),
          f'audit saw {len(audit_perfect)}, raw records say {len(perfect)} — accessor drifted')

print()
if FAILURES:
    print(f'FAILED {len(FAILURES)}:')
    for f in FAILURES:
        print(f'   - {f}')
    sys.exit(1)
print('all verifier-audit checks passed')
