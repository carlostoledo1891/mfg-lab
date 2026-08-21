# evidence-first-bench — Path A: measuring the evaluator, not the model

**Question this answers, per benchmark item:** *if the reference solution were wrong, would this
item's own test suite notice?*

No model is called. Nothing is scored. The measurement is a property of the **benchmark**, which
is what makes it reusable: the same mask applies to every model you later evaluate, so it
separates *the model could not do it* from *the benchmark could not tell*.

```
gold solution ──► mutate (first-order, semantic) ──► run the item's OWN tests
                                                          │
                              killed / survived ──────────┘
                                       │
                              kill rate per item
                                       │
                    SENSITIVE · INSENSITIVE · VACUOUS · OUT-OF-SCOPE
```

## Result — HumanEval, 164 items, measured 2026-08-08

```
SENSITIVE       151     suite killed a majority of first-order mutants
INSENSITIVE       3     suite let most wrong solutions through
OUT-OF-SCOPE     10     no mutant compiled (a limit of THIS prober, see below)
─────────────────────
mutants     759/853 killed        overall kill rate 0.8898
unfalsifiable  3 of 154 measurable items (1.9%)
```

Reproduce: `python3 sensitivity.py` (31s, no network, no model, stdlib only).

### The concrete instance — HumanEval/35, `max_element`

Its **entire** test suite:

```python
assert candidate([1, 2, 3]) == 3
assert candidate([5, 3, -5, 2, -3, 3, 9, 0, 124, 1, -10]) == 124
```

Change the reference solution's `m = l[0]` to `m = l[1]` and it **passes both assertions**. It is
also broken: `max_element([5])` raises `IndexError`. Verified by running it, not by reading it.

Neither assertion uses a single-element list, so nothing in this item can distinguish the correct
solution from that one. **A model scoring PASS on HumanEval/35 has not been shown to be right.**

## What this does NOT claim

Stated first, because the interesting numbers here are small and the temptation to inflate them
is the exact failure this project exists to name.

- **1.9% is a modest number, not a scandal.** HumanEval's suites are mostly sensitive to these
  operators — 104 of 151 sensitive items killed *every* mutant. The honest headline is that the
  method works and found three real instances, not that the benchmark is broken.
- **HumanEval being weak is already known.** EvalPlus (arXiv:2305.01210) established it and
  responded by *adding ~80× more tests*. This is a different measurement and a different response:
  EvalPlus strengthens the suite until it is sufficient; this **withholds the result** when it is
  not. Their inputs are new; our mutants are wrong *solutions*. The numbers are not comparable and
  should not be presented as though they were.
- **The 10 OUT-OF-SCOPE items are this prober's limit, not a benchmark finding.** All 10 are
  "no mutant compiled" — one-liners with no comparison, arithmetic, boolean or integer literal for
  the operator set to reach. Zero items failed the gold control, so the environment is sound.
- **Equivalent mutants are not fully solved and cannot be.** A mutant that is textually different
  and semantically identical is unkillable, so counting it as a survivor slanders the suite.
  `mutate.py:equivalent_guard` catches only the trivial case. This inflates INSENSITIVE slightly;
  the direction of the error is stated rather than hidden.
- **No claim is made about any model.** Nothing here was run against Claude or anything else.

## Dispositions

| | meaning |
|---|---|
| `SENSITIVE` | killed ≥ 50% of first-order mutants — a result on this item means something |
| `INSENSITIVE` | killed < 50% — a PASS here is not evidence the solution is correct |
| `VACUOUS` | cannot even kill `return None`; the strongest form of insensitive |
| `OUT-OF-SCOPE` | gold fails its own suite, or no mutant compiled — nothing concludable |

The 50% threshold is stated in `sensitivity.py`, printed in every run, and **every per-item kill
rate is written to `data/sensitivity.json`**, so any other threshold can be applied to the same
measurement without re-running it.

## Controls (both directions, or the number is worthless)

- **Gold control** — the unmutated reference must PASS. If it fails, the item is OUT-OF-SCOPE:
  the fault is the reference or the environment, not the suite. *Measured: 0 of 164 failed.*
- **Null control** — `return None` must be KILLED. A suite that cannot kill that is VACUOUS.
- **Compile check** — every emitted mutant compiles. A mutant that fails to parse measures the
  prober, not the suite.
- **No silent zero** — an item with no mutants reports `kill_rate: null`, never `0.0`.

`tests/test_sensitivity.py` proves each of these fires. Its decisive assertion (T2c) runs the
**identical** solution against a strong and a thin suite and requires the verdicts to differ —
1.0 vs 0.333 — because a prober that scored those the same would be measuring the solution
rather than the suite, which is the one thing it must never do.

**Two bugs this battery caught during the build**, both recorded rather than quietly fixed:

1. The engine was handed HumanEval's `canonical_solution`, an *indented fragment* that cannot be
   parsed alone, so it emitted zero mutants and every item reported `OUT-OF-SCOPE`. That reads
   exactly like a benchmark finding and was a fault in the prober. Frozen as T3.
2. The first fixture was a `clamp` whose boundary mutants are **genuinely equivalent** — no suite
   can kill them — so the strong-suite assertion failed against a working prober. Replaced with a
   fixture whose every mutation site is observable, and the reason is written where it happened.

## Path B — rank inversion: a NEGATIVE result, and why

The follow-up experiment was: run several models, drop the unfalsifiable items, and see whether
the leaderboard ordering changes. If two models swap places, the published ordering was partly
measuring benchmark noise.

**It did not, and the reason is worth more than the result would have been.**

```
                answered    raw      certified    unfalsifiable items
opus            164/164     0.994    0.993        passed 3/3
sonnet          164/164     1.000    1.000        passed 3/3

by raw       : sonnet > opus
by certified : sonnet > opus
RANK INVERSION: no
```

Opus missed exactly one item (`HumanEval/38`), which the mask rates `SENSITIVE` — so it counts in
both denominators and moves nothing.

**Why no inversion was detectable, as mechanism rather than luck.** Rank inversion requires the
refused pool to contain items where the models *disagree*. Here the refused pool is **3 items**
and **both models passed all 3**. That is zero discriminating power: removing those items is
arithmetically incapable of reordering anything. Two compounding causes, both measured —
a **ceiling effect** (99–100% in an agent harness leaves no headroom for a reordering to live in)
and a **1.9% refused pool**.

So the experiment is under-powered on this benchmark, and now by a known amount. Detecting rank
inversion needs a benchmark with real headroom *and* a substantial refused pool where models
diverge. That is a sharper argument for SWE-bench Verified than the intuition it started as,
because it is a number.

**Scope limits, stated rather than buried.** These models ran inside an **agent harness** (system
prompt, tools), not as bare API calls, so the absolute rates are not comparable to published
HumanEval scores and are not offered as such. The *between-tier* comparison is valid — identical
harness, identical mask, identical items. One sample per item per model, so there is no
confidence interval; the 0.006 gap is a single problem and is not a ranking.

Reproduce: **Path B is the half that does not ship.** It runs from the two model-calling
harnesses — one through an agent harness, one through the API — over model solutions to HumanEval
items. Those harnesses and the solutions they scored are withheld for the reason in
§*What is published here, and what is not*; the measurement they produced is the table above.

## The false-pass rate — the strongest result here

Path A mutates the gold solution mechanically (flip a comparison, offset a constant). That is a
proxy: real model failures are not sign flips, they are plausible-looking solutions with one wrong
edge case. So the same question was asked with **realistic** wrong answers — solutions written to
look correct and fail on one named input.

**Each candidate ships a WITNESS** — a concrete call where its author claims it diverges from
correct behaviour. The witness is evaluated against both the candidate and the gold solution.
Same value → **discarded**, counted in neither denominator. That branch is load-bearing: without
it, a candidate that is secretly correct would pass the suite and be recorded as a false pass,
manufacturing the exact scandal this project exists to avoid.

```
CAUGHT        139     proven wrong, and the suite failed it
FALSE-PASS     24     proven wrong, and the suite PASSED it
UNPROVEN        1     witness did not separate candidate from gold — discarded

FALSE-PASS RATE: 24/163 = 14.7%
```

**14.7% of HumanEval items accept a solution proven wrong by an independent witness.** A model
that produced one of those answers would be scored as passing a problem it got wrong.

### The cross-tab is the finding

```
                              CAUGHT   FALSE-PASS
SENSITIVE   (Path A: fine)      132        18
INSENSITIVE (Path A: weak)        2         1
OUT-OF-SCOPE                      5         5
```

**18 of the 24 false passes are items Path A rated `SENSITIVE`** — items that killed a majority of
mechanical mutants and got a clean bill of health. So:

> **Mechanical mutation testing overstates test-suite quality.** A suite can reliably kill
> sign-flips and constant-offsets and still accept a plausible off-by-one. Path A found 3
> unfalsifiable items (1.9%); probing with realistic wrong answers finds 24 (14.7%), and 75% of
> those were invisible to mutation.

That is a finding about **mutation testing as a method**, not only about HumanEval — and it is the
one result here that was not predictable in advance. It also revises this unit's own earlier
claim downward in usefulness: Path A's 1.9% is a floor, not an estimate.

**Sharper still: 10 of the 24 killed *every* mutant — a kill rate of exactly 1.00.**

```
HumanEval/7   HumanEval/9   HumanEval/13   HumanEval/19   HumanEval/21
HumanEval/48  HumanEval/53  HumanEval/58   HumanEval/109  HumanEval/152
```

Under mutation testing these are the best-behaved items in the benchmark — a perfect score, nothing
survived. Each then accepted a solution an independent witness proves is wrong. So the claim is not
the hedged *"mutation scores are an imperfect proxy"*; it is the flat one:

> **A perfect mutation score is not evidence that a test suite is sound.**

Falsifiable in one command: `python3 falsepass.py`, then read the kill-rate column for the
FALSE-PASS rows.

Three verified by hand, all passing HumanEval's own tests:

| Item | Bug | Witness | Gold | Wrong |
|---|---|---|---|---|
| `HumanEval/0` | `<=` instead of `<` at the threshold | `has_close_elements([1.0,2.0], 1.0)` | `False` | `True` |
| `HumanEval/7` | matches case-insensitively | `filter_by_substring(['ABC'],'a')` | `[]` | `['ABC']` |
| `HumanEval/9` | seeds running max at `0`, not the first element | `rolling_max([-1,-2])` | `[-1,-1]` | `[0,0]` |

### Limits, stated rather than buried

- Candidates were written by a model **asked** to introduce a subtle bug. They are realistic but
  not a random sample of real model errors, so 14.7% is a rate for *this* adversary, not a
  universal constant.
- **One candidate per item.** A different bug on the same item might well be caught.
- The witness proves wrongness at a **single input**. That is sufficient for "wrong" and says
  nothing about how wrong.
- The agents were told not to look for the test suite — targeting the tests instead of writing a
  realistic bug would invert the measurement. This was an instruction, not an enforced sandbox.
- EvalPlus (arXiv:2305.01210) already established HumanEval's suites are weak, by adding ~80×
  more tests. This is a different measurement (per-item acceptance of wrong *solutions*, not
  added *inputs*) and a different response (withhold the result rather than strengthen the
  suite). The numbers are not comparable and are not presented as if they were.

Reproduce: `python3 falsepass.py` (scores `data/wrong/`, produced by agents from the prompt-only
slices).

**The scorer's own battery is `tests/test_falsepass.py`**, and its decisive assertion (F2c) runs
the **identical** wrong candidate with the **identical** witness against a thorough and a thin
suite, requiring the verdicts to differ — `CAUGHT` vs `FALSE-PASS`. A scorer that returned the
same verdict for both would be measuring the candidate rather than the suite. It also pins the
discard branch (F3: a secretly-correct candidate must never score FALSE-PASS) and three ERROR
paths, including F6 — a candidate that will not parse must be an ERROR, never a false pass.

*Written after the headline number, not before.* This unit shipped 14.7% before its scorer had a
battery, which is the exact ordering the unit argues against. Recorded rather than quietly fixed.

## Where this goes next

**SWE-bench Verified is the real target** and is not runnable here — it needs a Docker container
per task. The prober is deliberately benchmark-shaped rather than HumanEval-shaped: it needs a
gold solution, a test program, and a way to run one against the other. An adapter is the work.

The number worth hunting is not this one. It is **rank inversion**: run several models, drop the
unfalsifiable items, and see whether the leaderboard ordering changes. If two models swap places
once items that cannot tell right from wrong are removed, the published ordering was partly
measuring benchmark noise.

## What is published here, and what is not

**Everything needed to re-run Path A end to end, and to re-derive the three-direction audit from
the recorded measurements, is in this directory:**

```
mutate.py                  AST mutation operators, compile-checked, first-order
sensitivity.py             Path A — the mutation prober + dispositions + controls
falsepass.py               the false-pass scorer — witness-gated, discard branch
verifier_audit.py          the THREE-DIRECTION audit — D1 accepts / D2 rejects constructed /
                           D3 rejects plausible. Reusable beyond HumanEval.
tests/test_sensitivity.py  the mutation prober's battery, both directions
tests/test_falsepass.py    the false-pass scorer's battery (F2c is the decisive one)
tests/test_verifier_audit.py  the audit's battery (V6 freezes a vacuous-degradation bug)
data/HumanEval.jsonl.gz    the dataset (fetched from openai/human-eval)
data/sensitivity.json      full per-item mutation results incl. every kill rate
data/falsepass.json        full per-item witness results + the cross-tab
data/verifier_audit.json   the three-direction table, its bands and its confidence intervals
```

`python3 sensitivity.py` runs the whole of Path A in about 30 seconds on the standard library
alone, and reproduces every number in the Path A section above. `python3 verifier_audit.py` reads
the two result files and reproduces the three-direction table.

**THE WRONG-ANSWER CORPUS IS DELIBERATELY WITHHELD, AND THAT IS THE POINT.** Several hundred of
those files are solutions engineered to pass HumanEval while being wrong. Publishing them would
hand a ready-made contamination set to a benchmark other people still use — so the prober ships
and the wrong answers do not. Withheld with it: the two model-calling harnesses that generated
them and the model solutions they scored, the page generators and their shared design shell, and
one internal design note. Every withheld glob is named, with its reason, in this unit's `.noship`.

**`falsepass.py` therefore cannot run here, and it says so rather than failing oddly** — without a
candidate corpus it prints `REFUSING: no candidates under data/wrong/. Nothing to measure.` and
stops. That is the same rule the rest of this site runs on: refusal is an output. Point it at your
own candidates, in the documented shape, and it will score them.

The report page is generated from the result files above, and every number on it is read out of
the measurement at build time. There is no path by which a figure reaches the page except from the
measurement, so the page cannot drift from the result it reports.
