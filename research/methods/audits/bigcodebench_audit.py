#!/usr/bin/env python3
# audit.py — a free, red-controlled outside-auditor for BigCodeBench, aimed at the SWE-bench play.
# Claimless probe. Pipeline: fetch tasks (HF, JSON) -> run the OFFICIAL test on a candidate solution
# in a subprocess -> verdict by exit code (timeout => INOPERATIVE, never a pass; C6). The audit here
# asks the cheapest false-pass question: does a task's own test ACCEPT a trivially-wrong solution
# (a constant / empty return)? If yes, the test is too weak to catch a degenerate model answer.
#
# WHY THIS EXISTS: SWE-bench's free data cannot reach current models (patches are S3-gated). BigCode-
# Bench's CAN — tasks are public JSON and per-model generations ship as a GitHub release
# (sanitized_calibrated_samples.zip). So this is the reachable rehearsal for the SWE-aimed audit.
#
# SAFETY: this script runs only the benchmark's OWN canonical code and controlled trivial bodies.
# To audit REAL model generations (see RUNBOOK.md) run inside a sandbox/Docker — never exec untrusted
# downloaded code on a bare machine.
import json, subprocess, tempfile, os, re, urllib.request

STD={'math','random','itertools','collections','functools','re','string','datetime','json','heapq',
     'bisect','statistics','decimal','fractions','operator','copy','textwrap'}
TRIVIAL={'return 0':'    return 0','return None':'    return None','return 1.0':'    return 1.0',
         'return []':'    return []','return ""':'    return ""','return {}':'    return {}'}

def fetch_tasks(n=60):
    url=(f"https://datasets-server.huggingface.co/rows?dataset=bigcode%2Fbigcodebench"
         f"&config=default&split=v0.1.4&offset=0&length={n}")
    with urllib.request.urlopen(url, timeout=60) as r:
        return [x['row'] for x in json.load(r)['rows']]

def parselibs(x):
    if isinstance(x,list): return x
    try: return json.loads(str(x).replace("'",'"'))
    except: return []

def run(task, body, test=None, timeout=40):
    src=(task['code_prompt']+body+"\n\n"+(test or task['test'])
         +"\n\nimport unittest\nunittest.main(argv=['x'],verbosity=0)\n")
    with tempfile.NamedTemporaryFile('w',suffix='.py',delete=False) as f: f.write(src); p=f.name
    try:
        r=subprocess.run(['python3',p],capture_output=True,text=True,timeout=timeout)
        return 'PASS' if (r.returncode==0 and r.stderr.strip().split('\n')[-1].startswith('OK')) else 'FAIL'
    except subprocess.TimeoutExpired: return 'INOPERATIVE'
    finally: os.unlink(p)

def audit(tasks):
    stdlib=[t for t in tasks if parselibs(t['libs']) and all(l in STD for l in parselibs(t['libs']))]
    weak=[]
    print(f"stdlib-only tasks under audit: {len(stdlib)}")
    print(f"{'task':16} {'canon':6}  weak? (a trivial body the official test ACCEPTS)")
    for t in stdlib:
        if run(t,t['canonical_solution'])!='PASS':
            print(f"{t['task_id']:16} {'(canon not PASS)':6}"); continue
        acc=[k for k,b in TRIVIAL.items() if run(t,b)=='PASS']
        if acc: weak.append((t['task_id'],acc))
        print(f"{t['task_id']:16} {'PASS':6}  {'WEAK: accepts '+', '.join(acc) if acc else '—'}")
    print(f"\n{len(weak)}/{len(stdlib)} tasks accept a trivial wrong solution.")
    return stdlib, weak

def red_control(task):
    """C10: prove the detector can go red — a weakened test must accept a trivial body."""
    weak_test=("import unittest\nclass TestCases(unittest.TestCase):\n"
               "    def test_it(self):\n        self.assertIsInstance(task_func(), float)\n")
    strong_trivial=run(task,"    return 1.0")                       # expect FAIL
    weak_trivial  =run(task,"    return 1.0", test=weak_test)       # expect PASS
    weak_canon    =run(task,task['canonical_solution'], test=weak_test)  # expect PASS
    ok = strong_trivial=='FAIL' and weak_trivial=='PASS' and weak_canon=='PASS'
    print(f"RED CONTROL on {task['task_id']}: strong+trivial={strong_trivial} (want FAIL), "
          f"weak+trivial={weak_trivial} (want PASS), weak+canon={weak_canon} (want PASS) -> "
          f"{'detector VALID' if ok else 'DETECTOR BROKEN'}")
    return ok

if __name__=='__main__':
    tasks=fetch_tasks(60)
    assert red_control(next(t for t in tasks if t['task_id']=='BigCodeBench/0')), "red control failed"
    print()
    audit(tasks)
