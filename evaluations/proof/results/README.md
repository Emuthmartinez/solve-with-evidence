# Results

No full run yet. This directory holds no trial and no judgment, and no number about the skill.

## Calibration pilot, 2026-11-15

The `no-skill` arm ran through `codex` (`gpt-6.1-sol`) on the 8 executable tasks, 2 repeats each, under freeze `2c78ed622e9a`. It passed 16 of 16 trials. That is above the pre-registered 25% to 75% calibration band in [`pass_bar.json`](../pass_bar.json), so the run was stopped and no skill arm was started. The pilot's artifacts are not committed.

The freeze has since changed to `ea0970b83b51` for three grader fixes. Regraded offline with the fixed graders, the same 16 solutions still pass every check. That is a regrade of the pilot's files, not a second pilot.

## Executable tasks replaced, 2026-11-15

After the pilot, the eight executable tasks were replaced with harder ones, before any skill arm ran. The freeze is now `74b1dd44410c`. The writing tasks, the traps, the pass bar and every threshold are unchanged. The pilot above measured the first set and says nothing about the new one. The new tasks have not been sent to any model, so the calibration row is open until a new pilot runs.

## Adding a run

When the benchmark has been run with a real agent, copy the whole run directory here unchanged: `run.json`, the `skills/` snapshots, every `trials/*/trial.json` with its agent log and work directory, `judgments.json`, `human.json` if people judged, and `report.json`. Do not add output from the mock adapter. It tests the harness and measures nothing.
