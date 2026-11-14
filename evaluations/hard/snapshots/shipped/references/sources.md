# Research basis

Checked November 14, 2026. The following are primary sources. Specific architecture choices, contracts, field names, and default limits in this package are proposed synthesis. None of these sources validates this package as a complete system.

| Source and locator | What it supports | Applicability limit |
|---|---|---|
| [Anthropic: Building effective agents](https://www.anthropic.com/research/building-effective-agents), December 19, 2024; routing, orchestrator-workers, evaluator-optimizer | Composable orchestration patterns and starting with simple solutions | Vendor engineering guidance; the page itself notes tooling changes since publication |
| [Anthropic: Building multi-agent systems](https://claude.com/resources/articles/building-multi-agent-systems-when-and-how-to-use-them), January 23, 2026; decision framework | Context isolation, parallelism and specialization as reasons for multiple agents | Vendor experience, not a universal guarantee of improvement |
| [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), RMF 1.0, 2023; Govern 2, Map 1, Measure 1–2 | Responsibilities, multidisciplinary expertise, proficiency, independent assessment, context-dependent measurement | Voluntary framework; the page says a revised version is in progress |
| [Principled Personas, EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1364/), abstract and paper | Inconsistent effects of expert personas and sensitivity to irrelevant attributes | Empirical results for studied models and tasks, not every future configuration |
| [NASA Systems Engineering Handbook, 2.4](https://www.nasa.gov/reference/2-0-fundamentals-of-systems-engineering/) | Distinguishing requirement verification from intended-purpose validation; inspection, test, analysis, demonstration | Systems-engineering principles adapted here to a general workflow |
| [W3C PROV-DM](https://www.w3.org/TR/prov-dm/), Recommendation, April 30, 2013; core model and derivation | Entities, activities, responsible agents, derivation, revision and invalidation | A provenance model records lineage; it does not prove truth |
| [Anthropic: Demystifying evals](https://www.anthropic.com/research/demystifying-evals-for-ai-agents), January 9, 2026; evaluation structure and graders | Environment-state outcomes, mixed grader types, repeated isolated trials and grader calibration | Evaluation guidance; grades depend on criteria and grader validity |
| [LangGraph: Persistence](https://docs.langchain.com/oss/python/langgraph/persistence), current documentation; checkpointers versus stores | Durable run state and the limits of in-memory checkpoints | Framework behavior must be checked against the installed version |
| [LangGraph: Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts), current documentation; pause/resume | Persisted waits for external input and resume identifiers | Does not grant authority or validate the resumed decision |
| [LangGraph: Fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance), current documentation; retry boundaries and idempotency | Durable action keys, bounded recovery and reconciliation of missing acknowledgements | External deduplication depends on provider behavior |
| [MCP: Security Best Practices](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices), versioned guidance; scope minimization, confused deputy, token handling | Constrained tool access and explicit authorization boundaries | Protocol-specific guidance, not a complete security audit of a host |

Each actual run needs its own domain and tool research. These references justify the orchestration approach; they do not replace professional standards, current pricing, environment checks, or task-specific evidence.

## Problem formulation and exploratory work

| Source and locator | What it supports | Applicability limit |
|---|---|---|
| [Felix Rieseberg, How to be more ambitious](https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/), October 13, 2026 | Motivation to examine outcomes, methods and adjacent disciplines | Practitioner essay with illustrative examples |
| [Working Backwards, Bryar and Carr excerpt](https://www.aboutamazon.com/news/workplace/an-insider-look-at-amazons-culture-and-processes), February 9, 2021 | Starting from the intended customer experience and investigating delivery constraints | Account of an organizational method |
| [Locke and Latham, Goal-setting theory](https://goal-lab.psych.umn.edu/orgPsych/2020/readings/5.%20Motivation/Locke%20%26%20Latham%20%282002%29.pdf), 2002, pp. 705–717 | Difficult specific goals, feedback, task complexity and learning strategies | Human research whose transfer to agents requires testing |
| [DeepMind, Specification gaming](https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/), April 21, 2020 | Examples of divergence between objective scores and intended results | Illustrative evidence, with no universal prevention guarantee |
| [Jackson and colleagues, Value of Information](https://arxiv.org/abs/1703.08994), 2017 preprint, JASA 2019 | Prioritizing information by its expected effect on decision loss | Formal estimates require an appropriate model and loss function |
| [Amdahl, 1967](https://www.cs.cmu.edu/~18742/papers/Amdahl1967.pdf) | Limits on whole-system gains from accelerating part of a computation | Applying the reasoning beyond computing requires measured process assumptions |

## Problem models and self-evaluation

| Source and locator | What it supports | Applicability limit |
|---|---|---|
| [Kambhampati et al., LLM-Modulo](https://arxiv.org/abs/2402.01817), ICML 2024, v3 | Combining language-model proposals with external model-based verifiers | Architecture position paper, with model adequacy still requiring validation |
| [Cemri et al., Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657), 2025, v3 | Diagnosing failures in system design, inter-agent alignment, and task verification | Taxonomy from studied systems, adapted here into a smaller repair procedure |
| [Kim et al., Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296), revised April 8, 2026, v3 | Coordination performance depends on task structure and configuration | Findings across six benchmarks, with no universal team-size rule |
| [Dwork et al., Generalization in Adaptive Data Analysis and Holdout Reuse](https://arxiv.org/abs/1506.02629), 2015, v2 | Adaptive reuse can overfit held-out evaluation data | This skill adopts fresh-case discipline and does not implement the paper's statistical algorithms |
| [Anthropic, Building strong safety evaluations](https://www.anthropic.com/research/building-strong-safety-evaluations), November 13, 2026 | Research-question alignment, grader checks, controlled comparisons, and reporting failures | Safety-evaluation guidance adapted to benign skill testing |
