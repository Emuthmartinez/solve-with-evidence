# Repeated benchmark and release evidence

> **These trials compare versions of the skill with each other.** No arm ran without the skill, so they can show a regression between versions and cannot show that the skill helps. They also measured wording that has since been restructured (November 15, 2026) and were not repeated. The comparison against no skill, a weaker model and a same-token-budget control is the [proof benchmark](../proof/README.md), which is built and not yet run.

This study asks two different questions. Did the solver deliver a correct artifact? Did it exercise the actual deliverable and check the result before handing it over? A solver can earn full outcome credit from an external grader even when its own trace contains no execution.

The baseline is the installed skill captured before the experiment. The `shipped` arm is preserved in [snapshots/shipped](snapshots/shipped). The intermediate snapshots in `snapshots/` and the successive [experiment decisions](protocol.md) document changes made during development. The labels `candidate`, `release`, `final`, and `published` are historical trial identifiers. Use `shipped` to reproduce the version distributed with this release.

## Results

Six versions produced 182 completed two-turn trials across 17 cases. The same external graders re-evaluated all 364 final responses. Seven setup, superseded, or quota-limited attempts are archived separately. The public copies of the four quota refusals redact the account reset time and include hashes of the exported files.

| Version | Trials passing every criterion | Points |
|---|---:|---:|
| Installed baseline | 34/34 | 466/466 |
| Candidate | 26/26 | 316/316 |
| Release | 26/26 | 316/316 |
| Final | 28/30 | 391/400 |
| Published | 30/32 | 432/434 |
| Shipped instructions | 32/34 | 453/466 |

The baseline beat the shipped instructions on two matched printer trials. The first returned a list where the example’s nested job required an object (16/17). In the second, the model changed the escaping in both final messages after testing working code. Both delivered programs failed to parse (5/17). An earlier version also supplied a counterexample on which the correct and faulty algorithms agreed. The original losses remain in the table. [First printer trace](trials/artifact-h3-shipped-r1/trace.jsonl) · [Second printer trace](trials/artifact-h3-shipped-r2/trace.jsonl)

Independent review found pre-delivery execution and an independent expected result in **14/16** shipped Python stages and **0/16** matched baseline stages. On a new sound-archive decision table, both versions passed 16/16 criteria in both repeats. The shipped instructions also checked the deliverable before submission in **4/4** stages, compared with **0/4** for the baseline. The checks cost time. The two shipped trials took 42–46 seconds each and used 39–48 thousand provider-reported tokens, compared with 12–13 seconds and about 17 thousand tokens for the baseline. [Receipts](process) · [Fresh task and timing](contract/results.json)

The optional installed handoff script runs a caller-supplied checker on the final bytes. On 28 archived stage answers from the affected transfers, it accepted 21 as received and rejected all seven defective answers. One trace-backed replacement per rejection then passed the consumer and the original functional grader. This replay did not change any model score. Use this gate at the point where a host receives the final message. [Integration instructions and repair evidence](handoff/README.md)

A separate simulator tested the completion rule. A registry-only implementation issued six false completions on eight signed snapshots and eight on thirteen independent controls. The revised rule issued zero in both sets and accepted the required successes. The package verifier also rejected altered, extra and symlinked files under ordinary and optimized Python. [Completion controls](closure/adapter-results.json) · [Package controls](package-negative-controls-fixed.json)

## What the cases require

| Family | Decision or artifact the grader checks |
|---|---|
| Diagnostic testing | Choose an adaptive two-test policy under shared calibration and update it after an observation and price change. |
| Dispatch | Find a feasible publication and optimal incident repairs under a limited swap budget. Supply a certificate identifying the next distinct score. |
| Record linkage | Return sharp bounds and feasible assignments attaining both ends, then revise the bounds when recovered records rule out assignments. |
| Completion | Compare signed requirements, registry coverage, stop receipts, and scope amendments before issuing a completion notice. |
| Consumer contract | Route archive records using a declarative table and deliver a valid counterexample. The oracle checks 12 inputs before a rule change and 36 after it. |
| Executable artifacts | Deliver callable Python and an effective counterexample. Hidden jobs cover reordered or duplicated events, updated correction rules, allocation, and exact text encoding. The grader executes decoded code in a separate process. |

Every solver case has two turns. The runner opens a new thread per repetition and releases the second prompt after recording the first answer. It gives the solver the assigned skill and optional references, a sealed Python calculator and the task input. All arms use the same resolved model (`gpt-6.1-sol`), medium effort, a limit of 24 tool calls and 200 seconds per turn. Each case has two independent repetitions per assigned arm. Some families and later repairs were selected in response to development results. The [cohort manifest](cohorts.json) says which comparisons were planned for each revision.

## Inspect or reproduce a result

Open a trial directory under [trials](trials). `trace.jsonl` records stage inputs, instruction text, public assistant items, tool names and arguments, returned output, calculator exit status, token usage, and ordering. `summary.json` identifies the runtime, skill digests, timing, caps and final messages. `grade.json` gives the criterion-level outcome, and `manifest.json` binds the trace and summary bytes. The traces omit private reasoning, credentials, provider-internal prompts, and transport deltas duplicated by completed messages. A partial message interrupted before completion may be unavailable. File hashes establish consistency with this export. They do not authenticate the upstream model provider.

From the repository root, regrade all saved answers and validate their trace records with the commands below. macOS and Python 3 are required for the sealed execution of submitted programs. Offline regrading does not call a model. Numeric and document-only graders can also run independently. The calculator exposes the standard library modules preloaded in `runner/calculate.py`. A module outside that subset may be unavailable; the trace retains failed calls and retries.

```sh
cd evaluations/hard
python3 -B tracecheck/audit.py --root . --cohorts cohorts.json \
  --skill baseline=snapshots/baseline --skill candidate=snapshots/candidate \
  --skill release=snapshots/release --skill final=snapshots/final \
  --skill published=snapshots/published --skill shipped=snapshots/shipped \
  --out /tmp/solve-with-evidence-regrade.json
python3 -B tracecheck/test_audit.py --root .
python3 -B closure/check_gate.py
```

For a fresh model run, the recorded environment used Codex CLI 0.166.0 on macOS, a file-backed ChatGPT sign-in, and the supported local app-server protocol. That runner is specific to Codex. The skill instructions are not. Run this from `evaluations/hard` using an empty output directory. Results can differ with model or tool updates. Offline regrading of saved answers does not call a model.

```sh
python3 -B compare.py --out /tmp/swe-new-run --arms baseline shipped \
  --cases ledger-d1 --repeats 1 2 --jobs 2
```

Arms are defined in [`arms.json`](arms.json). Besides the six snapshots it has `skill` (the live folder), `no-skill`, and `skill-weak` and `no-skill-weak` on a weaker model. This runner requires a skill folder and its hash is pinned by the trace audit, so a no-skill arm is given a [one-line placeholder](no-skill/SKILL.md) that says no skill is supplied. None of the new arms has been run on these 17 cases. The same-token-budget control needs repeated invocations and runs only in the proof suite: `compare.py --suite proof`.

The model received the five Markdown files in the [instruction manifest](shipped-manifest.json). The [distribution manifest](distribution-manifest.json) also covers the optional host-side Python checker added after the model trials. Verify that historical package from the repository root with `python3 -B evaluations/verify_evidence.py --manifest evaluations/hard/distribution-manifest.json --package evaluations/hard/snapshots/shipped`. The contract directory retains the frozen experiment launcher and its original layout assumptions. Use `compare.py` above for fresh runs in this repository.

## Limits

The cases use synthetic inputs, restricted tools, and two trials per cell. They exercise specific decisions, failure modes, and code handoffs. They do not estimate reliability across professions, open-web research, distributed execution, or deployment. All included cases are disclosed regression material for subsequent work. The simulator adapters demonstrate specification behavior under explicitly stated interpretations. Actual host enforcement requires an implementation.
