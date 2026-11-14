# Regrade recorded trials

Give the audit the directory containing `benchdesign/`, `linkage/`, `reconciliation/`, `closure/`, `runner/` and the selected trials. Each grader module is imported only for the requested family. Ledger grading executes the submitted function through that suite's restricted subprocess, which requires its documented host. Use `--skill ARM=DIR` for each frozen skill snapshot available. Paths are relative to `--root` unless absolute.

```sh
python3 audit.py --root . --trials trials --arms baseline candidate \
  --cases probe-d1 roster-d1 linkage-d1 ledger-d1 closure-d1 --reps 1 2 \
  --skill baseline=snapshots/baseline --skill candidate=snapshots/candidate \
  --out regrade.json
```

The original grid compares `baseline`, `candidate`, `release`, `final` and `published`. The earlier transfer grid compares `baseline`, `final` and `published` on `closure-h2` and `ledger-h2`. The prospective `artifact-h3` grid compares `baseline` and `published`. These names identify successive frozen skill snapshots. A matrix explicitly defines the expected arms, cases and repetitions. Each non-baseline arm receives its own matched comparison against the baseline, including point differences, pass gains, pass losses, and any unmatched trials. A missing third arm still allows a recorded comparison between the other two. The cohort-wide pair is marked incomplete and the audit returns an error. The default reference arm is named `baseline` if present, otherwise the first declared arm. A cohort may override it with the `baseline` field. A missing trial, altered grade, unmatched hash, reused thread, changed tool budget or broken event sequence returns a nonzero exit. A solver can fail a case while its trace passes the audit. The JSON report includes individual grades, matched pairs, elapsed time, observed calculator and reference calls, full and partial passes, criterion counts, critical errors and provider-reported tokens by family and arm. Token sums use the last recorded cumulative total per trial. Unreported usage is counted separately. Pairs containing an infrastructure failure are marked unmatched. Integrity errors exclude that row from all metrics and make the audit fail.

For separately located or differently sized cohorts, pass a JSON array with unique names using `--cohorts cohorts.json`. Each cohort has `name`, `trials`, `arms`, `cases` and `reps`. An optional `exclusions` array contains independently archived attempts with `path` and a stated `reason`, such as a preflight with a defective calculator. Their trace and summary digests are checked, and their status is reported outside the comparison matrix. Cross-arm settings are matched within each cohort. The same solver thread cannot be counted twice across a single audit invocation.

```json
[
  {"name":"development","trials":"trials","arms":["baseline","candidate"],
   "cases":["probe-d1","probe-d2"],"reps":[1,2]},
  {"name":"reserved","trials":"reserved-trials","arms":["baseline","candidate"],
   "cases":["probe-h1"],"reps":[1,2]}
]
```

A completed trial is regraded from its recorded public answers. A timeout reached after a solver turn started, without a recorded provider error, counts as a budget failure. A completed turn without a final answer also earns zero for that turn. In either case, previously completed turns retain their earned points. A provider or setup failure has no score. The harness does not expose sampling seeds, private provider state or cryptographic proof of authorship. The manifest checks detect archive inconsistency. Optional snapshot checks bind all reported skill files to the supplied directory. Without a snapshot the audit verifies within-arm file hashes, submitted entry text, listed reference names and actually served reference contents.

Run `python3 test_audit.py --root .` for corruption and failure-classification controls. This copies the completed `probe-d1-baseline-r1` development fixture into temporary storage, exercises the failure paths, then removes the copy.
