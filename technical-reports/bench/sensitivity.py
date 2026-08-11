#!/usr/bin/env python3
"""sensitivity.py — PATH A: does this benchmark item's own test suite notice a wrong answer?

THE QUESTION, AND WHY IT NEEDS NO MODEL. Standard practice asks "did the model pass the tests?"
This asks something the model is not involved in at all: *if the reference solution were wrong,
would this item's tests fail?* It is answered from the benchmark alone — gold solution, gold
tests, mutation. No model is called, nothing is scored, no leaderboard moves. That is what
makes the resulting mask reusable: it is a property of the BENCHMARK, so the same mask applies
to every model you later evaluate, which separates "the model could not do it" from "the
benchmark could not tell".

THE DISPOSITIONS, per item:
  SENSITIVE      the suite killed enough mutants to have demonstrated it can reject a wrong
                 solution. A model result on this item means something.
  INSENSITIVE    the suite let too many wrong solutions through. A model PASS here is not
                 evidence of correctness — the suite has not shown it would notice otherwise.
  VACUOUS        the suite cannot even kill a solution that ignores the problem entirely
                 (`return None`). The strongest form of insensitive.
  OUT-OF-SCOPE   the gold solution does not pass its own suite, or no mutant compiled. Nothing
                 can be concluded and the item is excluded from every denominator.

WHAT A KILL IS. Nonzero exit from the item's own test program: a failed assertion, an
exception, or a timeout. A timeout counts as killed and is tracked separately, because a mutant
that hangs HAS changed observable behaviour — but if timeouts dominated a result, you would
want to know, so the number is reported rather than folded in.

CONTROLS, BOTH DIRECTIONS (this file refuses to report a rate it has not earned):
  - GOLD control     the unmutated gold must PASS. If it fails, the runner or the environment
                     is broken, not the suite — the item goes OUT-OF-SCOPE rather than
                     contaminating the mask.
  - NULL control     a solution replaced by `return None` must be KILLED. A suite that cannot
                     kill that is vacuous, and saying so is a result.
Without both, a "0% kill rate" is indistinguishable from "the harness never ran the tests".

Stdlib only. No network at run time. Python 3.9+."""

import argparse
import concurrent.futures as futures
import gzip
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mutate import mutants  # noqa: E402

DEFAULT_DATA = os.path.join(HERE, 'data', 'HumanEval.jsonl.gz')

# Derived, not chosen by taste: an item is called SENSITIVE when its suite kills a strict
# majority of first-order mutants. The threshold is stated here, printed in every report, and
# the full per-item kill rate is written to the JSON so any other threshold can be applied to
# the same measurement without re-running it.
SENSITIVE_THRESHOLD = 0.5
TIMEOUT_SECONDS = 10


def load_problems(path):
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rt') as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _program(problem, function_src):
    """The exact program the benchmark itself would run: the complete function + the gold
    tests + the call. Nothing here is invented; `check(entry_point)` is HumanEval's own
    convention.

    `function_src` is the WHOLE function (signature + body), not a body fragment. That
    distinction cost a debugging round and is worth stating: HumanEval's `canonical_solution`
    is an INDENTED FRAGMENT, so `ast.parse` on it alone raises IndentationError and the
    mutation engine — which compile-checks everything it emits — silently produced zero
    mutants. Every item then reported OUT-OF-SCOPE with 'no first-order mutant compiled',
    which reads exactly like a benchmark finding and was in fact a bug here. The gold control
    passed throughout, which is precisely why the controls are worth having: they localised
    the fault to the prober rather than the suite."""
    return (function_src + '\n\n' + problem['test']
            + f"\n\ncheck({problem['entry_point']})\n")


def _run(source):
    """Run one candidate program in a subprocess. Returns (killed, reason).

    Subprocess rather than exec() in-process for three reasons, all of which bit somebody
    before: a mutant can hang (needs a timeout only a process boundary gives), a mutant can
    call sys.exit (which would kill the harness), and a mutant can leave global state behind
    that changes the NEXT item's result."""
    fd, path = tempfile.mkstemp(suffix='.py')
    try:
        with os.fdopen(fd, 'w') as fh:
            fh.write(source)
        try:
            proc = subprocess.run([sys.executable, path], capture_output=True,
                                  timeout=TIMEOUT_SECONDS, text=True)
        except subprocess.TimeoutExpired:
            return True, 'timeout'
        return (proc.returncode != 0), ('exit%d' % proc.returncode if proc.returncode else 'pass')
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def assess(problem, limit_per_operator=3):
    """Measure one item. Returns a record; never raises on a bad item."""
    tid = problem['task_id']
    # The complete, parseable function: signature + docstring + gold body.
    gold_func = problem['prompt'] + problem['canonical_solution']

    # ---- GOLD control ------------------------------------------------------
    gold_killed, gold_reason = _run(_program(problem, gold_func))
    if gold_killed:
        return {'task_id': tid, 'disposition': 'OUT-OF-SCOPE',
                'why': f'gold solution does not pass its own suite ({gold_reason}) — '
                       f'nothing can be concluded about this suite',
                'gold_passes': False, 'mutants': 0, 'killed': 0, 'kill_rate': None}

    # ---- NULL control ------------------------------------------------------
    # The same signature and docstring, with a body that ignores the problem entirely. A suite
    # that cannot kill this has demonstrated nothing about any solution.
    null_killed, _ = _run(_program(problem, problem['prompt'] + '    return None\n'))

    # ---- first-order mutants ----------------------------------------------
    results, timeouts = [], 0
    for op, idx, mutant_func in mutants(gold_func, limit_per_operator):
        killed, reason = _run(_program(problem, mutant_func))
        if reason == 'timeout':
            timeouts += 1
        results.append({'operator': op, 'site': idx, 'killed': killed, 'reason': reason})

    n = len(results)
    if n == 0:
        return {'task_id': tid, 'disposition': 'OUT-OF-SCOPE',
                'why': 'no first-order mutant compiled for this solution — the item cannot be '
                       'probed by this operator set, which is a limit of the prober not the suite',
                'gold_passes': True, 'null_killed': null_killed,
                'mutants': 0, 'killed': 0, 'kill_rate': None}

    killed = sum(1 for r in results if r['killed'])
    rate = killed / n

    if not null_killed:
        disp, why = 'VACUOUS', ('the suite does not even reject `return None` — it cannot be '
                                'evidence of correctness for any solution')
    elif rate >= SENSITIVE_THRESHOLD:
        disp, why = 'SENSITIVE', f'suite killed {killed}/{n} first-order mutants'
    else:
        disp, why = 'INSENSITIVE', (f'suite killed only {killed}/{n} first-order mutants — a '
                                    f'pass here is not evidence the solution is correct')

    return {'task_id': tid, 'disposition': disp, 'why': why,
            'gold_passes': True, 'null_killed': null_killed,
            'mutants': n, 'killed': killed, 'kill_rate': round(rate, 4),
            'timeouts': timeouts, 'detail': results}


def main():
    ap = argparse.ArgumentParser(description='Evidence-first Path A: measure evaluator sensitivity per benchmark item.')
    ap.add_argument('--data', default=DEFAULT_DATA)
    ap.add_argument('--limit', type=int, default=0, help='only the first N problems (0 = all)')
    ap.add_argument('--per-operator', type=int, default=3, help='max mutation sites per operator')
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 4) - 1))
    ap.add_argument('--out', default=os.path.join(HERE, 'data', 'sensitivity.json'))
    args = ap.parse_args()

    problems = load_problems(args.data)
    if args.limit:
        problems = problems[:args.limit]

    print(f'== evidence-first Path A — evaluator sensitivity ==')
    print(f'   {len(problems)} item(s) · {args.jobs} job(s) · '
          f'<= {args.per_operator} site(s)/operator · threshold {SENSITIVE_THRESHOLD} · '
          f'timeout {TIMEOUT_SECONDS}s')
    print('   NO MODEL IS CALLED. This measures the benchmark, not any model.\n')

    t0 = time.time()
    records = []
    with futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(assess, p, args.per_operator): p['task_id'] for p in problems}
        done = 0
        for fut in futures.as_completed(futs):
            records.append(fut.result())
            done += 1
            if done % 20 == 0 or done == len(problems):
                print(f'   {done}/{len(problems)} measured  ({time.time()-t0:.0f}s)')

    records.sort(key=lambda r: int(r['task_id'].split('/')[1]))

    counts = {}
    for r in records:
        counts[r['disposition']] = counts.get(r['disposition'], 0) + 1
    scored = [r for r in records if r['kill_rate'] is not None]
    unfalsifiable = [r for r in records if r['disposition'] in ('INSENSITIVE', 'VACUOUS')]

    total_mut = sum(r.get('mutants', 0) for r in records)
    total_kill = sum(r.get('killed', 0) for r in records)

    summary = {
        'benchmark': os.path.basename(args.data),
        'items': len(records),
        'threshold': SENSITIVE_THRESHOLD,
        'per_operator_cap': args.per_operator,
        'timeout_seconds': TIMEOUT_SECONDS,
        'dispositions': counts,
        'mutants_total': total_mut,
        'mutants_killed': total_kill,
        'overall_kill_rate': round(total_kill / total_mut, 4) if total_mut else None,
        'unfalsifiable_items': len(unfalsifiable),
        'unfalsifiable_fraction': round(len(unfalsifiable) / len(scored), 4) if scored else None,
        'unfalsifiable_task_ids': [r['task_id'] for r in unfalsifiable],
        'elapsed_seconds': round(time.time() - t0, 1),
        'what_this_is_not': (
            'This is not a model score and not a claim that any model is wrong. It measures '
            'whether each item could DISTINGUISH a correct solution from a deliberately broken '
            'one. An item counted unfalsifiable may still have a correct reference solution; '
            'what it lacks is a suite that would have noticed otherwise.'),
    }

    with open(args.out, 'w') as fh:
        json.dump({'summary': summary, 'records': records}, fh, indent=2)

    print('\n' + '=' * 66)
    for d in ('SENSITIVE', 'INSENSITIVE', 'VACUOUS', 'OUT-OF-SCOPE'):
        if d in counts:
            print(f'   {d:14s} {counts[d]:4d}')
    print('=' * 66)
    print(f'   mutants {total_kill}/{total_mut} killed  (overall kill rate '
          f'{summary["overall_kill_rate"]})')
    if summary['unfalsifiable_fraction'] is not None:
        pct = summary['unfalsifiable_fraction'] * 100
        print(f'\n   {len(unfalsifiable)} of {len(scored)} measurable items ({pct:.1f}%) cannot '
              f'distinguish the\n   reference solution from a deliberately broken one. A model '
              f'PASS on those\n   items is not evidence that its answer is correct.')
    print(f'\n   wrote {args.out}   ({summary["elapsed_seconds"]}s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
