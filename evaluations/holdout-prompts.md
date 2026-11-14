# Frozen held-out raw prompts

Give a solver only the indicated case and stage. H2 stage 2 must arrive in the same solver context after its stage-1 response.

## H1

Use Solve with Evidence to select the qualifying model for a small, fictional document-labeling pilot. The policy accepts a model only if it is at least 90% correct on at least eight distinct evaluation cases that are absent from that model's training set. Training overlap is the only contamination channel in this controlled fixture. All predictions were fixed before evaluation labels were revealed, and the records were not used for any later tuning. Apply the policy exactly and state the limits of what the result proves.

Evaluation cases are IDs 1 through 10. Every case's correct label is YES. Model A predicted YES on IDs 1 through 9 and NO on ID 10. Its training IDs were 1 through 6. Model B predicted YES on IDs 1 through 8 and NO on IDs 9 and 10. Its training IDs were 9 and 10.

The summary sheet ranks A above B, citing 90% versus 80% headline accuracy. Produce a compact audit table containing each model's eligible evaluation IDs, eligible count, correct eligible count, eligible accuracy, and qualification result. Select a model if the policy supports one. The requested deliverable is this audit and pilot choice. There is no live deployment in scope.


## H2 stage 1

Use Solve with Evidence to prepare a decision on allocating 120 optional tutoring sessions across two fictional workshop cohorts. Each cohort has 100 participants who could use one session. The approved priority score gives each served morning-cohort participant two points and each served evening-cohort participant one point. Leadership also wants a fair allocation, but has not specified how fairness should trade off against the priority score.

The available plans are fixed. Sessions cannot be split, no other plans can be created, and these plans have no cost or operational differences beyond the allocations listed.

| Plan | Morning sessions | Evening sessions |
|---|---:|---:|
| X | 90 | 30 |
| Y | 60 | 60 |
| Z | 70 | 50 |
| W | 50 | 50 |

Compute each plan's priority score, lowest cohort coverage percentage, and unused sessions. Identify which plans can be discarded without resolving the tradeoff. State whether the supplied policy determines a unique final choice. Complete the numerical decision preparation and ask at most one question if a leadership preference is indispensable. Do not allocate sessions or contact anyone.


## H2 stage 2

Leadership has now specified a minimum of 50 sessions for each cohort. It also corrected the total available sessions from 120 to 110. After satisfying those two limits, maximize the approved priority score. The four named plans remain fixed and sessions cannot be added to or moved between them. Finish the decision report under these revised requirements. No allocation action is authorized.
