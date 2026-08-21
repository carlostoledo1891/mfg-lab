#!/usr/bin/env python3
"""test_sensitivity.py — the battery for the sensitivity prober.

THE POINT OF THIS FILE. `sensitivity.py` audits other people's test suites. A tool that judges
suites and has no teeth of its own would be the joke that writes itself, and this whole project
is an argument that a measurement is worth exactly what its controls are worth. So every claim
the prober makes is checked here in BOTH directions: the thing it should catch, and the thing
it must not flag.

THE FAILURE THIS BATTERY EXISTS TO CATCH, stated concretely, because it already happened once
during the build: the mutation engine compile-checks everything it emits, so when it was handed
HumanEval's `canonical_solution` — an INDENTED FRAGMENT that cannot be parsed alone — it
emitted zero mutants, silently. Every item then reported `OUT-OF-SCOPE: no first-order mutant
compiled`, which reads exactly like a finding about the benchmark and was a bug in the prober.
T3 below is that bug, frozen as a regression.

Run: python3 tests/test_sensitivity.py     Exit 0 green, 1 red."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import mutate                      # noqa: E402
import sensitivity                 # noqa: E402

FAILS = []


def check(name, ok, detail=''):
    print(('   PASS  ' if ok else '   FAIL  ') + name + (('   [' + detail + ']') if detail else ''))
    if not ok:
        FAILS.append(name)


# ---------------------------------------------------------------- fixtures
# A tiny self-contained problem in HumanEval's exact shape, so the battery never depends on the
# dataset being present or on network.
# FIXTURE CHOICE IS LOAD-BEARING, and the first attempt here was wrong in an instructive way.
# It used a `clamp(x)` into [0, 10]. Its boundary mutants are GENUINELY EQUIVALENT: `x < 0`
# becomes `x <= 0` and both return 0 at x = 0, because the fall-through returns x anyway. No
# suite on earth can kill those, so the fixture could not reach the threshold no matter how
# good its tests were, and T2 failed against a prober that was working correctly.
#
# That is the equivalent-mutant problem this project cannot fully solve (see mutate.py
# `equivalent_guard`), and a battery must not be built on top of it. This fixture is chosen so
# every mutation site is OBSERVABLE: the two branches return different values for the same
# inputs, so flipping the comparison or either operator changes an answer the suite can see.
GOOD_SUITE = {
    'task_id': 'FIXTURE/strong',
    'entry_point': 'score',
    'prompt': 'def score(a, b):\n    """Return a*b when a > b, otherwise a+b."""\n',
    'canonical_solution': '    if a > b:\n        return a * b\n    return a + b\n',
    # a>b, a==b (where >= vs > diverges: 9 vs 6), a<b — plus values where * and + differ.
    'test': ('def check(candidate):\n'
             '    assert candidate(5, 2) == 10\n'
             '    assert candidate(3, 3) == 6\n'
             '    assert candidate(2, 5) == 7\n'
             '    assert candidate(4, 1) == 4\n'
             '    assert candidate(1, 4) == 5\n'),
}

# Same problem, same gold solution, DELIBERATELY THIN suite: a single case from ONE branch.
# It exercises a > b and the `*`, so it can catch the arithmetic mutant there — and it never
# reaches the `+` branch, and it never tests a == b where `>` and `>=` diverge. A thin suite is
# not a suite that catches nothing; it is one that catches the obvious and misses the boundary,
# which is exactly the shape this whole project is about.
WEAK_SUITE = dict(GOOD_SUITE, task_id='FIXTURE/weak',
                  test='def check(candidate):\n    assert candidate(5, 2) == 10\n')

# A suite that asserts nothing at all. `return None` passes it.
VACUOUS_SUITE = dict(GOOD_SUITE, task_id='FIXTURE/vacuous',
                     test='def check(candidate):\n    pass\n')

# A reference solution that RUNS but is wrong — it ignores the branch and always adds. It must
# read as OUT-OF-SCOPE (the reference is broken) and never as a verdict about the suite. Note
# it fails by a wrong ANSWER, not by an exception: a NameError here would exercise a different
# path and would not prove the gold control catches genuine wrongness.
BROKEN_GOLD = dict(GOOD_SUITE, task_id='FIXTURE/brokengold',
                   canonical_solution='    return a + b\n')


print('== evidence-first: sensitivity prober battery ==')
print('   every assertion below is checked in both directions\n')

# ---------------------------------------------------------------- T1: mutants are real
src = GOOD_SUITE['prompt'] + GOOD_SUITE['canonical_solution']
ms = list(mutate.mutants(src))
check('T1 the engine produces mutants from a complete function', len(ms) > 0, f'{len(ms)} mutants')

# T1b — every emitted mutant COMPILES. A mutant that will not compile measures the prober.
all_compile = True
for _, _, m in ms:
    try:
        compile(m, '<t>', 'exec')
    except SyntaxError:
        all_compile = False
check('T1b every emitted mutant compiles', all_compile)

# T1c — every emitted mutant DIFFERS from the original. An identical "mutant" is an
# automatic survivor and would slander the suite.
check('T1c no emitted mutant is textually identical to the original',
      all(m.strip() != src.strip() for _, _, m in ms))

# ---------------------------------------------------------------- T2: teeth, both directions
strong = sensitivity.assess(GOOD_SUITE)
weak = sensitivity.assess(WEAK_SUITE)

check('T2 a suite with boundary coverage is SENSITIVE',
      strong['disposition'] == 'SENSITIVE',
      f"{strong['disposition']} {strong['killed']}/{strong['mutants']}")

check('T2b THE SAME gold with a one-assertion suite is NOT sensitive',
      weak['disposition'] in ('INSENSITIVE', 'VACUOUS'),
      f"{weak['disposition']} {weak['killed']}/{weak['mutants']}")

# The decisive comparison: identical solution, identical mutants, different suite. If these
# two came out the same, the prober would be measuring the SOLUTION rather than the SUITE —
# which is the one thing it must never do.
# Guarded against None on both sides: an OUT-OF-SCOPE item reports kill_rate None, and
# comparing None with `>` raises TypeError — which would abort the battery mid-run and leave
# the remaining assertions unreported. A battery that dies is not a battery that passed.
check('T2c the two verdicts differ on identical code (it measures the SUITE, not the solution)',
      strong['kill_rate'] is not None and weak['kill_rate'] is not None
      and strong['kill_rate'] > weak['kill_rate'],
      f"strong {strong['kill_rate']} vs weak {weak['kill_rate']}")

# ---------------------------------------------------------------- T3: the regression
# The bug that shipped during the build: a body fragment cannot be parsed, so zero mutants were
# emitted and the item was reported OUT-OF-SCOPE as though the BENCHMARK were at fault.
frag = GOOD_SUITE['canonical_solution']
check('T3 a bare indented body yields no mutants (the bug that reported a prober fault as a benchmark finding)',
      len(list(mutate.mutants(frag))) == 0)
check('T3b the complete function does yield mutants — so assess() must be handed the whole function',
      len(list(mutate.mutants(GOOD_SUITE['prompt'] + frag))) > 0)

# ---------------------------------------------------------------- T4: the controls fire
vac = sensitivity.assess(VACUOUS_SUITE)
check('T4 a suite that asserts nothing is VACUOUS, not merely insensitive',
      vac['disposition'] == 'VACUOUS', vac['disposition'])
check('T4b the null control is what caught it', vac.get('null_killed') is False)

bad = sensitivity.assess(BROKEN_GOLD)
check('T5 a wrong reference solution is OUT-OF-SCOPE, never a suite verdict',
      bad['disposition'] == 'OUT-OF-SCOPE' and bad['gold_passes'] is False,
      bad['disposition'])

# ---------------------------------------------------------------- T6: no silent zero
# A 0/0 kill rate must never be reported as a rate. This is the "0 mismatches after a skipped
# comparison" defect, which this tree has paid for more than once.
check('T6 an item with no mutants reports kill_rate None, never 0.0',
      bad['kill_rate'] is None)

print()
if FAILS:
    print(f'FAILED {len(FAILS)} of the assertions above: ' + ', '.join(FAILS))
    sys.exit(1)
print('ALL PASS — the prober measures the suite, and every control was observed firing')
sys.exit(0)
