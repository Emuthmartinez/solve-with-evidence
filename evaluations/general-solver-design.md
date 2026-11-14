# Designing an expert general problem solver

An expert solver needs a way to express the problem, choose a method, act through available tools, and check whether the result serves the user's goal. Keep the existing coordinator, run record, capability registry, scheduler, tool gateway, and verifier. Improve the decisions they make using the following additions.

## Choose a testable representation

Before selecting experts, identify the structure of the problem. Scheduling needs variables, allowed assignments, constraints, and an objective. Diagnosis needs competing explanations and observations that distinguish them. Research needs claims, source lineage, and applicability conditions. Creative work needs an audience, a brief, and a rubric that permits different good answers. Operational work needs current state, allowed transitions, invariants, and recovery behavior.

Check the representation against the original request. An optimizer can return a feasible solution while its model omits the user's fairness requirement. A factual synthesis can accurately summarize sources whose populations do not match the intended use.

The LLM-Modulo proposal combines language-model candidates with external model-based verifiers. It motivates this division of responsibilities. The representation choices here are a design adaptation that requires task-level testing. [Kambhampati et al., ICML 2024](https://arxiv.org/abs/2402.01817)

## Route by capability and task coupling

An expert assignment should name the required operation, relevant method, available tools, input versions, owned output, and acceptance test. Use representative results to establish capability. Keep professional qualification explicit when a task requires it.

Parallel research benefits from distinct questions and clear source responsibilities. A tightly coupled sequence of state changes may work better with one executor and an independent reviewer. Measure whether extra coordination improves the result enough to justify its cost. A controlled study across six benchmarks found substantial variation in the benefit of agent coordination by task and configuration. [Kim et al., revised April 2026](https://arxiv.org/abs/2512.08296)

## Diagnose failed verification

Locate the failure before expanding the team or retrying the method. Check the goal, problem model, evidence, method, execution, integration, and verifier. When several causes fit the evidence, choose a bounded check whose results would distinguish them. Update affected conclusions and preserve valid independent work.

The MAST study categorizes failures in system design, inter-agent alignment, and task verification. The smaller set of repair questions above adapts that perspective to this skill. Its value should be measured through failures that it helps diagnose. [Cemri et al., 2025](https://arxiv.org/abs/2503.13657)

## Improve through controlled comparisons

Freeze the baseline, candidate, task inputs, relevant environment settings, and grading criteria. Give solvers the task and tools. Give independent graders the answer key, raw outputs, action trace, and final state. Preserve failures and record the number of attempts.

Use exposed cases for development and regression. Once a held-out result influences a revision, use fresh cases to evaluate that revision's generalization. Adaptive reuse can overfit a holdout set. This procedure applies that finding without claiming the statistical guarantees of specialized adaptive-analysis methods. [Dwork et al., 2015](https://arxiv.org/abs/1506.02629)

Record environmental outcomes as well as transcripts. A correct-looking response cannot establish that a write committed, and a timed-out call can still have changed state. Graders need evidence suited to the claim, including deterministic checks, bounded judgment, and qualified human review when necessary. [Anthropic, Demystifying evals](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)

## Applying this advice

The revised skill adds problem representations, task-coupling guidance, failure diagnosis, and an explicit self-evaluation procedure. It also clarifies two portability details identified in the document audit. Tool and worker content must be checked against governing authority. Unrelated changes to the run's storage revision must trigger a compatibility check before a valid independent result is discarded.

These are bounded changes to an instruction package and orchestration specification. The accompanying evaluation report records the cases tested, failures observed, and remaining limits. A deployed general solver would still need implemented adapters, durable state, concurrency enforcement, domain-specific verifiers, and representative operational evaluation.
