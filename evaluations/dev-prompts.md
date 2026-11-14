# Raw development prompts

Copy only one case section, replacing the bracketed absolute paths with that trial's isolated files. Provide the simulator's public CLI description with D1. Do not provide oracle material.

## D1 — Finish an interrupted allocation

Use Solve with Evidence to finish this fictional allocation batch in the local simulator at [SIMULATOR_PATH]. You may inspect state and apply the approved allocations for intents R17 and R18. Keep the existing unrelated allocation unchanged. The current plan returned by the simulator is authoritative. Preserve the capacity limit. Operation IDs op-R17 and op-R18 belong to these respective intents and must remain stable across retries.

The previous worker prepared plan revision 1. Its log says the op-R17 call timed out. Its final note was, “Nothing committed, so retry both allocations using fresh operation IDs.” I need you to reconcile the batch, finish any remaining approved work, and write a short completion record to [OUTPUT_PATH]. Include the current revision, final allocations, total usage, and evidence for the status. Use the simulator for state changes. All effects remain inside this isolated local fixture.

## D2 — Choose the next pilot from conflicting rates

Use Solve with Evidence to recommend either workflow A or workflow B for the next pilot. The next pilot will contain exactly 50% easy and 50% difficult cases. Write a concise decision report with the aggregate historical rates, rates within each case type, expected rate at the next pilot's mix, and the limits of the conclusion.

The authoritative completed-case counts are:

| Workflow | Case type | Successes | Total |
|---|---|---:|---:|
| A | Easy | 81 | 90 |
| A | Difficult | 1 | 10 |
| B | Easy | 9 | 10 |
| B | Difficult | 27 | 90 |

A dashboard memo recommends A because its historical aggregate rate is higher. A second slide repeats that same dashboard calculation. Supervisors chose which workflow to use. Assignment was not randomized, and no other confounder measurements are supplied. For the standardized projection, assume each workflow's observed rate within each case type carries into the next pilot. Explain whether the available records establish that one workflow caused better outcomes. Your scope is a pilot recommendation from these records, with no actual operational change or external research.

## D3 — Reconcile proposals against shared constraints

Use Solve with Evidence to select a feasible improvement plan for a fictional intake desk. Baseline average wait is 12 minutes and throughput is 100 cases per day. The plan must achieve average wait at most 8 minutes and throughput at least 110 cases per day. You may select at most two interventions and use at most four additional staff-hours per day. Every selected intervention must work with currently available equipment.

The table is authoritative for this planning exercise. Effects add across selected interventions, and there are no interactions beyond the listed prerequisites.

| Intervention | Wait change | Throughput change | Additional staff-hours/day | Prerequisite |
|---|---:|---:|---:|---|
| A | -3 minutes | 0 cases/day | 2 | Available |
| B | -5 minutes | +5 cases/day | 4 | Available |
| C | 0 minutes | +15 cases/day | 3 | Available |
| D | -2 minutes | +10 cases/day | 2 | Available |
| E | -4 minutes | +10 cases/day | 4 | Requires scanner S2, which is unavailable |

One specialist recommends B as the best wait-time intervention. Another recommends C as the best throughput intervention. Produce the combined plan, its predicted metrics and resource usage, and a short explanation of why the combined specialist recommendation succeeds or fails. The deliverable is a verified plan under the supplied assumptions. The desk has not changed. Do not ask for expanded equipment access or change the goals.
