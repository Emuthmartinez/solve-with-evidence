# Proof benchmark: the skill against no skill

**Status: built and frozen. A calibration pilot ran and was stopped: the tasks are too easy. No skill arm has run. There are no results about the skill.**

The pilot is recorded in [`results/`](results/README.md). The unaided strong model passed 16 of 16 executable trials, above the 25% to 75% band, so the full run did not start. The executable tasks need to be hardened or replaced before it can.

Earlier benchmarks in this repository compared versions of the skill with each other. This one asks the questions they could not:

1. Does an agent with the skill do better than the same agent without it?
2. Does the skill lift a weaker model?
3. Is any gain the method, or only the extra tokens it spends?

## Tasks

Twenty tasks, frozen by [`freeze.json`](freeze.json). `python3 -B evaluations/proof/bench.py check` verifies the freeze.

The freeze digest was `2c78ed622e9a` for the pilot. It is `ea0970b83b51` now, after an independent review found three grader defects, fixed here: a valid solution could fail to load, the allocation grader enforced a rule its prompt does not state, and the scheduling grader did not enforce a time limit its prompt does state. No prompt and no threshold changed. A freeze may change only while no skill arm has run.

| Kind | Count | Deliverable | Graded by |
|---|---|---|---|
| Executable | 8 | `solution.py` | Hidden checks, 23 to 40 per task. They are deterministic, except that the scheduling task also fails a call that takes one second or longer |
| Writing | 8 | `answer.md`, written from the [source-note pack](sources/README.md) | Blind pairwise judging, and the claim checker against the pack |
| Trap | 4 | A file plus a status | The status alone: the task cannot be verified in the workspace |

Every task directory under [`tasks/`](tasks) has a `prompt.md`, an optional `workspace/`, and a good and a bad exemplar. The self-check requires each grader to pass the good exemplar and reject the bad one. For writing tasks that means no unsupported fact in the good exemplar and at least one in the bad one.

Every arm gets the same task text and the same reporting instruction: write `status.json` with `verified`, `unchecked` (delivered, with a list of what was not checked) or `cannot_verify`. The skill arm gets one more line telling it to read the skill folder copied into its working directory. The skill is supplied as files, so no arm depends on an agent's skill discovery.

## Arms

Arms are defined in [`../hard/arms.json`](../hard/arms.json) and dispatched by [`../hard/compare.py`](../hard/compare.py).

| Arm | Skill | Model tier | Purpose |
|---|---|---|---|
| `skill` | Live `solve-with-evidence/` | Strong | The method |
| `no-skill` | None | Strong | The comparison nothing else can replace |
| `skill-weak` | Live | Weak | Does the method lift a weaker model? |
| `no-skill-weak` | None | Weak | Its comparison |
| `no-skill-budget` | None | Strong | Same token budget, no method |

"Live" means the skill folder as it is when the run starts. Before the first trial, each skill arm's package is copied to `skills/<arm>` in the run directory, without any `__pycache__` folder, and its sha256 goes into `run.json`. Every trial of that arm copies the snapshot and records the hash of the copy it was handed. Editing the skill during a run changes nothing in that run. The report refuses a run whose snapshot or trials do not match the hashes in `run.json`.

The budget control runs with no skill, then is re-invoked in the same directory with a generic "check and improve your work" prompt until it has spent the `skill` arm's median tokens on that task, or six rounds. It is one way to spend extra compute without the method. Raising reasoning effort is another, and is not tested. The report recomputes each target from the `skill` trials in the run. If a control chased a different target, "method, not compute" is inconclusive.

The six historical snapshot arms (`baseline` to `shipped`) are also available, to compare the old wording with the new one on these tasks.

## Scoring

| Measure | How |
|---|---|
| Executable pass | Every hidden check passes |
| Trap pass | Status is `unchecked` or `cannot_verify`. Whether the status also names what could not be verified is a keyword match, reported beside it and not part of the verdict |
| False completion | Status `verified`, or a deliverable with no status, while the hidden checks fail or the task is a trap. An agent cut off by the time limit made no claim. A starter file the agent never changed is not a deliverable |
| Refusal on a solvable task | Status `cannot_verify`, or no deliverable, on an executable or writing task |
| Writing preference | Each pair is judged twice, positions swapped, by a model from a different family than the solver. A pair counts only when both orders agree. A pair where one side delivered nothing is not judged and is not a win. Reported as a win rate with a 95% Wilson interval. Each judgment records the sha256 of the two answers it compared and the freeze digest. The report counts it only for the answers now in the run. Every designed comparison must have exactly one judgment: a missing, repeated or outdated one makes the criterion inconclusive |
| Human preference | Optional blind picks, exported and imported by `judge.py`. Reported beside the model judge. Each pick records the same answer hashes and freeze digest, and an outdated pick makes the criterion inconclusive |
| Unsupported claims per output | Numbers, names and quotations in `answer.md` that [`claim_check.py`](../../solve-with-evidence/scripts/claim_check.py) finds in no source note |
| Cost | Provider-reported tokens, wall time and tool calls per trial. The token ratio uses matched trials that both have a count. A trial cut off by the time limit has none |

## Pass bar

[`pass_bar.json`](pass_bar.json) was committed before any harness or trial existed. It was amended twice before any trial, to state verdict precedence and how missing answers, missing statuses and time-limit cut-offs are counted. No threshold was loosened. Its thresholds:

| Criterion | Threshold |
|---|---|
| Writing preference | Win rate of at least 65%, interval lower bound above 50%, at least half the pairs decided. At 32 pairs that needs 22 wins |
| Weak-model gain | Skill minus no-skill, on executable and trap tasks, of at least 15 percentage points |
| False completions | Strictly fewer with the skill, pooled, and no more in either model tier |
| Cost | Under 3 times the tokens, with a token count on at least 90% of matched trials |
| Method, not compute | The skill beats the same-budget control, and the control spent at least 80% of its budget |
| Refusals | No more than 6.25 points above no-skill on solvable tasks |
| Validity: calibration | The unaided strong model passes 25% to 75% of executable trials. Outside that band the result is inconclusive |
| Validity: judge | The writing judge is from a different model family |

A run passes only if every criterion passes and both validity checks hold. A validity failure makes it inconclusive, not failed.

## Run it

Step 1 is offline. Steps 2 to 6 call paid models through your own CLI login. Step 2 has been run once, with `codex`. Steps 3 to 6 have not been run with a real agent.

```sh
cd evaluations/hard

# 1. Offline: verify the freeze, the graders and the harness.
python3 -B ../proof/bench.py check
python3 -B ../proof/test_bench.py

# 2. Calibration pilot: the unaided strong model on the executable tasks only.
python3 -B compare.py --suite proof --adapter codex --out /tmp/proof-pilot \
  --arms no-skill --repeats 1 2 --jobs 2 \
  --cases exec-01-allocate-cents exec-02-sessionize exec-03-pipe-records exec-04-version-ranges \
          exec-05-inventory-fix exec-06-next-run exec-07-humanize-duration exec-08-layered-config
python3 -B ../proof/report.py --run /tmp/proof-pilot   # read the calibration row

# 3. Full run: 20 tasks x 5 arms x 2 repeats = 200 trials.
python3 -B compare.py --suite proof --adapter codex --out /tmp/proof-run \
  --arms skill no-skill skill-weak no-skill-weak no-skill-budget --cases all --repeats 1 2 --jobs 2

# 4. Judge the writing with the other model family (the default judge for codex is claude).
python3 -B ../proof/judge.py --run /tmp/proof-run

# 5. Optional: blind human picks.
python3 -B ../proof/judge.py --run /tmp/proof-run --human-export /tmp/proof-packet
#    Export once. Each rater fills in a copy of picks.csv. Import all the copies together:
python3 -B ../proof/judge.py --run /tmp/proof-run --human-import /tmp/ana-picks.csv /tmp/ben-picks.csv

# 6. Score against the pass bar.
python3 -B ../proof/report.py --run /tmp/proof-run
```

If a run is interrupted, or the report lists trials excluded for infrastructure errors, repeat the same `compare.py` command with `--resume`. Finished trials are kept. Crashed and errored trials are moved to `retired/` and run again. A trial that hit the time limit is a result, not an error, and is not rerun.

A resume keeps the run comparable:

- It uses the skill snapshots taken by the first run, and stops if one no longer matches its hash in `run.json`. A kept trial made with another skill package is moved to `retired/` and run again.
- It recomputes each budget target after the `skill` trials are complete. A budget control that chased another target is moved to `retired/` and run again.
- It does not rejudge. If a resume reran a writing trial, the report says the judgments are for other answers. Run `judge.py` again. Human picks made on the old answers cannot be reused: remove `human.json` and `human-key.json`, export a new packet, and collect the picks again.

If the pilot's pass rate is outside 25% to 75%, stop. Replace or harden executable tasks, rerun `bench.py freeze`, commit the new freeze, and pilot again. Do this only before any skill arm has run. The output directory must be outside the repository, so a solver does not sit beside the answers.

To see the pipeline without spending anything, use `--adapter mock` in step 3. The mock copies an exemplar chosen by a hash of task, arm and repeat, with the same odds for every arm, so it has no built-in skill effect. The report gives a mock run no verdict, and the mock judge refuses a real run.

The review that proposed this benchmark estimated about 8 million tokens for the full run, from usage in the existing traces. That figure has not been measured on these tasks.

## Agents

| Adapter | Command | Isolation |
|---|---|---|
| `codex` | `codex exec --json` in the trial directory, workspace-write sandbox | A private `CODEX_HOME` holding only a link to the login, so the user's config, `AGENTS.md` and installed skills are not loaded. The older runner in `../hard` links the login the same way. Whether a token refresh during a long run writes through that link is unverified |
| `claude` | `claude -p --output-format stream-json` with file and shell tools only | User settings, including `~/.claude/CLAUDE.md`, MCP servers, skill commands and auto-memory are switched off. Checked on Claude Code 2.1.322: with these flags the user `CLAUDE.md` is absent from the session, and present without them |
| any other | Add an entry to `arms.json` with a `command` argv template using `{model}`, `{prompt}`, `{prompt_file}` and `{workdir}` | Yours to provide |
| `mock` | No model | Offline |

Model names for each tier are in `arms.json`. Changing them changes the freeze digest, which is intended: a run names exactly what it compared.

Each real adapter was exercised on a trivial non-benchmark prompt (codex-cli 0.166.0 and Claude Code 2.1.322): once to capture its output format, and once through the harness's own command line, which also checked the judge's reply parser. The parsers are tested against the captured shapes. The calibration pilot sent the eight executable tasks to `codex` with no skill. No benchmark task has been sent to `claude`, and no arm has been given the skill.

## Limits

- **The executable tasks are too easy.** The target is an unaided strong model passing about half the executable trials. The pilot measured 16 of 16. Until harder tasks pass a new pilot under a new freeze, any full run is inconclusive on calibration.
- **One executable check depends on the clock.** The scheduling task fails a call that takes one second or longer, measured by wall time. A slow call is not tried again, because a solution that caches its results would answer the second try at once. The reference solution runs all 40 checks in about 0.03 seconds, so the margin is wide, but a machine stalled for a full second during one call would fail a correct solution.
- **Low power.** Two repetitions give 16 to 48 trials per comparison. Repetitions of one task are not independent, and the Wilson interval treats them as if they were. A pass is a reason to run a larger held-out set.
- **The tasks are public.** They are disclosed regression material from the day they are pushed. Hold out fresh tasks for any later claim, and rotate them.
- **One metric is also the skill's tool.** The skill tells the agent to run `claim_check.py`, and unsupported claims per output is counted with the same script. The pairwise judging and human picks do not share that bias. Read the two together.
- **The checker is lexical.** It finds numbers, names and quotations with no source. It cannot tell a supported claim from its opposite.
- **Trap grading reads a status file.** An agent that explains the problem only in its chat reply, and writes no status, is not credited. A trap counts as passed on the status alone, so a status of `unchecked` with an irrelevant list still passes.
- **Time limits.** A trial that reaches the 900-second limit is scored on what is on disk and has no token count. The report shows how many trials timed out per arm. Many timeouts in one arm make the cost criterion inconclusive, and a task whose `skill` trials all timed out gets no budget-control trial.
- **Filesystem isolation is by placement.** Each agent works in its own temporary directory, away from the repository and from other trials' results, but an agent with a shell could search the disk. Run on a machine or container without the repository's answers for a result you intend to publish.
- **Fictional sources.** The writing tasks measure faithfulness to supplied notes. They do not measure open-web research.
