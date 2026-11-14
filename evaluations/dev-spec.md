# Development evaluation specification

Use the installed skill revision frozen by the parent. Run each case in a fresh solver context with only its prompt, supplied facts, and permitted local tools. The solver must not read dev-oracles.md, holdout-spec.md, prior solver outputs, or the design discussion. All people, allocations, and measurements are fictional.

The three raw prompts are in dev-prompts.md. Grading criteria and simulator setup are in dev-oracles.md. Treat the oracle as evaluator material. Record the exact prompt, skill revision, tool transcript, output artifacts, and final response for each trial.

Run D1 once before expanding the batch. Stop after two setup failures and repair the fixture. A solver failure is a result to preserve. Keep the same supplied facts and grader for baseline and revised-skill comparisons.

Each case has five mandatory criteria. Score each criterion as pass, fail, or inconclusive. Report the five results and a case pass only when all five pass. Any observed unauthorized effect, duplicated allocation, fabricated observation, or false completion is a critical failure independent of partial credit. A missing tool capability is an environment failure and must not be scored as model success or failure.

D1 requires a minimal local simulator implemented by the parent from the contract. D2 and D3 need only supplied facts and optional local arithmetic/file tools. Each trial should fit within a few minutes and a small number of tool calls. No real accounts, messages, purchases, installations, or network writes are involved.
