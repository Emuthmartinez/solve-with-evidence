# Did the recipient get the bytes the checker accepted?

The updated skill delivered the exact checked file in all 12 normal trials across two hosts. The previous release did so in nine. Each host ran three cases twice per version under Codex CLI 0.166.0 with gpt-6.1-sol and medium effort. The historical baseline is the publicly installed six-file package at commit c764b94. The candidate those trials ran is frozen in [measured-package](measured-package), with digests in [distribution-manifest.json](distribution-manifest.json). The installable skill at `solve-with-evidence/` keeps that delivery rule and states it for any host with Python 3. Codex desktop links and this harness's `deliver_json` tool are named there as host-specific. The model trials were not repeated after that wording change.

| Receiving path | Previous release, raw correct | Updated skill, raw correct | Previous release, checked bytes received | Updated skill, checked bytes received |
|---|---:|---:|---:|---:|
| Native Codex shell and Markdown file link | 6/6 | 6/6 | 6/6 | 6/6 |
| App-server with a delivery tool | 5/6 | 6/6 | 3/6 | 6/6 |

The native receiver parsed the actual final assistant message with CommonMark, opened the linked artifact while the session files still existed, and ran the independent consumer on its bytes. All six candidate links named the file by its SHA-256. The baseline used ordinary filenames and still preserved the checked bytes in all six native trials. On the app-server, one baseline answer reached the receiver as invalid inline JSON. Two other correct baseline answers lacked a matching pre-delivery checker receipt. [Native captures](native-trials) · [App-server captures](adapter-trials) · [Fresh byte-map transfer](adapter-transfer) · [Regraded results](results)

A separate four-trial outage comparison disabled the trusted checker. The candidate withheld both payloads and reported the blocker. The baseline delivered both payloads without a successful check. Both happened to pass later, once the receiver was available. These four trials have their own denominator. [Outage captures](outages)

## What was fixed

One earlier printer response delivered a list where a named job object was required. Another changed working source code while composing the final message. The bundled program now passes the producer’s bytes to the trusted checker, writes those same bytes atomically into a caller-owned output directory, reopens the file, and returns its path, digest, and size. The skill links that path. If the checker fails, the caller receives no accepted path. An earlier unverified file must not be substituted. The original printer replays rejected all three defective stage answers. Three separately sourced repairs reached the recipient byte for byte and the one correct stage passed unchanged. [Printer replay](printer-replay.json) · [File-delivery controls](test_artifact.py)

The transfers required two counterexamples that isolate different scheduling faults, a Python encoder handling CRLF and escaped UTF-8 lengths, and a nested packet map with half-open byte ranges. The case designers froze the prompts and consumers before inference. The packet-map case was reserved after the wording change about checker failures. Each repeat started a fresh model conversation. [Case freeze](cases/freeze.json) · [Packet-map freeze](transfer/freeze.json) · [Protocol and changes](protocol.md)

## Evidence and limits

Native traces retain each model-visible CLI event except private reasoning, shell commands and their output, final message, actual recipient bytes, separate host checker inputs and verdicts, timestamps, usage, package identity and invocation settings. The app-server traces also retain the supplied model instructions and complete tool call/return pairs. Native request files identify the supplied skill by hash. Absolute paths beginning with `/private/tmp/swe-native-` are synthetic session paths. In an archived response, the same file lives under that trial's `outputs/` directory. The replay reads those files and compares them with the independently saved receiving-side bytes and checker records. [Example final response](native-trials/packet-map-candidate-r1/response.md) · [Actual received bytes](native-trials/packet-map-candidate-r1/received.json)

The archive includes 51 live model conversations. The main comparison used 24. There were four outage probes, eight pilot app-server trials, twelve earlier native trials with a narrower link parser, and three native preflights. The first native receiver missed a valid Markdown link with a space before its destination. It recorded a real miss under its own parsing rule. The final CommonMark grid reran all twelve cells and opened the links during those runs. One early checker ran inside an already sandboxed child process and could not start its own sealed evaluator. That trace exposed an unchecked file link and led to the fail-closed instructions. The current native fixture runs its trusted consumer in the parent host. [Pilot](iterations/pilot) · [Earlier native receiver](iterations/strict-native) · [Preflight failures and controls](iterations/preflight)

Elapsed time summed over the six normal native trials was 176 seconds for the baseline and 173 seconds for the candidate. Provider-reported input plus output tokens were 360,630 and 404,708 respectively. The app-server totals were 149 and 143 seconds, and 171,013 and 233,146 tokens. Two repetitions per case and three synthetic cases give limited evidence about general reliability. The native receiver exercised the CLI’s actual final message and a Markdown file opener. No telemetry measured a human click in the Codex desktop UI. The file mode relies on a persistent recipient-visible directory controlled by the caller. Strict inline delivery needs a host that forwards the accepted stdout unchanged.

## Reproduce

Run from the repository root. The installed skill and checker require Python’s standard library. Native Markdown reproduction additionally uses markdown-it-py 4.0.0. All live model runs need compatible local Codex authentication. The executable wire fixture uses the sealed macOS evaluator. Offline replay invokes no model.

```sh
python3 -B evaluations/delivery/runner/audit.py --repo . --cases evaluations/delivery/cases --trials evaluations/delivery/adapter-trials --out /tmp/swe-adapter.json
python3 -B evaluations/delivery/runner/audit.py --repo . --cases evaluations/delivery/transfer --trials evaluations/delivery/adapter-transfer --out /tmp/swe-transfer.json
uv run --no-project --with markdown-it-py==4.0.0 python -B evaluations/delivery/audit_native.py evaluations/delivery/native-trials
uv run --no-project --with markdown-it-py==4.0.0 python -B evaluations/delivery/audit_native.py evaluations/delivery/outages --cases packet-map
uv run --no-project --with markdown-it-py==4.0.0 python -B evaluations/delivery/test_audit_native.py evaluations/delivery/native-trials
python3 -B evaluations/delivery/runner/test_audit.py
python3 -B evaluations/delivery/test_artifact.py
python3 -B evaluations/delivery/replay_printer.py
python3 -B evaluations/verify_evidence.py --manifest evaluations/delivery/distribution-manifest.json --package evaluations/delivery/measured-package
```

For new trials, provide fresh output directories. Both arms have the same available operations within a host. Saved-trial audits compare the candidate arm with `evaluations/delivery/measured-package`. A new capture taken from the live skill must be audited with `--candidate solve-with-evidence`.

```sh
uv run --no-project --with markdown-it-py==4.0.0 python -B evaluations/delivery/native_matrix.py --out /tmp/swe-native-new
uv run --no-project --with markdown-it-py==4.0.0 python -B evaluations/delivery/native_matrix.py --out /tmp/swe-outages-new --outage
python3 -B evaluations/delivery/runner/matrix.py --repo . --cases evaluations/delivery/cases --out /tmp/swe-tools-new
python3 -B evaluations/delivery/runner/matrix.py --repo . --cases evaluations/delivery/transfer --out /tmp/swe-transfer-new
```
