# Results

No full run yet. This directory holds no trial and no judgment, and no number about the skill.

## Calibration pilot, 2026-11-15

The `no-skill` arm ran through `codex` (`gpt-6.1-sol`) on the 8 executable tasks, 2 repeats each, under freeze `2c78ed622e9a`. It passed 16 of 16 trials. That is above the pre-registered 25% to 75% calibration band in [`pass_bar.json`](../pass_bar.json), so the run was stopped and no skill arm was started. The pilot's artifacts are not committed.

The freeze has since changed to `00b32c8ad7e2` for three grader fixes. Regraded offline with the fixed graders, the same 16 solutions still pass every check. That is a regrade of the pilot's files, not a second pilot.

## Adding a run

When the benchmark has been run with a real agent, copy the whole run directory here unchanged: `run.json`, the `skills/` snapshots, every `trials/*/trial.json` with its agent log and work directory, `judgments.json`, `human.json` if people judged, and `report.json`. Do not add output from the mock adapter. It tests the harness and measures nothing.
