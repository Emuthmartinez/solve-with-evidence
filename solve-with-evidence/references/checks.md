# Problem types and their checks

This expands step 1 and step 2 of the skill. The routing table and the rules here are design choices. The cited work supports individual ideas. It does not show that this whole method works. That is what [the benchmark](validation.md) is for.

## Scale to complexity and consequence

Judge two things separately: how much coordination the work needs, and what a wrong answer costs. A small task can have serious consequences. A large document can be easy to undo.

| Profile | Setup | Evidence depth |
|---|---|---|
| Compact | One agent, a short note of the goal, the type and the check | Direct inspection or calculation, and one outcome check |
| Coordinated | A coordinator and a few workers with [contracts](contracts.md) | A check per part, interface checks, and a final check of the whole |
| Consequential | Either size, with restricted tools and independent review | Primary evidence, a representative trial, stated uncertainty, a readback of current state |

Add a worker only when its contribution is worth the context transfer and coordination. Multi-agent gains vary with task structure, so keep tightly ordered state changes with one executor ([Kim et al.](https://arxiv.org/abs/2512.08296)). A prompted persona is not a competence certificate ([Principled Personas](https://aclanthology.org/2025.emnlp-main.1364/)).

## Routing a request

1. Write down the product of the work: an answer, a recommendation, an artifact, a change, or an observed improvement. Keep that distinction to the end.
2. Split the request into parts by the operation each one needs: build, choose, explain, find out, write, change. Each part gets one type from the table in `SKILL.md`.
3. For each part, write the check before the method. If you cannot write a check that could reject a bad result, the type is probably wrong, or the part is unverifiable here. Say which.
4. State the chosen type in the plan and the report. A reader who sees the type can catch a wrong route. A wrong route is otherwise invisible, because its check passes.

Reroute when new evidence changes what the part is. A "writing" task that turns out to hinge on a disputed figure has a "facts" part inside it.

## Notes by type

**Executable artifact.** Derive expected results without the code under test: by hand, from the specification, or from a second implementation. Run the entry point the recipient will use. A test that passes on a different copy proves nothing about the delivered bytes.

**Decision under constraints.** Check that the model kept every real constraint before trusting its answer. A feasible schedule can still omit a requirement. Recompute totals from the source figures. Language models propose and external checkers verify ([LLM-Modulo](https://arxiv.org/abs/2402.01817)).

**Diagnosis.** Write down at least two explanations and what each predicts. Look for the observation that separates them. A before-and-after association supports a description, not a cause.

**Facts and research synthesis.** Every claim points to a passage. Repeated coverage of one study is one evidence chain. Classify each source by what it can establish:

| Source | Establishes | Does not establish |
|---|---|---|
| Current official documentation | Supported behavior, versions, limits | Performance in the user's environment |
| Standards and professional guidance | Recognized procedure and its boundaries | That it applies in this jurisdiction or is current |
| Primary empirical research | Findings under its stated conditions | The same result elsewhere |
| Vendor case study, community material | Leads and failure modes to test | Anything, until corroborated |

**Writing and design.** Judgment is real here, so make it inspectable. Write the audience and the brief. Collect good and bad exemplars and record them as evidence ([contracts](contracts.md)). Write a rubric and confirm it ranks the good exemplars above the bad ones. Then have an independent reviewer apply it. Where taste is the user's, the user picks. Facts inside the prose still follow the facts row.

**Operational change.** Check preconditions and authority immediately before acting. Read back the final state from the system itself. A returned success code is a receipt, not an outcome.

## Three questions for every check

| Question | Typical evidence |
|---|---|
| Suitability: does the method fit this problem and this data? | Input checks, version check, a small pilot |
| Execution: was it applied correctly? | A reproducible calculation, a test of the artifact |
| Outcome: did it meet the user's goal? | Intended-use test, observed state, measured change |

Also check the parts together. Correct parts can fail when combined: units, populations, versions and interfaces must agree. Requirement checks and intended-use checks are different things ([NASA Systems Engineering Handbook, 2.4](https://www.nasa.gov/reference/2-0-fundamentals-of-systems-engineering/)).

## Rubrics and exemplars

A rubric is a check, so it must be able to fail. Before relying on one, score at least one good and one bad exemplar with it. A rubric that does not separate them is invalid, and its scores are not evidence.

Three ways a rubric goes wrong over time:

- A rubric judge rewards writing to the rubric.
- A banned-phrase list produces the next cliché.
- Exemplars that shaped the instructions stop being a fair test of them.

So hold some exemplars back, and rotate them ([specification gaming](https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/)).

## Independent review

Models correct their own errors reliably only with an outside signal ([Huang et al.](https://arxiv.org/abs/2310.01798), [Kamoi et al.](https://arxiv.org/abs/2406.01297)). Review is that signal only when it is independent:

1. The reviewer is not the author. Prefer a different model family. Record which model reviewed.
2. The reviewer receives the original request, the checks, the output and the raw evidence. It forms a verdict from those.
3. The author's rationale is shown afterwards. The reviewer notes whether it changed the verdict and why.
4. A review of an old version does not cover a new one. Recheck after material changes.

A same-family review still catches slips. Report it as a same-family review.

## After a failed check

Locate the fault in one of seven places: the goal, the problem type, the evidence, the method, the execution, the integration, or the check. Test competing causes before repeating the work. Fix that part and recheck what depends on it. Keep the failed result on record. A revised check must still reflect the original requirement ([Cemri et al.](https://arxiv.org/abs/2503.13657)).

## When to stop researching

Stop when the questions that could change the method or the check are answered well enough to act, or when the stated budget runs out. Say which. Unresolved uncertainty goes in the report, not away.
