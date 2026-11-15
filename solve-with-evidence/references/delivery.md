# Delivery: hand over what was checked

Two standard-library Python scripts sit in `scripts/`. One delivers machine-read JSON byte for byte. The other maps prose claims to sources. Run them from this skill's directory on a host with a shell and Python 3.

## Machine-read JSON: `json_handoff.py`

Use this when a program, not a person, will read the JSON, including JSON that carries code. A model that retypes checked JSON into a chat message can change bytes, so the file is the deliverable.

Write the producer's serialized bytes to a staging file once. Then run:

```sh
python3 scripts/json_handoff.py candidate.json --deliver-to "$OUTPUT_DIRECTORY" -- python3 recipient_check.py
```

- Use a persistent directory the user can see, and the recipient's actual trusted checker. The checker reads the JSON on stdin. It exits 0 to accept, 1 to reject, and anything else for a checker error.
- The checker should test what the recipient relies on: nested field names, types, expected results and behavior.
- On acceptance the script prints a receipt with `path`, `sha256` and `bytes`. The file at `path` holds exactly the accepted bytes. Give that path in the final answer. Link the absolute path where the host renders links to local files. Leave the payload in the file. Return just the link when the user asked for an artifact alone.
- On rejection, use the diagnostic to fix the producer, serialize again, and submit the new bytes through the same checker.
- If the checker is unavailable, retry through an authorized working checker. If verification stays unresolved, the outcome is withheld: report the blocker and give no file link and no payload. Never copy an unchecked staging file into the output directory as a fallback.

The checker is a gating check. `--unchecked` does not weaken it. It records what the checker does not cover, for the delivered-with-unchecked-items outcome:

```sh
python3 scripts/json_handoff.py candidate.json --deliver-to "$OUTPUT_DIRECTORY" \
  --unchecked "live availability of the listed venues" -- python3 recipient_check.py
```

The receipt then also carries `"outcome": "delivered_unchecked"` and the `unchecked` list. The checker must still accept the bytes. Repeat each listed item in the final report with why it was not checked and what would check it.

Other options: `--replacement PATH` supplies one alternate payload, tried only if the first is rejected. `--timeout SECONDS` bounds each checker attempt (default 20). Exit status is 0 for acceptance, 1 when every payload was rejected, and 2 when the checker timed out, could not run, or returned something other than 0 or 1.

If the host provides a `deliver_json` tool, pass it the reference to the producer's output instead of pasting JSON into a message. For a required inline-only response, omit `--deliver-to`: the script writes the accepted bytes to stdout, and the host must forward that stdout to the recipient unchanged. If the host cannot do that, say so. Do not present a retyped message as the checked artifact.

## Prose: `claim_check.py`

Use this for any prose deliverable that states facts: a summary, a reply, an email, a report.

```sh
python3 scripts/claim_check.py draft.md --source notes/ --source transcript.txt
```

Every sentence is mapped to a source passage or flagged. `--source` takes files or directories of `.md` and `.txt` files. `--json` prints the full report, including the passage each sentence mapped to.

| Flag | Meaning | What to do |
|---|---|---|
| `unsupported` | A number, name or quotation is in no source, or a number appears only beside different wording | Find the source and add it, correct the claim, or cut it |
| `unmatched` | No passage shares enough of the sentence's wording, or an opening word may be an unsourced name | Decide whether it is a claim or your own framing. A claim needs a source |

Exit status is 0 when every sentence maps, 1 when anything is flagged, and 2 when a file cannot be read.

What the checker cannot do:

- It does not judge entailment. "Revenue grew 20%" maps to a passage that says "revenue fell 20%". After a clean run, read each mapped pair, or have the independent reviewer read them.
- A number you derived, such as a count or a total, is flagged because it is in no source. Show the calculation in the report.
- The default `--min-overlap` of 0.4 is a starting point, not a calibrated threshold.

A flag you cannot resolve is not a reason to stop. If the flagged claim is not under a gating check, deliver with it in the unchecked list, quoted, with what would settle it. If the user made accuracy a condition, the outcome is withheld until it is resolved.

## Everything else

For code, run the delivered entry point. For a decision, recompute it. A check run by someone downstream, later, does not stand in for a check you claimed to run before delivery.
