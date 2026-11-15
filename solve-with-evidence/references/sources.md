# Sources and prior work

None of the mechanisms in this skill is new. What it does is combine them: checks written before the work, checks that must reject a plausible bad answer, delivery that fails closed, and all of it as portable instructions instead of a framework. Nothing below validates the combination. Each run still needs its own research into the user's domain.

## Prior work this method assembles

arXiv records checked November 15, 2026.

| Idea in this skill | Established name | Source |
|---|---|---|
| Classify the problem before solving it | Problem-class routing, representation selection | Pólya, *How to Solve It*, 1945. [Zhou et al., Self-Discover](https://arxiv.org/abs/2402.03620), 2024 |
| Step back to the general problem first | Abstraction-first prompting | [Zheng et al., Take a Step Back](https://arxiv.org/abs/2310.06117), 2023 |
| Solve, then check against something outside the model | Generator and verifier separation | [Kambhampati et al., LLM-Modulo](https://arxiv.org/abs/2402.01817), 2024. [Gou et al., CRITIC](https://arxiv.org/abs/2305.11738), 2023. [Dhuliawala et al., Chain-of-Verification](https://arxiv.org/abs/2309.11495), 2023 |
| A model needs an outside signal to fix its own errors | Limits of self-correction | [Huang et al.](https://arxiv.org/abs/2310.01798), 2023. [Kamoi et al.](https://arxiv.org/abs/2406.01297), 2024 |
| Slower runs can let a weaker model do more | Test-time compute traded for model size | [Snell et al.](https://arxiv.org/abs/2408.03314), 2024 |
| One model directing its own sub-tasks | Scaffolding, meta-prompting | [Suzgun and Kalai, Meta-Prompting](https://arxiv.org/abs/2401.12954), 2024 |

The self-correction results are why the skill requires an external check or an independent reviewer, and why it withholds or lists what could not be checked.

## Design sources

Checked November 14, 2026.

| Source | What it supports | Limit |
|---|---|---|
| [Anthropic, Building effective agents](https://www.anthropic.com/research/building-effective-agents), 2024 | Starting simple. Routing, orchestrator and evaluator patterns | Vendor engineering guidance |
| [Anthropic, Building multi-agent systems](https://claude.com/resources/articles/building-multi-agent-systems-when-and-how-to-use-them), 2026 | Context isolation, parallelism and specialization as reasons for more agents | Vendor experience |
| [Kim et al., Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296), revised 2026 | Coordination gains depend on task structure | Six benchmarks. No universal team-size rule |
| [Principled Personas](https://aclanthology.org/2025.emnlp-main.1364/), EMNLP 2025 | A role prompt is not competence | Studied models and tasks |
| [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), 2023 | Independent assessment and context-dependent measurement | Voluntary framework |
| [NASA Systems Engineering Handbook, 2.4](https://www.nasa.gov/reference/2-0-fundamentals-of-systems-engineering/) | Requirement verification is distinct from intended-use validation | Adapted from systems engineering |
| [Cemri et al., Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657), 2025 | Locating a failure before repeating work | Taxonomy from studied systems |
| [DeepMind, Specification gaming](https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/), 2020 | A score can diverge from the intended result | Illustrative examples |
| [MCP, Security Best Practices](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices) | Retrieved content and tools do not grant authority | Protocol-specific guidance |

## Evaluation sources

| Source | What it supports | Limit |
|---|---|---|
| [Anthropic, Demystifying evals](https://www.anthropic.com/research/demystifying-evals-for-ai-agents), 2026 | Grading resulting state, mixed graders, repeated isolated trials | Grades depend on grader validity |
| [Anthropic, Building strong safety evaluations](https://www.anthropic.com/research/building-strong-safety-evaluations), 2026 | Aligning tests with the question, checking graders, keeping failures | Safety-evaluation guidance adapted here |
| [Dwork et al., Holdout Reuse](https://arxiv.org/abs/1506.02629), 2015 | Adaptive reuse overfits held-out data | This skill uses fresh-case discipline, not the paper's algorithms |
