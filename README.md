# Solve with Evidence

A portable skill that takes a multi-step problem from clarification and expert selection through current research, coordinated execution, integration, and evidence-based verification. It uses a seven-step loop at the depth the problem needs. These instructions grant no new authority, access, credentials, budget, or professional qualification.

## When to use

Use it when the work crosses disciplines, requires tool or method selection, or needs a defensible outcome.

## When not to use

Scale the loop down, or skip the research survey, for simple, directly checkable requests. This package is a skill plus contracts and evaluation records, not a running orchestration service. A completed plan is not evidence that the plan was executed.

## Install

The installable skill is the [`solve-with-evidence/`](solve-with-evidence/SKILL.md) directory, which contains `SKILL.md`, `references/`, and `scripts/`. That path is the skill folder, not the repository root.

### Codex

In a Codex session, ask the bundled installer to fetch that folder:

```text
$skill-installer install https://github.com/Emuthmartinez/solve-with-evidence/tree/main/solve-with-evidence
```

Start a new chat and invoke it with

```text
$solve-with-evidence Help me solve [your problem].
```

The skill can also be selected automatically when a request matches its description. See the [Codex skills documentation](https://developers.openai.com/codex/skills).

### Claude Code

Copy the same folder to `~/.claude/skills/solve-with-evidence/` for personal use, or to `.claude/skills/solve-with-evidence/` in a repository, so the file sits at `skills/solve-with-evidence/SKILL.md`. Invoke it with `/solve-with-evidence`. See the [Claude Code skills documentation](https://code.claude.com/docs/en/skills).

### Cursor

Copy the same folder into one of the skill directories Cursor loads: `.cursor/skills/`, `.agents/skills/`, `~/.cursor/skills/`, or `~/.agents/skills/`. In Agent chat, type `/` and select `solve-with-evidence`. See the [Cursor skills documentation](https://cursor.com/docs/skills).

## Example

```text
$solve-with-evidence Compare these venue offers against capacity, step-free access, and a fixed budget. Recommend a venue only if it satisfies every hard constraint.
```

If no offer qualifies, the skill should report that rather than relax the limits.

## Exact JSON handoffs

When another program consumes an answer, route the received bytes through the included checker before forwarding them. Supply a trusted validator for the recipient’s schema and behavior. From the installed skill directory, run

```sh
python3 scripts/json_handoff.py received.json -- python3 your_consumer.py > accepted.json
```

Forward the output after exit code 0. Codex does not automatically intercept the final chat response. A host or caller must wire this step into delivery. On 28 archived stage answers from the affected transfers, it accepted 21 as received and rejected all seven defective answers ([evaluations/hard/README.md](evaluations/hard/README.md); [checker and replay guide](evaluations/hard/handoff/README.md)).

## Evidence

On the repeated benchmark in [evaluations/hard/README.md](evaluations/hard/README.md), six versions produced 182 completed two-turn trials across 17 cases. The shipped instructions passed 32/34 trials and 453/466 points. The installed baseline passed 34/34 trials and 466/466 points. The cases use synthetic inputs, restricted tools, and two trials per cell. They do not estimate reliability across professions, open-web research, distributed execution, or deployment.

An earlier self-audit is in [evaluations/README.md](evaluations/README.md). Design notes are in [evaluations/general-solver-design.md](evaluations/general-solver-design.md).

## Package

- [Skill instructions](solve-with-evidence/SKILL.md)
- [Architecture](solve-with-evidence/references/architecture.md)
- [Delegation and completion contracts](solve-with-evidence/references/contracts.md)
- [Validation cases and completed checks](solve-with-evidence/references/validation.md)
- [Research sources](solve-with-evidence/references/sources.md)
