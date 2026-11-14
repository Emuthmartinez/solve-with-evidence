# Two-turn reasoning benchmarks

Six generated cases test decisions under changing information. Each family has two development cases (`d1`, `d2`) and one reserved case (`h1`). Case IDs combine the family and variant, for example `probe-d1` or `roster-h1`. Python 3.8+ and its standard library suffice. Run from this directory.

```sh
python3 bench.py prompt probe-d1 1
python3 bench.py prompt probe-d1 2
python3 bench.py grade probe-d1 turn1.json turn2.json
python3 bench.py selftest
```

For an actual trial, give the solver only the first prompt. Save its unedited answer before delivering the second prompt in the same conversation. The second message fixes what the team did, even if the solver chose differently. Supply private scratch space for Python. Keep the harness, source, seeds, other arms' responses and grading output away from solvers. Freeze the candidate before generating reserved prompts. Source access reveals the deterministic case generator and oracle.

The grader reads a JSON object per turn, accepts a surrounding Markdown JSON fence, and accepts uppercase or lowercase action IDs. Numeric bounds and required keys appear in each prompt. All legal tied optimal actions are accepted. Each stage earns at most 5 points and each case 10. A pass requires 10/10 and no critical failure. Individual checks retain their points when another check fails. The checks in the returned JSON say exactly what was credited. For Python callers, use `bench.prompt(case_id, stage)` and `bench.grade(case_id, [reply1_dict, reply2_dict])`.

## What the cases measure

| Family | Stage 1 | Stage 2 | Independent check |
|---|---|---|---|
| `probe` | Price four adaptive two-test policies with persistent shared calibration. The best test for a one-test budget differs from the best first action for the actual budget. | Condition on one observation echoed by a second display. Recalculate after a price change that changes the next action. | Bellman recursion with rational arithmetic agrees with enumeration of deterministic contingent terminal policies. The self-test also checks the posterior against a direct weighted-row calculation. |
| `roster` | Choose a five-job publication minimizing nominal cost plus worst-case optimized incident cost. The nominal optimum differs from the robust optimum. | Reoptimize from the actual publication after a further closure and a second, surcharged exchange becomes available. Count each distinct feasible final roster at its minimum exchange distance. | The primary oracle enumerates permutations and uses cycle counts. A second implementation traverses explicit pair exchanges, recomputes costs independently and compares all publication scores and realized-incident rosters. |

The probe oracle requires a margin of at least 0.12 over the next initial action and 0.15 over the next realized action across all variants. The response tolerance is 0.01. The roster uses integral costs and has unique optima in both stages. Development margins over the second-best initial and realized actions are shown below. The reserved values remain in the runner.

| Case | Stage 1 margin | Stage 2 margin |
|---|---:|---:|
| probe-d1 | 0.5852 | 0.2308 |
| probe-d2 | 0.1764 | 0.3000 |
| roster-d1 | 7 | 3 |
| roster-d2 | 6 | 8 |

The self-test scores the full reference outputs, empty responses, invalid JSON objects, partially correct numeric certificates and an illegal final action for each variant. It verifies that a recorded stage 1 with no stage 2 scores exactly 5 points. Retesting a consumed instrument, choosing an unknown final action, dispatching a forbidden roster, or recommending an illegal incident repair triggers a named critical failure. Valid but suboptimal choices lose the corresponding points. The probe grader gives continuation credit relative to the solver's own first choice and the roster grader gives repair credit relative to the solver's own legal publication.

The six cases sample two synthetic decision models. Fresh answers on both arms under matched model, history and tool privileges are needed to measure any skill effect. Grader self-tests establish grading behavior.
