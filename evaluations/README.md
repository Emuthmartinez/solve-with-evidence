# Self-audit and harder-case evaluation

Evaluated on November 14, 2026. The baseline is commit `7bfbd4e3f9bad42023ae223bd1773d2f55290d52`. The candidate's five file digests are stored with the trial records.

## Changes and evidence

| Change | Reason | Verification |
|---|---|---|
| Explicit solver, grader, baseline, candidate, and fresh-case protocol | The previous instructions left evaluation contamination and failed-case reuse ambiguous | Independent document review and a frozen candidate evaluated on reserved cases |
| Trust boundary in the skill entrypoint | The authority rule was only in an optional architecture reference | Independent review of entrypoint and architecture consistency |
| Relevant-version compatibility when accepting results | Global run revision checks could conflict with preserving independent work | Independent walkthroughs of unrelated revision changes and changed input/criterion versions |
| Testable problem representations | Expert selection lacked guidance on expressing the problem in a checkable form | Research rationale and constraint, evidence-selection, and revised-objective cases |
| Failure diagnosis | Replanning guidance left the location of failure implicit | Research rationale and independent specification review |
| Task-coupling guidance | Team selection needed a clearer distinction between independent work and ordered shared-state operations | Research rationale and sequential simulator recovery case |

The representation, diagnosis, and coordination recommendations are synthesized design choices. The advisory describes their source basis and limitations. [General solver design](general-solver-design.md)

## Trial protocol

An independent agent prepared three development cases and two reserved cases, each with five mandatory criteria. The author read the development cases and audited the existing skill. The five-file candidate was frozen before the author opened the reserved prompts. Answer keys stayed with the grader until execution. Both versions received one fresh solver session per case. H2's second stage arrived in the same session after the first response. No candidate edits followed exposure to the reserved cases.

Solvers used the host's default model configuration with no model overrides, local tools, separate trial directories, and instructions to avoid other trials and answer keys. They had no external-action or additional-agent task scope. Isolation relied on assignment instructions and fresh contexts. The host's full filesystem capabilities remained available. Exact model build, token use, cost, and comparable latency were unrecorded.

The published case prompts preserve the task facts and canonical wording. Baseline D1–D3 were dispatched as equivalent paraphrases. Assignment wrappers added skill paths and file ownership. Candidate D1 also received explicit sequential-execution guidance after fixture review. Baseline D1 executed sequentially. These differences and missing full process transcripts limit controlled attribution.

After grading, the coordinator transcribed the dispatched task messages and H2 followups into `records.json`. These preserve the original wrappers alongside the canonical prompts. The grading report's earlier observation that the wrapper was absent from the saved prompt remains part of that review record. Process receipts and full host context remain outside the export.

## Results

Both versions passed all five cases, with 25 of 25 criteria satisfied per version. The ten trials produced no observed criterion failures or critical behaviors. The observed performance difference is zero. These results support compatibility with the tested scenarios and leave broader improvement unproven.

| Scenario | Baseline | Candidate |
|---|---|---|
| Interrupted allocation with stale plan and two ambiguous acknowledgements | 5/5 | 5/5 |
| Pilot selection with reversed aggregate and standardized rates | 5/5 | 5/5 |
| Conflicting specialist proposals under a shared resource limit | 5/5 | 5/5 |
| Model selection after excluding training-overlap cases | 5/5 | 5/5 |
| Two-stage allocation with a changed budget and fairness rule | 5/5 | 5/5 |

The independent grader's complete criterion-level assessment is published separately. The records preserve both stages of H2, all final reports, and both D1 state/event histories. [Grading](comparison-grade.md), [Trial records](records.json)

## Reproduce the checks

Run from the repository root with Python 3.

```sh
python3 -B evaluations/verify_evidence.py
```

This replays both recorded D1 call sequences, and probes stale revisions, invalid operation IDs, wrong quantities, timeout-after-commit, readback, and same-key deduplication. It verifies recorded outcomes and the fixture implementation. Add `--manifest historical-candidate --package PATH` to verify an archived copy of the five files from that trial. For a newer package, supply its own JSON filename-to-SHA-256 manifest. The historical transcript uses `<trial-workspace>` for machine-specific paths. Fresh solver trials require new sessions using the documented tasks and grading protocols.

The allocation simulator is a deterministic, single-executor fixture. Use a separate state file per trial and execute its calls sequentially. Each invocation persists its state and event history. The simulator lacks concurrency locking, and these tests do not establish concurrent correctness.

```sh
python3 evaluations/allocation_simulator.py --state /tmp/solve-evidence-example/state.json inspect
```

Use a new empty trial directory when starting another run. The [development protocol](dev-spec.md) and [reserved-case protocol](holdout-spec.md) describe delivery and grading. The included cases have now been disclosed and are regression material for future revisions. Fresh evaluation claims require newly reserved cases.

## Verification limits

D1 event histories reproduce exactly and show the expected final state with one new allocation. The files do not include protected append-only receipts or literal process outputs. For analytical cases, the grader independently checks the numbers and conclusions. The reports' claims about local calculation-tool use rely on their execution context, whose full transcript is not exported here.

One trial per version per case cannot estimate reliability or isolate the effect of a prompt change. These supplied-data fixtures do not measure open-web research quality, professional expertise, creative quality, long-running recovery, real-provider effects, concurrency enforcement, or deployment performance. The separate document review establishes specification consistency. An implemented orchestration service still needs runtime testing.
