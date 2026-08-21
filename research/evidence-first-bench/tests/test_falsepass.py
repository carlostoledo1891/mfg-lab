#!/usr/bin/env python3
"""test_falsepass.py — the false-pass scorer's own battery, both directions.

WHY THIS FILE EXISTS. falsepass.py audits other people's test suites. A prober that grades
suites and has no teeth of its own is a joke that writes itself — and this one shipped a
14.7% headline before this battery existed, which is precisely the ordering this project
argues against. The battery is written after the fact and says so.

THE ASSERTION THAT MATTERS is F2 vs F1: the SAME wrong candidate, with the SAME witness, must
score CAUGHT against a thorough suite and FALSE-PASS against a thin one. A scorer that returned
the same verdict for both would be measuring the candidate rather than the suite, which is the
one thing it must never do.

Run: python3 tests/test_falsepass.py     Exit 0 = all pass. Stdlib only."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import falsepass  # noqa: E402

FAILURES = []


def check(label, cond, detail=''):
    print(f'   {"ok  " if cond else "FAIL"}  {label}')
    if not cond:
        FAILURES.append(f'{label}{" — " + detail if detail else ""}')


# ---------------------------------------------------------------------------
# The fixture: last_index(xs, v) -> index of the LAST occurrence, or -1.
# The wrong candidate returns the FIRST occurrence. That is a realistic bug: it is correct
# whenever v appears at most once, which is what a thin suite happens to test.
# ---------------------------------------------------------------------------
PROMPT = 'def last_index(xs, v):\n'
GOLD_BODY = ('    r = -1\n'
             '    for i, x in enumerate(xs):\n'
             '        if x == v:\n'
             '            r = i\n'
             '    return r\n')
WRONG = ('def last_index(xs, v):\n'
         '    for i, x in enumerate(xs):\n'
         '        if x == v:\n'
         '            return i\n'
         '    return -1\n')

THIN_SUITE = ('def check(candidate):\n'
              '    assert candidate([1, 2, 3], 2) == 1\n'
              '    assert candidate([1, 2, 3], 9) == -1\n')
THOROUGH_SUITE = ('def check(candidate):\n'
                  '    assert candidate([1, 2, 3], 2) == 1\n'
                  '    assert candidate([1, 2, 3], 9) == -1\n'
                  '    assert candidate([5, 5, 5], 5) == 2\n')   # the duplicate case


def problem(test):
    return {'prompt': PROMPT, 'canonical_solution': GOLD_BODY,
            'test': test, 'entry_point': 'last_index'}


WITNESS = 'last_index([5, 5, 5], 5)'

print('== falsepass scorer battery ==\n')

# F1 — a genuinely wrong candidate, and a suite that notices.
r = falsepass.assess(problem(THOROUGH_SUITE), {'wrong_code': WRONG, 'witness_call': WITNESS})
check('F1  thorough suite catches the wrong candidate -> CAUGHT',
      r['outcome'] == 'CAUGHT', repr(r))

# F2 — THE DECISIVE ONE. Same candidate, same witness, thinner suite.
r2 = falsepass.assess(problem(THIN_SUITE), {'wrong_code': WRONG, 'witness_call': WITNESS})
check('F2  thin suite accepts the SAME candidate -> FALSE-PASS',
      r2['outcome'] == 'FALSE-PASS', repr(r2))

check('F2c the two verdicts DIFFER — the scorer measures the SUITE, not the candidate',
      r['outcome'] != r2['outcome'],
      f'both returned {r["outcome"]} — scorer is blind to suite strength')

# F3 — the discard branch. A candidate that is secretly CORRECT must never be counted as a
# false pass, however thin the suite. Without this branch the headline number is manufactured.
r3 = falsepass.assess(problem(THIN_SUITE),
                      {'wrong_code': PROMPT + GOLD_BODY, 'witness_call': WITNESS})
check('F3  witness does not separate a correct candidate -> UNPROVEN (never FALSE-PASS)',
      r3['outcome'] == 'UNPROVEN', repr(r3))

# F4 — a broken witness (undefined name) raises the SAME exception on both sides. That is not
# "possibly correct", it is "never probed", and conflating them inflates the testable pool.
r4 = falsepass.assess(problem(THIN_SUITE),
                      {'wrong_code': WRONG, 'witness_call': 'last_index(NOPE, 5)'})
check('F4  witness raising identically on both sides -> ERROR, not UNPROVEN',
      r4['outcome'] == 'ERROR', repr(r4))

# F5 — refuse to score an incomplete candidate rather than guessing.
r5 = falsepass.assess(problem(THIN_SUITE), {'wrong_code': WRONG, 'witness_call': ''})
check('F5  missing witness -> ERROR', r5['outcome'] == 'ERROR', repr(r5))

# F6 — a candidate that does not even run is an ERROR, never a FALSE-PASS. A syntax error
# scored as a pass would be the most embarrassing possible direction for this bug to point.
r6 = falsepass.assess(problem(THIN_SUITE),
                      {'wrong_code': 'def last_index(xs, v)\n  return 0\n',
                       'witness_call': WITNESS})
check('F6  candidate that will not parse -> ERROR, never FALSE-PASS',
      r6['outcome'] == 'ERROR', repr(r6))

print()
if FAILURES:
    print(f'FAILED {len(FAILURES)}:')
    for f in FAILURES:
        print(f'   - {f}')
    sys.exit(1)
print('all falsepass scorer checks passed')
