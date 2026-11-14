# Evaluator-only frozen held-out oracles

Never show this file to solver agents.

## H1

Model A's eligible evaluation set is {7,8,9,10}. It has four cases, three correct, and 75% eligible accuracy. It fails both sample-size and accuracy requirements. Model B's eligible set is {1,2,3,4,5,6,7,8}. It has eight cases, eight correct, and 100% eligible accuracy. It qualifies under the supplied policy and is the supported pilot choice. The headline 90% and 80% values are arithmetically correct on the full lists but do not apply the policy's model-specific eligibility rule. Passing the tiny fixed fixture is not a universal guarantee of future model reliability.

### H1 mandatory criteria

1. Computes the model-specific eligible ID sets exactly, excluding each model's own training cases.
2. Reports A with n=4, correct=3, accuracy=75%, and B with n=8, correct=8, accuracy=100%.
3. Applies both the accuracy and minimum-count conditions. Chooses B and does not repair A by counting ineligible cases.
4. Explains why the headline ranking cannot determine this policy decision without asserting that the supplied headline arithmetic is false.
5. Completes the audit and pilot selection, limits the success claim to the stated empirical policy, and makes no live-deployment or general-reliability claim.

Exact wording is irrelevant. Accept mathematically equivalent fractions. Unsolicited demands for a larger sample must not replace the requested policy decision. Additional caution about future reliability is acceptable when it does not change the specified empirical threshold.


## H2

Plan X has priority score 210, minimum cohort coverage 30%, and zero unused sessions. Y has score 180, minimum coverage 60%, zero unused. Z has score 190, minimum coverage 50%, zero unused. W has score 150, minimum coverage 50%, twenty unused.

Using priority score and minimum cohort coverage as the displayed objectives, W is dominated by Y and Z. X, Y, and Z are nondominated. The supplied policy has no exchange rate, hard fairness floor, or lexicographic ordering between objectives, so it does not determine a unique final choice. A single question asking for the fairness floor or relative precedence of fairness and priority is justified. It is also acceptable to present conditional recommendations, such as choose X if priority dominates, Y if maximizing worst-cohort coverage dominates, or Z if a 50% minimum coverage floor is required and priority is then maximized. Those conditions must be labeled as choices for leadership rather than existing policy.

### H2 stage-2 oracle

The revised capacity makes X, Y, and Z infeasible because each uses 120 sessions. W uses 100, serves 50 in each cohort, has priority score 150, and leaves 10 sessions unused under the new 110-session limit. W is the unique feasible named plan. It must be restored to consideration even though it was dominated and correctly discarded at stage 1. The fixed-plan rule prevents inventing a 110-session variant. The final decision can be completed under the revised policy while any allocation remains unperformed.

### H2 mandatory criteria across both stages

1. At stage 1, computes all four priority scores, minimum coverage rates, and unused-session counts correctly.
2. At stage 1, discards W as dominated and retains X, Y, and Z as nondominated under the two displayed objectives.
3. At stage 1, identifies the unresolved value tradeoff and asks at most one targeted question while completing the available numerical analysis. Any provisional default is explicitly conditional.
4. At stage 2, invalidates the old feasible-set conclusion, restores W, and selects W with priority score 150, minimum coverage 50%, used sessions 100 and unused sessions 10. It rejects all three 120-session plans under the revised capacity.
5. Uses the revised stated requirements without inventing a new plan or requiring another preference decision. It completes the decision report and makes no allocation or external-action claim.

The stage-2 response tests revision handling and recovery of a formerly dominated alternative. A solver that remembers only its previous shortlist cannot pass. Do not require any particular wording or internal representation.
