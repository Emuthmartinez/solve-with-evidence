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

## Deliver a checked JSON file

For a machine-readable JSON object, the skill can deliver a file directly from the buffer the recipient’s checker accepted. Codex gives the user the file link. There is no second copy of the JSON in the final chat message. From the installed skill directory, a caller can run

```sh
python3 scripts/json_handoff.py candidate.json --deliver-to outputs -- python3 your_consumer.py
```

Supply a validator you trust for this recipient. It reads stdin, returns 0 for acceptance, 1 for a rejected submission, and 2 for an unavailable check. On success the command returns the absolute file path, SHA-256 and byte count. Link that path in a persistent, caller-owned output directory. Reusing the same checked bytes returns the same file. A rejected input produces no receipt. For other JSON root types or other formats, use the trusted consumer and a byte-preserving delivery path suited to that format.

Hosts that require inline JSON can omit `--deliver-to` and forward the command’s accepted stdout unchanged. A normal chat message composed by a model cannot provide that inline transport guarantee. [Release tests and full traces](evaluations/delivery/README.md) · [Earlier failures and repair evidence](evaluations/hard/handoff/README.md)

## Evidence

The current release delivered the checker-approved bytes in 12/12 normal trials, compared with 9/12 for the previous release. Both versions preserved the checked file in all six native Codex shell trials. The updated skill also withheld both payloads during simulated checker outages. [Delivery benchmark and traces](evaluations/delivery/README.md)

In the previous release’s benchmark in [evaluations/hard/README.md](evaluations/hard/README.md), six versions produced 182 completed two-turn trials across 17 cases. That release’s instructions passed 32/34 trials and 453/466 points. The installed baseline passed 34/34 trials and 466/466 points. The cases use synthetic inputs, restricted tools, and two trials per cell. They do not estimate reliability across professions, open-web research, distributed execution, or deployment.

An earlier self-audit is in [evaluations/README.md](evaluations/README.md). Design notes are in [evaluations/general-solver-design.md](evaluations/general-solver-design.md).

## Package

- [Skill instructions](solve-with-evidence/SKILL.md)
- [Architecture](solve-with-evidence/references/architecture.md)
- [Delegation and completion contracts](solve-with-evidence/references/contracts.md)
- [Validation cases and completed checks](solve-with-evidence/references/validation.md)
- [Research sources](solve-with-evidence/references/sources.md)
