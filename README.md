# Solve with Evidence

A reusable Codex skill for taking a problem through understanding, expert selection, research, coordinated execution, and verified results.

## Use

In Codex, ask `$skill-installer` to install `solve-with-evidence` from `Emuthmartinez/solve-with-evidence`, using the repository path `solve-with-evidence`. Start a new chat and invoke it with

```text
$solve-with-evidence Help me solve [your problem].
```

The skill can also be selected automatically for relevant requests.

## Package

- [Skill instructions](solve-with-evidence/SKILL.md)
- [Architecture](solve-with-evidence/references/architecture.md)
- [Delegation and completion contracts](solve-with-evidence/references/contracts.md)
- [Validation cases and completed checks](solve-with-evidence/references/validation.md)
- [Research sources](solve-with-evidence/references/sources.md)
- [Repeated benchmark results and full observable traces](evaluations/hard/README.md)
- [Earlier self-audit and evaluation limits](evaluations/README.md)
- [General problem-solver design advisory](evaluations/general-solver-design.md)

## Exact JSON handoffs

When another program consumes an answer, route the received bytes through the included checker before forwarding them. Supply a trusted validator for the recipient’s schema and behavior. From the installed skill directory, run

```sh
python3 scripts/json_handoff.py received.json -- python3 your_consumer.py > accepted.json
```

Forward the output after exit code 0. Codex does not automatically intercept the final chat response. A host or caller must wire this step into delivery. The repository includes a replay showing which published model answers it caught and how each replacement was obtained. [Checker and replay guide](evaluations/hard/handoff/README.md)
