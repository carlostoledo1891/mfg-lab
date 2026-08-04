# Expected outputs — fellows-pack CI contract

Golden files are bit-stable for offline fixtures. Live PGR fields are never
golden-hashed; tag `remeasured:true` instead. `~18k USD` cost_refuse stays REFUSED.

| Command | Exit | Must contain |
|---|---|---|
| `python tools/dual_client.py --fixture heldout-ccs-es` | 0 | `disposition.verdict=CERTIFIED`, `disagreement.kind=agree_with_teeth`, `cost_refuse.status=REFUSED`, `pgr.mode=reported` |
| `python tools/dual_client.py --fixture heldout-ccs-es --plant-mutant` | 0 | `disposition.verdict=REFUSED`, `disagreement.kind=disagree` |
| `python tools/volume_runner.py --batch fixtures/volume_batch_100.jsonl` | 0 | `n=100`, `certified + refused = 100`, `mutant_certified=0` |
| `python kernels/disposition_validate.py --pack fixtures/exam-pack.public.json` | 0 | every mutant side ≠ CERTIFIED |
| `W2S_EVAL_URL=… python tools/dual_client.py --post-pgr …` | 0 only if URL set and body real | live `pgr` fields; never silent fake |
| `--post-pgr` without `W2S_EVAL_URL` | ≠0 | error names `W2S_EVAL_URL` |

## Golden files

| File | Role |
|---|---|
| `golden/dual_client_heldout.json` | Offline dual-eval held-out fixture |
| `golden/volume_batch_100.summary.json` | Offline volume summary (`n=100`, `mutant_certified=0`) |
| `golden/plant_mutant.refused.json` | Planted-mutant batch — all REFUSED, `mutant_certified=0` |

Re-generate goldens only when fixtures or kernels change deliberately; then
re-hash `MANIFEST.json`.
