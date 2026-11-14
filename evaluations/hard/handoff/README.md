# Verify the bytes you hand off

Use [json_handoff.py](../../../solve-with-evidence/scripts/json_handoff.py) when the recipient expects a UTF-8 JSON object and you have a trusted checker for **that recipient's contract**. It sends the checker exactly the bytes it received, waits for a verdict, and emits those same bytes only on acceptance. It does not invent fields, strip fences, fix escapes, or generate a witness.

From the installed skill directory, run

```sh
python3 scripts/json_handoff.py received.json -- python3 your_consumer.py > accepted.json
```

The consumer reads stdin. It exits **0** only when the nested schema and required behavior pass, **1** for a bad submission, and **2** for an unavailable check or internal error. Supply the trusted validation command yourself. A JSON parser or a checker that always succeeds cannot establish function or witness correctness. For a claimed counterexample, compare the submitted expectation to an independent reference and require the specified faulty implementation to differ on **that same input**. When the contract delivers executable code, run the recovered source on the submitted edge and appropriate functional cases in an isolated runner.

On rejection, nothing is emitted; forward only after exit 0. If the producer can supply a faithful replacement, allow one recheck:

```sh
python3 scripts/json_handoff.py received.json --replacement producer-correction.json -- python3 your_consumer.py > accepted.json
```

The original is tried first. If neither is accepted, the gate exits 1; if the consumer is unavailable, times out, or exits unexpectedly, it stops with 2. Use a new destination, keep the original, and use only the accepted output for delivery. A missing validated source or uncheckable witness belongs back with its producer. The generic gate has no third-party dependencies; it does not execute submitted source, obtain credentials, or arrange a sandbox for the chosen consumer.

## Captured failure replay

[replay.json](replay.json) is a **post-hoc harness result** using the original five experimental arms. Their original, unchanged outcome remains **142/146**. We replayed all ten two-stage trials in the two affected transfers against their frozen graders and checked the actual final message bytes from each stage. Sixteen stage answers passed unchanged. The other four were rejected. A separate demonstration supplied one provenance-checked replacement for each; all four then passed. No solver was called by this replay.

| Captured trial and stage | Received | How the demonstration obtained the replacement | Frozen trial points, original → reconstructed |
|---|---|---|---|
| artifact-h3-published-r1 / 1 | A rows array at `edge.job` | Kept the producer-tested rows and expected string; placed the rows under the required named argument. | 16/17 → 17/17 |
| artifact-h3-published-r2 / 1 | Same wrong job shape | Applied the same single wrapper to this trial’s own producer-tested rows. | 16/17 → 17/17 |
| ledger-h2-final-r2 / 1 | Invalid JSON escape in the function source | Restored one missing `n` in a newline escape. Checked the recovered source character for character against the successfully executed original function; every other byte stayed unchanged. | 10/18 → 18/18 |
| ledger-h2-final-r1 / 2 | Correct and faulty allocators both returned `{"a":0,"b":2}` | Reused the same stage’s independently replayable five-identifier input and observed result. The correct result gives Gale 4 slots; the faulty first-round allocator gives Gale 2. | 17/18 → 18/18 |

The shipped package is kept separate. Of four shipped trials on the same two transfer cases, two passed the original grader. The consumer accepted five of their eight original stage answers; three required replacements. Shipped printer r1 stage 1 again needed its producer-tested rows wrapped (trial **16/17 → 17/17**). Shipped printer r2 corrupted the source in both final messages, even though its calculator had emitted valid, tested payloads; stage 1 also used the wrong wrapper. Recovering each stage’s exact source from its own earlier successful serialized payload, and wrapping only stage 1, passed the consumer and frozen grader (**5/17 → 17/17**). Both shipped ledger trials passed unchanged.

The [r1 summary](../trials/artifact-h3-shipped-r1/summary.json), [r1 trace](../trials/artifact-h3-shipped-r1/trace.jsonl), [r2 summary](../trials/artifact-h3-shipped-r2/summary.json), and [r2 trace](../trials/artifact-h3-shipped-r2/trace.jsonl) preserve the full original final messages and distinct tool output. The replay report includes hashes of both original and replacement bytes and links each replacement to its original stage’s successful tool call by ID and sequence. The original five-arm cohort is an explicit set of 146 trial IDs. Neither the separate shipped figures nor the later contract-h4 family enter that denominator.

[transfer_consumer.py](transfer_consumer.py) is an example for just these two known contracts. It checks the nested structure, uses the existing independent reference and mutant, executes the recovered function on the exact edge, and calls the frozen outcome grader on its other inputs. [replay.py](replay.py) also compares each original grade in full with the historical record, verifies trace/summary hashes and the final message against its trace, and links every replacement to an earlier successful producer call. These retrospective conversions are deliberately outside the runtime gate. They do not measure autonomous retry success, generalization, or usefulness on other problems.

To reproduce from this directory (the transfer grader uses the existing macOS sealed calculator):

```sh
python3 test_handoff.py
python3 replay.py --out /tmp/handoff-replay.json
cmp /tmp/handoff-replay.json replay.json
```

The replay expects sibling `trials/`, `reconciliation/`, and `runner/` directories from this evaluation archive. The portable filter and its CLI controls run independently of those directories.
