# Contracts, evidence and completion

These are record shapes for an agent to keep, not a service to run. A small run can hold them as a short Markdown note with the same meaning. Use the full forms when several workers are involved or the run must be resumable.

## Run record

| Field | Content |
|---|---|
| Request | The original request, the current scope, and who authorized each change |
| Parts | Each part of the request, its problem type, and the reason for that type |
| Goals | ID, desired outcome, required or optional, and its check IDs |
| Constraints | Hard limits and preferences, with their source. A preference never grants authority |
| Knowledge | Each statement with a status: `user_reported`, `observed`, `source_supported`, `assumption`, `unknown` |
| Authority | What may be done, what may not, and when that expires |
| Limits | Budget, deadline, retries and revisions allowed, and a reserve for verification |
| Results | Artifacts, claims, evidence, assessments, review findings, receipts |
| Outcome | One of the three outcomes below, with the unchecked list |

Keep credentials and unneeded personal data out of the record. Store decisions and reasons, not private reasoning.

## Assignment and return

Send a worker these fields. Point to large artifacts instead of copying the conversation.

| Field | Content |
|---|---|
| `objective` | One sentence, linked to the goals it serves |
| `problem_type` | The type from the routing table, so the worker uses the right check |
| `inputs` | Exact artifacts and versions |
| `owns` | The output this worker alone writes |
| `allowed` | Tools and actions. This cannot widen the coordinator's authority |
| `checks` | The check IDs the output must meet, and which are gating |
| `limits` | Attempts, revisions, deadline |
| `stop_when` | Sources conflict in a way that changes the answer. An action exceeds authority. The budget is spent |

A worker returns:

| Field | Meaning |
|---|---|
| `status` | `submitted`, `blocked` or `failed`. A worker cannot declare the run complete |
| `artifacts` | What was produced, where, and which version |
| `claims` | Each claim with its evidence IDs, scope and uncertainty |
| `actions` | Tool and action receipts, state readbacks, unresolved side effects |
| `self_checks` | Checks attempted and results. These are not independent approval |
| `unchecked` | What the worker could not check, why, and what would check it |
| `blockers` | What is missing and the exact condition that would unblock it |
| `usage` | Tokens, calls and time spent |

Missing evidence is `inconclusive`, never a pass. The coordinator rejects a malformed or stale return.

## Checks and assessments

A check is a definition. An assessment is one attempt to evaluate it. Keep them apart so a check cannot be quietly changed to match the output.

```yaml
check:
  id: C3
  goal_id: G1
  problem_type: decision_under_constraints
  gate: gating            # gating | best_effort
  description: The recommended venue meets every hard constraint at the supplied terms.
  target: venue-comparison
  rule: {all_hard_constraints_satisfied: true, total_cost_lte: 600, currency: USD}
  evaluator: reviewer-1
  independent: true
  exemplars: {good: [E7], bad: [E8]}   # the check must pass E7 and reject E8
  evidence_required: [constraint_matrix, reproduced_total, source_offer_refs]
  scope: Recommendation only. No claim about live availability or booking.
  on_failure: reopen_selection
assessment:
  id: A3
  check_id: C3
  evaluator: reviewer-1
  status: pending         # pending | passed | failed | inconclusive | not_run | stale
  artifact_version: 1
  evidence_ids: []
  limitations: []
```

Rules:

- A gating check must be `passed` for anything to be delivered as done.
- A best-effort check may end as `not_run`. It then appears in the unchecked list with the reason and what would run it.
- `failed` is never downgraded to `not_run`. A check that ran and failed is a failure.
- A check with exemplars is valid only if it passes every good exemplar and rejects every bad one. Record that trial as an assessment before using the check.
- Changing the user's goal or a hard constraint needs the user's authority. Tightening a technical test does not.
- When an input, artifact or source changes, mark dependent assessments `stale` and rerun them. Approval of an old version does not carry over.

## Evidence

Each evidence record has an ID, a kind, who produced it, when it was observed, a locator down to the passage or record, the versions involved, the result, and what it does not cover.

| Kind | Establishes |
|---|---|
| `source` | What a source says, at a located passage |
| `observation` | What was seen in a named environment at a named time |
| `test` | What happened when the artifact ran under recorded conditions |
| `calculation` | A reproducible result from stated inputs |
| `review` | An independent reviewer's verdict, the reviewer's model family, and whether the verdict was formed before reading the author's rationale |
| `action_receipt` | That a tool reported an action. Not that the outcome exists |
| `exemplar_good` | An example that meets the standard, with who judged it so and why |
| `exemplar_bad` | A plausible example that fails the standard, with the reason it fails |

Exemplars are evidence about the standard, not about the deliverable. Use them to validate a rubric or a test, and keep some out of the instructions so they remain a fair check. A citation, a digest or an ID proves neither authenticity nor correctness alone. Read the referenced content and judge whether it applies.

## Outcomes

Track execution separately from outcome.

```text
execution = active | waiting | finished | stopped
outcome   = pending | verified | delivered_unchecked | withheld
```

| Outcome | Condition | What the user receives |
|---|---|---|
| `verified` | Every gating check passed, and every best-effort check ran and passed | The deliverable and the goal-to-evidence map |
| `delivered_unchecked` | No check failed. Every gating check passed. One or more best-effort checks are `not_run` or `inconclusive` | The deliverable, and a list of each unchecked item with why and what would check it |
| `withheld` | A check failed, or a gating check is `not_run` or `inconclusive` | The blocker and what would clear it. No deliverable presented as done |

`delivered_unchecked` exists because strict fail-closed delivery blocks most writing and strategy work, where some judgment cannot be checked mechanically. It is not a softer pass. It may not be used to ship past a failed check, to cover a gating check, or without the list.

`waiting` with `pending` covers an observation window that has not elapsed. Installation can be verified while the outcome it should cause is still pending.

## Completion rule

Report `verified` or `delivered_unchecked` only when all of these hold. Otherwise the outcome is `withheld` or still `pending`.

1. **Coverage.** Derive the required outcomes from the original request and its authorized amendments, independently of your own task list. Each maps to a required goal, a deliverable or effect, and at least one adequate check. A list that lost a requirement, or marked it optional, fails coverage.
2. **Checks.** Every gating check is `passed` on current evidence for the delivered version. No check is `failed`.
3. **Deliverables.** Each required deliverable exists, matches the version that was checked, and works through its intended entry point.
4. **Constraints.** Hard constraints hold. No must-fix finding, critical assumption or unknown external effect undermines the claim. Nothing still running can change the result.
5. **Independence.** Any required independent review is done by a non-author on the final version. An author cannot create independence by changing a label.
6. **Scope at the last moment.** Recheck authority, scope and any stop instruction immediately before reporting. A binding stop suppresses a new completion notice even when every check is green. Keep the evidence of work already done.
7. **Claim size.** The report claims no more than the evidence covers in scope, population, time and environment.

These conditions need judgment as well as bookkeeping. Linkage and status can be checked mechanically. Whether evidence is true cannot.

## Final report

Lead with the outcome and its scope. Then give:

- The problem type chosen for each part.
- Each required goal, the observed result, the evidence, and the status.
- Deliverable links, with environment and version where they matter.
- The unchecked list: item, why it was not checked, what would check it.
- Limits, contrary evidence and unresolved assumptions.
- Each blocker, its effect, the next action, and who can unblock it.

Optional improvements stay separate from unmet requirements.
