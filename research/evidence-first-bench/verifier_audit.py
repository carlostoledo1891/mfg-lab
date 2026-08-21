#!/usr/bin/env python3
"""verifier_audit.py — is an automated verifier adequate? Measured in THREE directions.

THE PROBLEM THIS EXISTS FOR. Any benchmark that scores answers automatically rests on a verifier:
a unit-test suite, an exact-answer check, a proof checker, a domain-specific validator. The
verifier is trusted and almost never audited, because auditing it looks circular — the obvious
way to ask "is this verifier right?" is to run it, which is the thing in question.

It is not circular if you separate the directions. A verifier can fail two ways, and they are
independent:

    FALSE NEGATIVE   rejects a solution that is correct   -> the benchmark loses a good answer
    FALSE POSITIVE   accepts a solution that is WRONG     -> the benchmark AWARDS a wrong answer

The second is the expensive one. A false negative costs a retired problem; a false positive means
a model is publicly credited with something it did not do.

THE THREE DIRECTIONS, and why two is not enough:

    D1  ACCEPTS CORRECT        run the reference solution. It must pass.
                               Catches false negatives. Cheap, and the one everybody runs.

    D2  REJECTS CONSTRUCTED-WRONG   break the reference mechanically (flip a comparison, offset a
                               constant) and require rejection. Catches gross false positives.
                               Cheap, automatic, needs no adversary — this is mutation testing.

    D3  REJECTS PLAUSIBLY-WRONG     hand the verifier a solution that LOOKS right and is provably
                               wrong, and require rejection. Catches the false positives that
                               actually occur, because real wrong answers are not sign flips.

D3 needs an independent proof of wrongness or it collapses back into circularity, and that proof
cannot come from the verifier. Here it is a WITNESS: one concrete input where the candidate and
the reference disagree, evaluated against both. If they agree the candidate is not shown to be
wrong and is DISCARDED — counted in no denominator. Without that discard, a secretly-correct
candidate sailing through a weak verifier would be recorded as a false positive, manufacturing
the exact result the audit exists to test for.

THE MEASURED FINDING, and the reason this file is not just bookkeeping: **D2 BARELY predicts D3.**
On HumanEval, of the items whose verifier scored a PERFECT D2 — every constructed-wrong variant
rejected, nothing survived — roughly one in ten still accepted a plausibly-wrong solution. Across
the whole D2 range the D3 failure rate falls only from about a third to under a tenth and never
reaches zero (r is small, negative, and computed rather than asserted).

The wording is deliberate and it CORRECTS AN EARLIER VERSION OF THIS FILE, which claimed D2 "does
not predict" D3 on the strength of a single point at D2 == 1.0. One point cannot separate "D2 is
uninformative" from "D2 helps, but nowhere near enough", and those imply different advice. The
weaker claim is also the more durable one: an absence of relationship dies to one counterexample,
whereas a dose-response curve that never reaches zero says the thing a practitioner needs — D1
plus D2 is not uninformative, it is INSUFFICIENT, at every threshold including a perfect score.
That is a statement about the METHOD and applies to any auto-verified benchmark, not only this one.

REUSE, stated accurately. An earlier version of this paragraph said "supply the four callables
in AuditInputs". THERE IS NO AuditInputs — it was never written, and the sentence described an
interface that does not exist, which is the drift this unit exists to catch. What is true: the
THREE-DIRECTION SHAPE is not HumanEval-specific and applies to any verifier — a proof checker,
an exact-answer comparator, a domain validator. The CODE here is not yet generic: `main()`
reads this unit's own JSON, and `audit_item()` is the only genuinely reusable part. Extracting
a real injection point is unstarted work, not a shipped feature.

Stdlib only. No network. Python 3.9+."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# A verifier is ADEQUATE for an item only if it passes all three directions. The D2/D3 bars are
# stated here, printed in every run, and every per-item rate is written to the JSON — so any
# other threshold can be applied to the same measurement without re-running anything.
D2_BAR = 0.5
D3_BAR = 1.0        # D3 is unforgiving on purpose: ONE accepted wrong answer is the failure.


def audit_item(d1_accepts_gold, d2_rejected, d2_total, d3_rejected, d3_total):
    """Score one verifier on the three directions. Returns a record; never raises.

    A direction with no evidence reports None, never 0.0 — "0 rejected out of 0" reads as total
    failure and is actually silence. That distinction is the defect this tree has paid for more
    than once, so it is structural here rather than a convention."""
    d2 = (d2_rejected / d2_total) if d2_total else None
    d3 = (d3_rejected / d3_total) if d3_total else None

    if not d1_accepts_gold:
        verdict = 'BROKEN'            # rejects its own reference: nothing else is concludable
    elif d3 is not None and d3 < D3_BAR:
        verdict = 'FALSE-POSITIVE'    # the expensive failure, and it is measured
    elif d2 is not None and d2 < D2_BAR:
        verdict = 'WEAK'              # fails even the cheap direction
    elif d3 is None:
        verdict = 'UNAUDITED-D3'      # D1/D2 green and D3 never asked — the blind spot
    else:
        verdict = 'ADEQUATE'

    return {'verdict': verdict, 'd1_accepts_gold': d1_accepts_gold,
            'd2_reject_rate': None if d2 is None else round(d2, 4),
            'd3_reject_rate': None if d3 is None else round(d3, 4),
            'd2_n': d2_total, 'd3_n': d3_total}


def wilson(k, n, z=1.96):
    """95% Wilson score interval for a proportion.

    Wilson rather than the normal approximation because the interesting rates here are small and
    the denominators are in the low hundreds — the regime where `p +/- z*sqrt(p(1-p)/n)` produces
    bounds below zero and quietly implies more precision than the data holds."""
    if not n:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


def pearson(xs, ys):
    """Correlation, or None when it is undefined (fewer than two points, or no variance)."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = sum((a - mx) ** 2 for a in xs)
    sy = sum((b - my) ** 2 for b in ys)
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / ((sx * sy) ** 0.5)


# The dose-response bins. Stated here and printed, so the shape of the curve is not an artefact
# of a boundary chosen after seeing the answer.
CURVE_BINS = [(0.0, 0.5), (0.5, 0.75), (0.75, 0.9), (0.9, 1.0), (1.0, 1.01)]


def load(name):
    with open(os.path.join(HERE, 'data', name)) as fh:
        return json.load(fh)


def main():
    try:
        sen, fp = load('sensitivity.json'), load('falsepass.json')
    except FileNotFoundError as e:
        print(f'REFUSING: {e.filename} missing. Run sensitivity.py and falsepass.py first — '
              f'this file composes their measurements and measures nothing on its own.',
              file=sys.stderr)
        return 2

    mask = {r['task_id']: r for r in sen['records']}
    fprec = fp['records']

    rows = {}
    for tid, m in mask.items():
        # FIELD NAMES ARE READ FROM THE RECORD, NOT GUESSED. The first version of this loop asked
        # for 'mutants_killed'/'mutants_total'/'gold_failed' — none of which exist; the real keys
        # are 'killed'/'mutants'/'gold_passes'. Every .get() returned None, D2 was computed as
        # 0/0 -> None for all 164 items, and the audit still printed a full green-looking table
        # driven entirely by D3. It was caught only because the D2-vs-D3 headline reported
        # "0 verifiers with a perfect D2 score" when 103 was the known answer. That is this
        # file's own subject turned on itself: a measurement that silently degrades to vacuous
        # is worse than one that fails, which is why the headline is computed from a number
        # known in advance and why no direction may report 0.0 where it means "no evidence".
        killed, total = m.get('killed'), m.get('mutants')
        d1 = m.get('gold_passes', False)
        r = fprec.get(tid)
        if r and r['outcome'] in ('CAUGHT', 'FALSE-PASS'):
            d3_n, d3_rej = 1, (1 if r['outcome'] == 'CAUGHT' else 0)
        else:
            d3_n, d3_rej = 0, 0
        rows[tid] = audit_item(d1, killed or 0, total or 0, d3_rej, d3_n)

    # ---- the headline: does D2 predict D3? ----------------------------------------------
    audited = {t: r for t, r in rows.items() if r['d3_n']}
    perfect_d2 = {t: r for t, r in audited.items() if r['d2_reject_rate'] == 1.0}
    perfect_and_failed = {t: r for t, r in perfect_d2.items() if r['verdict'] == 'FALSE-POSITIVE'}
    passed_d2 = {t: r for t, r in audited.items()
                 if r['d2_reject_rate'] is not None and r['d2_reject_rate'] >= D2_BAR}
    passed_and_failed = {t: r for t, r in passed_d2.items() if r['verdict'] == 'FALSE-POSITIVE'}

    counts = {}
    for r in rows.values():
        counts[r['verdict']] = counts.get(r['verdict'], 0) + 1

    # ---- THE DOSE-RESPONSE CURVE. --------------------------------------------------------
    # Measuring the D2/D3 relationship at the single point D2==1.0 cannot distinguish "D2 is
    # uninformative" from "D2 helps, but not enough" — and those call for different advice. This
    # bins the whole range and reports the correlation, which corrected this file's own earlier
    # claim: the first version of the page asserted "D2 does not predict D3", and r = -0.17 says
    # the weaker and more useful thing, that D2 predicts D3 BARELY. A relationship that is real
    # but far too weak to substitute for measuring D3 is a harder claim to wave away than an
    # absence, because a single counterexample refutes an absence and nothing refutes a curve.
    curve = []
    for lo, hi in CURVE_BINS:
        g = [t for t, r in audited.items()
             if r['d2_reject_rate'] is not None and lo <= r['d2_reject_rate'] < hi]
        if not g:
            continue
        failed = [t for t in g if rows[t]['verdict'] == 'FALSE-POSITIVE']
        curve.append({'d2_lo': lo, 'd2_hi': None if hi > 1 else hi, 'n': len(g),
                      'failed_d3': len(failed),
                      'rate': round(len(failed) / len(g), 4),
                      'ci95': wilson(len(failed), len(g))})

    xs = [r['d2_reject_rate'] for r in audited.values() if r['d2_reject_rate'] is not None]
    ys = [1.0 if rows[t]['verdict'] == 'FALSE-POSITIVE' else 0.0
          for t, r in audited.items() if r['d2_reject_rate'] is not None]
    corr = pearson(xs, ys)

    summary = {
        'items': len(rows),
        'verdicts': counts,
        'd1_gold_control_failures': sum(1 for r in rows.values() if not r['d1_accepts_gold']),
        'd2_overall_reject_rate': sen['summary']['overall_kill_rate'],
        'd3_overall_reject_rate': round(1 - fp['summary']['false_pass_rate'], 4),
        'n_audited_on_d3': len(audited),
        'n_perfect_d2': len(perfect_d2),
        'n_perfect_d2_that_failed_d3': len(perfect_and_failed),
        'perfect_d2_failure_rate': (round(len(perfect_and_failed) / len(perfect_d2), 4)
                                    if perfect_d2 else None),
        'perfect_d2_failure_ci95': wilson(len(perfect_and_failed), len(perfect_d2)),
        'd2_d3_curve': curve,
        'd2_d3_correlation': None if corr is None else round(corr, 4),
        'correlation_n': len(xs),
        'n_passed_d2': len(passed_d2),
        'n_passed_d2_that_failed_d3': len(passed_and_failed),
        'the_finding': (
            'D2 BARELY predicts D3, and the distinction from "does not predict" is deliberate. '
            'The correlation is real, weak and in the expected direction; across the whole D2 '
            'range the D3 failure rate falls only from roughly a third to under a tenth, and it '
            'never reaches zero. So a QA procedure built on D1 + D2 is not uninformative — it is '
            'INSUFFICIENT, at every threshold, including a perfect score. That is the weaker '
            'claim and the more useful one: an absence of relationship dies to one counterexample, '
            'a dose-response curve that never reaches zero does not.'),
        'why_d3_needs_a_witness': (
            'Asking the verifier whether a candidate is wrong is circular, because the verifier '
            'is the thing under audit. The witness breaks the circle: one input where candidate '
            'and reference disagree, evaluated against both. Candidates the witness does not '
            'separate are DISCARDED from every denominator rather than counted as failures.'),
        'limits': (
            'D3 here rests on ONE adversarial candidate per item, written by a model asked to '
            'introduce a subtle bug. It is a lower bound on the false-positive rate for that '
            'adversary and not a universal constant: a stronger adversary would find more, and '
            'a different one might find different items. D2_BAR=%s, D3_BAR=%s.' % (D2_BAR, D3_BAR)),
    }

    out = os.path.join(HERE, 'data', 'verifier_audit.json')
    with open(out, 'w') as fh:
        json.dump({'summary': summary, 'records': rows}, fh, indent=2)

    print('== verifier audit: three directions ==')
    print(f'   {len(rows)} verifier(s) · D2 bar {D2_BAR} · D3 bar {D3_BAR}\n')
    print(f'   D1  accepts correct          {len(rows) - summary["d1_gold_control_failures"]}'
          f'/{len(rows)}   ({100 * (1 - summary["d1_gold_control_failures"] / len(rows)):.1f}%)')
    print(f'   D2  rejects constructed-wrong  {sen["summary"]["mutants_killed"]}'
          f'/{sen["summary"]["mutants_total"]}   ({100 * summary["d2_overall_reject_rate"]:.1f}%)')
    d3_rejected = sum(1 for r in audited.values() if r['verdict'] != 'FALSE-POSITIVE')
    print(f'   D3  rejects plausibly-wrong    {d3_rejected}'
          f'/{len(audited)}   ({100 * summary["d3_overall_reject_rate"]:.1f}%)')
    print('\n   ' + '=' * 62)
    print(f'   Of {len(perfect_d2)} verifiers with a PERFECT D2 score, '
          f'{len(perfect_and_failed)} FAILED D3')
    if perfect_d2:
        print(f'   -> {100 * len(perfect_and_failed) / len(perfect_d2):.1f}% of "perfectly tested" '
              f'verifiers accept a provably wrong answer')
    print('   ' + '=' * 62)
    if corr is not None:
        print(f'   correlation(D2, failed D3) = {corr:+.3f} over n={len(xs)} '
              f'-> weak, real, and nowhere near sufficient\n')
        print('   D2 kill rate      n   failed D3    rate   95% CI')
        for b in curve:
            lbl = f'{b["d2_lo"]:.2f}' if b['d2_hi'] is None else f'{b["d2_lo"]:.2f}-{b["d2_hi"]:.2f}'
            lo, hi = b['ci95']
            print(f'   {lbl:14s} {b["n"]:4d}  {b["failed_d3"]:8d}  {100*b["rate"]:6.1f}%  '
                  f'[{100*lo:.1f}, {100*hi:.1f}]')
        print()
    for k in sorted(counts):
        print(f'   {k:16s} {counts[k]:4d}')
    print(f'\n   wrote {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
