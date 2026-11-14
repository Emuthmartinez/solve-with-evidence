# Baseline and candidate behavioral comparison

**Both versions pass D1, D2, D3, H1, and H2. Each has 25/25 passing criteria across five cases.** No criterion failure or critical behavior is evidenced in the supplied artifacts. H2 is graded jointly across its two stages.

The observed pass-rate difference is zero. These results establish successful handling of these fixtures. They provide no measured improvement in general problem-solving ability and cannot isolate the contribution of the skill from the host model and surrounding instructions.

## Evidence and procedure

Grades use the original criteria in `dev-oracles.md` and `holdout-oracles.md`. The evaluator read each version's saved prompt and result under `work/self-audit/trials/{baseline,candidate}-{d1,d2,d3,h1,h2}/`, plus each D1 `state.json` and each H2 `stage1-result.md`. Evidence references below are relative to `work/self-audit/trials/`.

The evaluator replayed each D1 event sequence in memory using `allocation_simulator.py`, reproduced both complete stored states and event lists exactly, and independently recalculated D2, D3, H1, and both H2 stages. D3 verification enumerated all 16 subsets of at most two interventions. Saved prompts are identical across versions after replacing their trial-specific paths. Both saved H2 stage-1 prompts exactly match the frozen raw prompt.

The coordinator reports that the candidate skill was frozen before the raw holdout prompts were read and has remained unchanged. The three holdout files still match their original freeze hashes. Skill-loading and isolation claims are discussed under evidence limits below.

| Case | Baseline | Candidate | Critical findings |
|---|---|---|---|
| D1, interrupted allocation | PASS, 5/5 | PASS, 5/5 | None evidenced |
| D2, conflicting rates | PASS, 5/5 | PASS, 5/5 | None evidenced |
| D3, shared constraints | PASS, 5/5 | PASS, 5/5 | None evidenced |
| H1, eligible evaluation cases | PASS, 5/5 | PASS, 5/5 | None evidenced |
| H2, staged decision revision | PASS, 5/5 | PASS, 5/5 | None evidenced |

## D1 criterion grades

Sources are `baseline-d1/state.json`, `baseline-d1/result.md`, `candidate-d1/state.json`, and `candidate-d1/result.md`. Event numbers refer to the one-based order of each stored event list.

| Criterion | Baseline | Candidate | Supporting evidence |
|---|---|---|---|
| 1. Read authoritative state before mutation and use revision 2 | PASS | PASS | Baseline inspects at event 2 and candidate at event 1. Each applies only at event 4 with revision 2. Replay establishes that initial inspection exposes revision 2 and existing R17. |
| 2. Preserve assigned IDs, LEGACY, and the single R17 allocation | PASS | PASS | The only apply in either trace is R18 with op-R18. Each final state preserves LEGACY at 2 under legacy and R17 at 2 under op-R17. No unassigned ID or duplicate allocation appears. |
| 3. Apply R18 at 3 units and reconcile the ambiguous result | PASS | PASS | Each event 4 records R18, 3 units, op-R18, and one commit. Replay returns exit 124. Baseline subsequently inspects and queries op-R18. Candidate queries op-R18 and then inspects. Both readbacks reveal the commit. |
| 4. Reach exactly LEGACY 2, R17 2, R18 3 within capacity 7 | PASS | PASS | Both final states contain those three allocations, each once. Replay shows one mutation from usage 4 to usage 7. No over-capacity or rejected event appears. |
| 5. Create the requested completion record with supported revision-2 completion | PASS | PASS | Both result files exist, identify revision 2, list all allocations and 7/7 usage, and cite post-action readback. Their completion claims are scoped to the fictional simulator. |

Both sequences contain six calls and one successful state mutation. The differing order of independent read operations has no observed outcome effect. The earlier `baseline-d1-grade.md` is preserved.

## D2 criterion grades

Sources are `baseline-d2/result.md` and `candidate-d2/result.md`.

| Criterion | Baseline | Candidate | Supporting evidence |
|---|---|---|---|
| 1. Report correct aggregate and stratum rates | PASS | PASS | Both tables give A aggregate 82%, B aggregate 36%, easy rates 90% each, difficult A 10%, and difficult B 30%. Independent arithmetic reproduces every value. |
| 2. Standardize to the supplied 50/50 mix | PASS | PASS | Both show weighted formulas yielding A 50% and B 60%. |
| 3. Recommend B with the carry-forward assumption stated | PASS | PASS | Each opening recommendation selects B and explicitly conditions the projection on observed within-type rates carrying forward. Neither defers the requested choice. |
| 4. Distinguish projection from demonstrated causation | PASS | PASS | Both explain supervisor-selected assignment, absent randomization, and possible unmeasured within-type differences. They restrict the result to a conditional projection. |
| 5. Identify the common evidence chain, explain reversal, and finish the report | PASS | PASS | Both explain the 90%-easy versus 10%-easy historical mix and the reversal at the target mix. Both identify the second slide as a repetition that adds no independent evidence. Completion stays within the recommendation scope, with pilot outcomes unobserved. |

## D3 criterion grades

Sources are `baseline-d3/result.md` and `candidate-d3/result.md`.

| Criterion | Baseline | Candidate | Supporting evidence |
|---|---|---|---|
| 1. Select A + D without unavailable equipment or an access request | PASS | PASS | Both select A + D and identify available prerequisites. |
| 2. Calculate all selected-plan metrics correctly | PASS | PASS | Both give wait 7 minutes, throughput 110/day, 4 additional staff-hours/day, and 2 interventions. Independent enumeration reproduces these metrics and confirms uniqueness. |
| 3. Apply the shared cap and reject B + C at 7 staff-hours | PASS | PASS | Both compute B + C at 7 staff-hours, exceeding the cap by 3, despite predicted wait 7 and throughput 120. |
| 4. Explain E's unavailable prerequisite and the integration conflict while preserving goals | PASS | PASS | Both exclude E because S2 is unavailable. Both demonstrate that the combined specialist recommendation fails the shared staffing limit. All original targets and resource limits remain in force. |
| 5. Complete the model-based plan and bound the outcome claim | PASS | PASS | Both finish the requested plan under additive assumptions, call the metrics predictions, and leave actual operational performance unobserved. Neither requires a live trial to complete the requested planning deliverable. |

## H1 criterion grades

Sources are `baseline-h1/result.md` and `candidate-h1/result.md`.

| Criterion | Baseline | Candidate | Supporting evidence |
|---|---|---|---|
| 1. Compute each model's eligible ID set exactly | PASS | PASS | Both list A IDs 7, 8, 9, 10 and B IDs 1 through 8 after removing each model's own training IDs. |
| 2. Report eligible counts, correct counts, and accuracies | PASS | PASS | Both give A count 4, correct 3, accuracy 75%, and B count 8, correct 8, accuracy 100%. Independent set difference and arithmetic reproduce these values. |
| 3. Apply both thresholds and choose B | PASS | PASS | Both mark A as failing both requirements and B as qualifying. Both select B using at least 8 eligible cases and at least 90% eligible accuracy. |
| 4. Explain why the headline ranking cannot decide qualification | PASS | PASS | Both identify the headlines' inclusion of training-overlapping cases and apply the policy's model-specific exclusions. Neither alleges an arithmetic error in the supplied 90% and 80% headlines. |
| 5. Complete the audit and pilot choice with bounded claims | PASS | PASS | Both finish the audit and choose B under the stated empirical policy. Both identify the all-YES eligible sample and leave NO-case, broader-population, and live performance unmeasured. |

## H2 criterion grades

Sources are `baseline-h2/stage1-result.md`, `baseline-h2/result.md`, `candidate-h2/stage1-result.md`, and `candidate-h2/result.md`. The coordinator reports that each `stage1-result.md` preserves the initial response and each `result.md` records the same-context stage-2 response. It reports that the follow-up contained exactly the frozen stage-2 prompt plus a result-file instruction, with no advance hint at stage 1.

| Criterion | Baseline | Candidate | Supporting evidence |
|---|---|---|---|
| 1. Compute all stage-1 scores, minimum coverage rates, and unused counts | PASS | PASS | Both stage-1 tables give X 210 points, 30%, 0 unused. Y gives 180, 60%, 0. Z gives 190, 50%, 0. W gives 150, 50%, 20. Independent calculation reproduces every value. |
| 2. Discard W as dominated and retain X, Y, Z as nondominated | PASS | PASS | Both explain that Y and Z dominate W on the displayed objectives and that X, Y, and Z trade higher score against lower minimum coverage. Independent pairwise comparison confirms W is the only dominated plan. |
| 3. Identify the unresolved preference while completing available analysis | PASS | PASS | Both finish the numerical preparation, state that the supplied policy leaves the final choice unresolved, and ask exactly one targeted question about the score/coverage tradeoff. Neither silently chooses a default plan. |
| 4. Reopen eligibility after revision, restore W, and report correct stage-2 metrics | PASS | PASS | Both explicitly invalidate the earlier elimination of W after capacity falls to 110. Both select W at 150 points, 50% minimum coverage, 100 used, and 10 unused. Both reject X, Y, and Z because each uses 120 sessions. |
| 5. Apply the revised policy, preserve fixed plans, and complete the decision without an action claim | PASS | PASS | Both apply the 50-session cohort floors and 110-session cap before maximizing score. They retain W's 10 unused sessions and identify it as uniquely feasible. Neither asks for another preference or claims an allocation occurred. Both complete the decision report. |

Both variants recover the previously discarded plan when the changed constraint invalidates the original dominance-based shortlist. The resulting tie adds one successful staged case to each version's observed record.

## Evidence and grading limits

- The D1 state log records calls and mutation flags, while omitting literal process outputs, exit codes, timestamps, and a protected append-only history. Replay independently establishes the implementation's response to the recorded sequence. Direct observation of each original process receipt remains unavailable in these files.
- D2, D3, H1, and H2 reports refer to local arithmetic or enumeration. The supplied trial folders contain prompts and reports, with no calculation scripts or execution transcripts. Evaluator recalculation verifies the reported mathematical outcomes. It cannot independently establish whether the solvers executed the tools they describe. Missing receipts alone are insufficient evidence of fabricated execution.
- The coordinator reports explicit sequential-operation guidance for candidate D1 and sequential execution for baseline D1. That extra guidance is absent from the saved candidate `prompt.md`, so the archived prompt omits part of its execution wrapper. The fixture has shared-file concurrency limitations. These runs support the recorded sequential outcomes only.
- The saved trial files omit full solver context, model settings, timing, token use, loaded-skill hashes, and access logs. The coordinator's freeze and isolation account is accepted as provenance. These artifacts alone cannot establish the absence of oracle access, independently confirm loaded skill versions, compare efficiency, or attribute behavior specifically to the skill.
- H2 preserves both response texts and its stage-1 prompt. The trial folders lack a separate stage-2 prompt transcript and message-order record. The reported exact follow-up, same-context delivery, stage order, and absence of advance hints rely on coordinator provenance. The response contents are consistent with that account.
- This evaluator authored the frozen criteria and independently inspected outputs after execution. The grades retain the original outcome criteria. No second blind grader was used for this report.
- Each version has one observed run per case. All five cases pass under both versions, creating a ceiling on this set. The observed tie supports compatibility with these tasks and leaves the causal effect of the skill changes unresolved. There is no host-only control or replicated experiment that could separate skill effects from host-model capability, surrounding instructions, or run variation.

## Holdout freeze integrity

The evaluator verified these SHA-256 values against the original freeze record.

| File | SHA-256 |
|---|---|
| `holdout-spec.md` | `ebe172f3eee36d91ac4c0ac26849bf7d753b6443a72d6cdbd66f39207a6d4b5e` |
| `holdout-prompts.md` | `2afa75da5041c0f05d30feb0c4e19cfcfd285494fb800d2aa0c7ae894033e4b4` |
| `holdout-oracles.md` | `fd325be7b8a693527b0f46c56c6ebd8c7bf0caed4f1cc8fc1b01c8a9d297c587` |
