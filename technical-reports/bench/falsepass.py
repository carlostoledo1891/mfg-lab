#!/usr/bin/env python3
"""falsepass.py — how often does an item's test suite accept a PLAUSIBLE WRONG answer?

THE QUESTION, and why it is sharper than Path A's. Path A mutated the gold solution mechanically
(flip a comparison, offset a constant) and asked whether the suite noticed. That is a proxy: real
model failures are not sign flips, they are plausible-looking solutions with a wrong edge case.
This file uses realistic wrong answers instead — solutions written to look correct and to fail on
one specific input — and asks the same question. A suite that catches sign flips but accepts a
plausible off-by-one is weaker than Path A alone would suggest.

THE CONTROL THAT MAKES IT A MEASUREMENT. A "false pass" only means something if the candidate is
genuinely wrong. Establishing that against the suite would be circular — the suite is the thing
under audit — so each candidate ships a WITNESS CALL: an expression where its author claims the
solution diverges from correct behaviour. The witness is evaluated twice, once against the gold
solution and once against the candidate:

    gold(witness) != candidate(witness)   ->  genuinely wrong. Proceed.
    gold(witness) == candidate(witness)   ->  DISCARDED, not counted either way.

The discard branch is the honest one and it is load-bearing: without it, a candidate that is
secretly correct would sail through the suite and be recorded as a false pass, manufacturing
exactly the scandal this project exists to avoid. Discards are reported as their own number.

THE FOUR OUTCOMES, per item:
    CAUGHT        genuinely wrong, and the suite failed it. The suite did its job.
    FALSE-PASS    genuinely wrong, and the suite PASSED it. A model producing this answer
                  would score a pass on a wrong solution.
    UNPROVEN      the witness did not separate candidate from gold. Nothing concluded.
    ERROR         the candidate or the witness would not run. Excluded from both denominators.

Stdlib only. No network. Python 3.9+."""

import glob
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sensitivity import _run  # noqa: E402

WITNESS_TIMEOUT_MARKER = '__EFB_RESULT__'


def load_problems():
    path = os.path.join(HERE, 'data', 'HumanEval.jsonl.gz')
    return {json.loads(l)['task_id']: json.loads(l) for l in gzip.open(path, 'rt')}


def _witness_value(function_src, witness_call):
    """Evaluate `witness_call` against `function_src` in a subprocess; return (ok, repr).

    Subprocess for the same three reasons the mutation runner uses one: a candidate can hang,
    can call sys.exit, and can leave global state behind. `repr` is compared rather than the
    object so that an unhashable or unorderable return value still compares cleanly."""
    program = (
        function_src + '\n\n'
        'import sys\n'
        'try:\n'
        f'    __v = {witness_call}\n'
        f'    sys.stdout.write({WITNESS_TIMEOUT_MARKER!r} + repr(__v))\n'
        'except Exception as __e:\n'
        f'    sys.stdout.write({WITNESS_TIMEOUT_MARKER!r} + "RAISED:" + type(__e).__name__)\n'
    )
    import subprocess, tempfile  # noqa: E401 — local, mirrors sensitivity._run
    fd, path = tempfile.mkstemp(suffix='.py')
    try:
        with os.fdopen(fd, 'w') as fh:
            fh.write(program)
        try:
            proc = subprocess.run([sys.executable, path], capture_output=True,
                                  timeout=10, text=True)
        except subprocess.TimeoutExpired:
            return False, 'TIMEOUT'
        out = proc.stdout
        if WITNESS_TIMEOUT_MARKER not in out:
            return False, 'NO_RESULT'
        return True, out.split(WITNESS_TIMEOUT_MARKER, 1)[1]
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def assess(problem, candidate):
    """One item. Returns a record; never raises."""
    code = candidate.get('wrong_code') or ''
    witness = (candidate.get('witness_call') or '').strip()
    if not code.strip() or not witness:
        return {'outcome': 'ERROR', 'why': 'candidate missing wrong_code or witness_call'}

    gold_src = problem['prompt'] + problem['canonical_solution']

    ok_g, val_g = _witness_value(gold_src, witness)
    ok_c, val_c = _witness_value(code, witness)
    if not ok_g or not ok_c:
        return {'outcome': 'ERROR',
                'why': f'witness would not evaluate (gold={val_g!r}, candidate={val_c!r})'}

    # A witness that RAISES THE SAME EXCEPTION on both sides did not exercise anything — the
    # call itself is broken (undefined name, wrong arity, bad literal). Scoring that as UNPROVEN
    # would conflate two different diagnoses: "the candidate may be secretly correct" and "the
    # probe never ran". Caught by the fixture test in tests/, where a witness referencing an
    # undefined variable was scoring UNPROVEN instead of ERROR and would have quietly inflated
    # the apparent number of testable candidates.
    if val_g == val_c and val_g.startswith('RAISED:'):
        return {'outcome': 'ERROR',
                'why': f'witness raised {val_g[7:]} on BOTH gold and candidate — the call is '
                       f'broken, so nothing was probed',
                'witness': witness}

    if val_g == val_c:
        return {'outcome': 'UNPROVEN', 'why': 'witness did not separate candidate from gold',
                'gold': val_g, 'candidate': val_c}

    # Genuinely wrong. Now: does the item's OWN suite notice?
    program = code + '\n\n' + problem['test'] + f"\n\ncheck({problem['entry_point']})\n"
    failed, reason = _run(program)
    return {
        'outcome': 'CAUGHT' if failed else 'FALSE-PASS',
        'why': reason,
        'gold_at_witness': val_g,
        'candidate_at_witness': val_c,
        'witness': witness,
        'bug': candidate.get('bug'),
    }


def main():
    mask_path = os.path.join(HERE, 'data', 'sensitivity.json')
    mask = ({r['task_id']: r['disposition'] for r in json.load(open(mask_path))['records']}
            if os.path.exists(mask_path) else {})

    problems = load_problems()
    candidates = {}
    for path in sorted(glob.glob(os.path.join(HERE, 'data', 'wrong', '*.json'))):
        try:
            candidates.update(json.load(open(path)))
        except Exception as e:                                  # noqa: BLE001
            print(f'   WARNING unreadable {os.path.basename(path)}: {e}', file=sys.stderr)

    if not candidates:
        print('REFUSING: no candidates under data/wrong/. Nothing to measure.', file=sys.stderr)
        return 2

    print('== evidence-first: FALSE-PASS RATE ==')
    print(f'   {len(candidates)} plausible-wrong candidate(s) over {len(problems)} items')
    print('   a candidate counts only once a WITNESS proves it differs from the gold solution\n')

    # A DROP THAT NOBODY COUNTS IS A SHRINKING DENOMINATOR — added 2026-08-09.
    # `continue` here removes a candidate from `records`, and the rate below is computed over a
    # subset of `records`. The summary prints `candidates` (164 today) and `proven_wrong`, and both
    # are honest; what was never computed is the difference between them caused by THIS line. If
    # the problems file ever loaded partially, `candidates` would still print whole while the base
    # of the rate quietly shrank — the eval-harness form of a vacuous pass (antecedent failure;
    # Beer, Ben-David, Eisner & Rodeh 2001). Measured today: 164 of 164 matched, 0 dropped. The
    # shape was latent, not live, and it is closed here rather than left for the day it is not.
    records = {}
    unmatched = []
    for tid, cand in candidates.items():
        if tid not in problems:
            unmatched.append(tid)
            continue
        records[tid] = assess(problems[tid], cand)
    if unmatched:
        print(f'   WARNING {len(unmatched)} candidate(s) name a task_id absent from the problem '
              f'set and are NOT in any figure below: {", ".join(sorted(unmatched)[:5])}'
              f'{" ..." if len(unmatched) > 5 else ""}', file=sys.stderr)

    counts = {}
    for r in records.values():
        counts[r['outcome']] = counts.get(r['outcome'], 0) + 1

    proven = [t for t, r in records.items() if r['outcome'] in ('CAUGHT', 'FALSE-PASS')]
    false_pass = [t for t, r in records.items() if r['outcome'] == 'FALSE-PASS']
    rate = len(false_pass) / len(proven) if proven else None

    # Cross-tab against Path A's mechanical verdict — the interesting comparison.
    crosstab = {}
    for t in proven:
        key = (mask.get(t, 'UNKNOWN'), records[t]['outcome'])
        crosstab[f'{key[0]} / {key[1]}'] = crosstab.get(f'{key[0]} / {key[1]}', 0) + 1

    summary = {
        'candidates': len(candidates),
        'candidates_unmatched_to_a_problem': len(unmatched),
        'scored_base': len(records),
        'outcomes': counts,
        'proven_wrong': len(proven),
        'false_passes': len(false_pass),
        'false_pass_rate': round(rate, 4) if rate is not None else None,
        'false_pass_task_ids': false_pass,
        'crosstab_pathA_disposition_vs_outcome': crosstab,
        'what_this_measures': (
            'Of the candidates PROVEN wrong by an independent witness, the fraction whose own '
            'test suite accepted them anyway. A model that produced one of these answers would '
            'be scored as passing a problem it got wrong.'),
        'why_unproven_is_discarded': (
            'A candidate whose witness does not separate it from the gold solution has not been '
            'shown to be wrong. Counting it as a false pass would manufacture the very result '
            'this measurement exists to test for, so it is excluded from both denominators and '
            'reported separately.'),
        'limits': (
            'Candidates were written by a model asked to introduce a subtle bug; they are '
            'realistic but not a random sample of real model errors. One candidate per item. '
            'The witness proves wrongness at a single input, which is sufficient for "wrong" '
            'and says nothing about how wrong.'),
    }

    out = os.path.join(HERE, 'data', 'falsepass.json')
    json.dump({'summary': summary, 'records': records}, open(out, 'w'), indent=2)

    print('=' * 66)
    for k in ('CAUGHT', 'FALSE-PASS', 'UNPROVEN', 'ERROR'):
        if k in counts:
            print(f'   {k:12s} {counts[k]:4d}')
    print('=' * 66)
    if rate is not None:
        print(f'\n   FALSE-PASS RATE: {len(false_pass)}/{len(proven)} = {rate*100:.1f}%')
        print(f'   {len(false_pass)} item(s) accepted a solution PROVEN wrong by witness.')
    if crosstab:
        print('\n   vs Path A mechanical mutation:')
        for k in sorted(crosstab):
            print(f'     {k:34s} {crosstab[k]}')
    print(f'\n   wrote {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
