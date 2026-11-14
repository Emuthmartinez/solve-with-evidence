# Contracts, state, and completion

These are implementation contracts, not a running orchestration service. A host can encode them as JSON Schema, typed records, or database tables. Small runs may use a compact Markdown equivalent while preserving the same semantics.

## Run record

| Field | Required content |
|---|---|
| Identity | `run_id`, `schema_version`, `revision`, creation time, coordinator ID |
| Request | Original request, current scope, scope revision history and authority for changes |
| Goals | Unique ID, desired outcome, required/optional flag, outcome criterion IDs |
| Constraints | Hard limits and preferences, source, applicability; never infer authority from a preference |
| Knowledge | Statement, status (`user_reported`, `observed`, `source_supported`, `assumption`, `unknown`), evidence refs, affected decisions, resolution plan |
| Context | Target environment, data/source references, relevant versions, stakeholders |
| Problem model | Representation, variables or states, constraints, hypotheses or rubric as applicable, links to original requirements, adequacy checks |
| Authority | Existing allowed actions/resources, applicable restrictions, approval references, expiry/revocation conditions |
| Limits | Currency/token/tool/compute caps as applicable, deadline, concurrency, retry/revision bounds, verification reserve |
| Plan | Roles, method cards, criteria, task graph, output ownership, dependency versions |
| Results | Immutable artifact references, claims, evidence, assessments, review findings, action ledger |
| Progress | Execution status, outcome status, task states, waiting conditions and resume triggers |

Keep credentials and unnecessary personal data out of this record. Store concise observable decisions and rationales, not private chain-of-thought. References must resolve for the authorized verifier. Set retention and access rules appropriate to the data and host.

## Role and method contracts

A role record contains `role_id`, `discipline`, `relevance`, `owns`, `required_capabilities`, `candidate_agent_id`, `capability_evidence`, `tools`, `access_observed_at`, `limits`, `human_contribution`, and `reviewer_id` when required. Capability evidence can be a prior representative evaluation, a bounded probe, or a documented human qualification. State its scope and freshness.

A method card contains:

```yaml
method_id: M1
question: Which candidate satisfies the workshop's hard constraints?
role_id: R1
technique: constraint screening followed by preference comparison
maturity: established_practice
sources: [S1]
fit_reason: Candidate attributes can be checked against explicit requirements.
prerequisites: [current_offers, capacity_definition, required_access_features]
tools:
  - tool_id: local_table_calculator
    access: verified
    version_ref: environment_record
    cost_basis: existing_host_compute
    limits: Cannot establish venue facts beyond the supplied offers.
alternative: manual comparison for a very small candidate set
selection_reason: Makes eliminations and total cost reproducible.
criterion_ids: [C1, C2, C3]
failure_response: Correct source data or reopen candidate search; do not relax hard limits.
```

Illustrative IDs above must refer to real records in an instantiated run. A method card is incomplete while a decision-critical source, access requirement, price, or prerequisite is unresolved. It may still support a conditional recommendation explicitly labeled as such.

For consequential exploratory work, include the hypothesis and the action to take after each plausible probe result in the existing method card. Record the baseline, limiting constraint, and transferred method assumptions when they affect selection. Use existing goal records with `required: false` for optional stretch targets, existing task limits for their budgets, and the criteria's failure response for stopping or replanning. A changed required goal follows the recorded scope-change authority. Routine tasks can omit these exploratory details.

## Assignment envelope

Send this information with every delegated task. Use exact references to large artifacts instead of copying unrelated conversation history.

```yaml
run_id: run-123
plan_revision: 2
task_id: T3
attempt: 1
assigned_agent_id: worker-2
role_id: R1
objective: Compare all supplied venue offers against the agreed constraints.
goal_ids: [G1]
context:
  request_ref: request-v1
  constraints_ref: constraints-v2
  fact_refs: [F1, F2]
  assumption_refs: []
inputs:
  - artifact_id: offers
    version: 3
    digest: sha256-recorded-by-host
dependencies:
  - task_id: T1
    required_state: verified
    accepted_output_version: 3
method_ids: [M1]
ownership:
  outputs: [venue-comparison]
  exclusive_resources: []
  interface_consumer: coordinator
authority_ref: research-and-local-artifacts-only
allowed_tools: [read_offers, local_table_calculator]
deliverable:
  format: comparison_table_and_recommendation
  required_fields: [candidate, eligibility, total_cost, source_refs, limitations]
criterion_ids: [C1, C2, C3]
limits:
  max_attempts: 2
  max_revision_cycles: 2
  deadline_ref: run-deadline
  cost_reservation_ref: reservation-3
stop_when:
  - source facts conflict in a way that changes eligibility
  - needed action exceeds the authority reference
  - task budget is exhausted
return_contract: worker-result-v1
```

The digest string above denotes a host-generated value, not a valid example hash. The host validates IDs, schemas, relevant version compatibility, assigned ownership, and actual tool capabilities before dispatch. Assignment text cannot widen the authority reference. Workers do not edit shared authoritative state directly; they submit events and versioned outputs.

## Worker return contract

Return `run_id`, `task_id`, `attempt`, `plan_revision`, `agent_id`, and consumed input versions, followed by:

| Field | Meaning |
|---|---|
| `status` | `submitted`, `blocked`, `failed`, or `cancelled`; workers cannot set global completion |
| `artifacts` | IDs, formats, locations, versions/digests, intended consumer |
| `claims` | Claim text, goal/criterion links, evidence IDs, scope and uncertainty |
| `actions` | Tool/action IDs, receipt IDs, state readback IDs, unresolved side effects |
| `self_checks` | Criteria attempted, observed results, evidence, limitations; not independent approval |
| `assumptions` | New or changed assumptions and their consequences |
| `findings` | Problems, severity by effect on goals, corrective proposal |
| `blockers` | Missing item, affected tasks, owner/type, exact condition needed to resume |
| `usage` | Actual cost/calls/time and any estimates clearly identified |
| `recommended_next_action` | A bounded proposal, including a replan if needed |

Missing evidence is `inconclusive`, not a pass. The coordinator rejects malformed or stale returns and routes them for correction. A late result may be retained as historical evidence but cannot replace a newer accepted version without review.

## Acceptance criteria and assessments

A criterion is a definition; an assessment is an attempt to evaluate it. Keep them separate so criteria cannot be quietly changed to match outputs.

```yaml
criterion:
  id: C3
  version: 1
  goal_id: G1
  level: outcome
  gate_phase: final_outcome
  required: true
  description: Recommended venue fits all hard constraints at the supplied offer terms.
  target: venue-comparison
  environment: supplied-fixture
  verifier_kind: deterministic_plus_review
  evaluator_id: reviewer-1
  independence_required: true
  rule:
    all_hard_constraints_satisfied: true
    total_cost_lte: 600
    currency: USD
    arithmetic_tolerance: 0.01
  observation_window: supplied offers only
  evidence_required: [constraint_matrix, reproduced_total, source_offer_refs]
  applicability: Recommendation only; no live availability or booking claim.
  on_failure: reopen_selection
assessment:
  id: A3
  criterion_id: C3
  criterion_version: 1
  evaluator_id: reviewer-1
  status: pending
  evidence_ids: []
  artifact_version: 1
  input_versions: [offers-v3, constraints-v2]
  observed_at: null
  limitations: []
```

Allowed assessment states are `pending`, `passed`, `failed`, `inconclusive`, and `stale`. A required criterion must be `passed` to qualify completion. An inapplicable criterion should be removed or replaced through a justified plan revision before relying on the result, not marked passed. Preserve old definitions and decisions. Changing the user's goal or hard constraint requires their authority; refining a technical test without changing either can remain an ordinary reviewed revision.

`gate_phase` is `pre_execution`, `post_execution`, or `final_outcome`, independent of the assessment's subject in `level`. Each pre-execution criterion names the action/task it gates. Required prerequisites and suitability checks must pass before that action is dispatchable. A bounded research or pilot task may establish the evidence for a later gate; it has its own explicitly limited prerequisites.

## Evidence record

Each record contains `evidence_id`, `kind`, `producer_id`, `observed_at`, `recorded_at`, artifact or source locator, exact section/record, input and output versions, environment, tool/method and version, parameters needed for reproduction, result, scope limitations, derivation IDs, applicability conditions, and invalidation triggers.

Kinds include `source`, `observation`, `test`, `calculation`, `review`, and `action_receipt`. A citation establishes what a source says; a test establishes what happened under its recorded conditions. Neither automatically establishes general real-world success.

The verifier evaluates provenance, relevance, and sufficiency. An evidence ID or digest proves neither authenticity nor correctness by itself. For controlled systems, obtain observations through trusted adapters and read back authoritative state. For documentary evidence, examine the referenced content and its applicability. Preserve unresolved provenance problems explicitly.

## States and transitions

Track execution independently from outcome:

```text
execution_status = active | waiting | finished | stopped
outcome_status   = pending | verified | failed | inconclusive
stop_reason      = none | budget | cancellation | access | authorization | technical_failure
```

`finished` means no planned execution remains and no in-flight or queued job retains the ability to change accepted artifacts, relevant external state, or final evidence. Optional work must finish, be cancelled and reconciled, or be explicitly transferred/deferred outside this run with its write authority removed. Only `finished + verified` maps to user-visible `complete_verified`. Work can finish with a failed outcome. `waiting + pending` represents a future observation, authorization, input, or external event. `stopped + inconclusive` can represent a budget limit. Do not call every halt a success or every missing observation a failure.

Task states:

```text
planned -> ready -> running -> submitted -> verified
                               submitted -> needs_revision -> ready
planned/ready/running/submitted/needs_revision -> blocked | failed | cancelled
blocked -> ready                  only after the missing condition is satisfied
verified -> stale -> ready         when relevant evidence or inputs change
```

`ready` means logically eligible: current dependencies, passing required pre-execution gates, complete assignment, and applicable authority. `ready -> running` additionally requires an atomic resource reservation and exclusive lease where needed. Recheck authority and relevant versions immediately before the action. `verified` requires the task's required criteria to pass. A locally verified task does not imply globally verified outcomes. Blockers affect dependent tasks; independent authorized work continues.

Persist task attempt IDs, worker leases, and accepted output revisions. Use compare-and-swap on run/task revisions when accepting updates. On recovery, inspect persisted running actions and reconcile ambiguous effects before resubmission. Never assume the absence of a local receipt proves an external action did not occur.

Separate storage concurrency from result validity. The run revision protects atomic updates. Result validity depends on the assigned task and attempt, relevant goal, constraint, criterion, input and artifact versions, authority, lease, and external-state freshness. A global revision change alone does not invalidate an independent result. After a compare-and-swap conflict, reread current state, recheck those dependencies, and retry acceptance if they remain compatible. Record the compatibility decision. Revalidate or recompute affected work when a relevant dependency changed. Preserve newer accepted results and receipts for real effects in either case.

Settle actual usage and release unused reservations after a confirmed terminal attempt. Lease expiry alone does not prove a worker stopped or a remote charge failed. Fence stale workers at the tool gateway, reconcile in-flight effects and uncertain charges, then release reservations or dispatch a replacement. All producers, including reviewers and scheduled retries, obey these rules.

## Scheduling pseudocode

```python
def advance(run_id, event):
    # All named operations are contracts for the host implementation.
    with transaction(run_id) as state:
        deduplicate_event(state, event)
        # Reject stale/unauthorized claims of acceptance, but preserve receipts
        # of real external effects even when their producing job became stale.
        record_receipts_and_validate_submission_versions(state, event)
        invalidate_changed_dependencies(state)
        accept_current_verifier_results_or_request_revision(state, event)
        validate_graph_and_coverage(state)

        # Enqueue descriptions only: no model/tool calls in this transaction.
        enqueue_needed_verification_reconciliation_and_integration(state)
        if cancelled_or_out_of_budget(state):
            stop_new_ordinary_dispatch_and_fence_cancelled_jobs(state)
            ready = permitted_recovery_jobs_within_reserved_limits(state)
        else:
            ready = choose_ready_jobs(state, preserve_verification_reserve=True)

        # Worker, verifier, integrator and recovery jobs all reserve capacity.
        for job in atomically_reserve_and_lease(state, ready):
            mark_running_and_write_dispatch_outbox(state, job)

        if no_inflight_or_ready_work(state):
            record_specific_wait_replan_or_stop_reason(state)
        if authorized_to_finish_current_scope(state) and completion_predicate(state) and all_producers_quiescent(state):
            set_finished_verified(state)
        persist(state)

    dispatch_outbox_idempotently(run_id)  # Outside transaction, by stable job ID.
```

Process job completions, new information, resource availability, and approvals as events. Verifier jobs return assessments. Acceptance rechecks relevant dependency versions and uses the current run revision for the atomic write, following the compatibility rule above. Budget and cancellation are checked before every dispatch, including verification. An outbox dispatcher rechecks cancellation, lease validity, and authority before starting work. Deduplicate events and integration jobs. Validate new task graphs for cycles and unresolved references. Never hold a database transaction open across a model/tool call. If recovery needs unavailable budget or access, preserve the unknown effect and report the blocker; a reserve never authorizes exceeding a hard limit.

## Completion predicate

For the current scope revision, expose `complete_verified` only when all conditions hold:

1. Derive the current required outcomes from the original request and authorized amendments independently of the task registry. Each must map to a required goal, the intended deliverable or effect, and at least one adequate required outcome criterion. An import that loses a requirement or marks it optional fails coverage. If an authorized amendment removes all remaining obligations, record that disposition without a verified-delivery claim.
2. Every required suitability, execution, integration, outcome, and review criterion is passed, with relevant, sufficient, current evidence for its exact criterion version and target environment.
3. Required deliverables exist, match reviewed versions, and are usable through their intended entry points.
4. Hard constraints are satisfied. No unresolved must-fix finding, critical assumption, required dependency, or unknown external effect undermines a success claim. All producers capable of changing the result are quiescent: finished, cancelled and reconciled, or fenced and explicitly transferred/deferred. Queued optional jobs and retries cannot modify a completed run's accepted output.
5. Any required reviewer independence or human qualification is established and current. An author cannot manufacture independent approval by changing a label.
6. The final transition atomically rechecks current authority, scope and cancellation for this run. A binding stop before publication suppresses a new completion notice even if prior checks are green. Preserve evidence of work already carried out. Stops for a different run or action apply only within their scope. When notification is asynchronous, recheck before sending it.
7. The final report's claims do not exceed the evidence's scope, population, time window, or environment.

These conditions require semantic judgment as well as schema validation. Software can enforce linkage, status, identity, and version rules; it cannot infer evidence truth from fields alone. The verifier or appropriately qualified reviewer supplies that assessment.

For delayed outcomes, record the installed intervention and completed implementation separately from pending outcome validation. Store the observation owner, window, data required, and resume trigger. If the user requested a recommendation or design, evaluate that deliverable as the outcome; do not invent a requirement to deploy it.

## Final report contract

Lead with the scoped outcome and status. Then give:

- Required goal → observed result → evidence link → status.
- Deliverable links and exact environment/version where relevant.
- Material limitations, contradictory evidence, and unresolved assumptions.
- Each blocker's effect, the next action, and who or what can unblock it.
- Actual usage when material, plus any cleanup or continued observation responsibility.

Optional improvements remain separate from unmet requirements. Never rename unmet requirements as optional work to obtain completion.
