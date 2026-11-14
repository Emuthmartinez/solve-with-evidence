# Delivery-tool comparison

Each repeat starts a new Codex app-server with the existing isolated benchmark transport. Both arms receive the same model, limits, case text, checker, Python tool and delivery tool. Each solver gets its assigned skill instructions. The provider does not expose a model sampling seed. The Python calculator has seed zero.

A successful Python tool call retains its stdout bytes in the host. The `deliver_json` tool uses a call ID or the latest successful call. The host passes that exact buffer to the production delivery CLI. The trusted case consumer validates the submitted JSON. The CLI writes a content-addressed file and returns a receipt. The tool gives the model a Markdown link relative to the final response document. It stores the path in that relative form in public evidence.

The final model message is saved as `response.md` without adding a newline. A separate recipient process follows the single link from the directory containing that message and reads the file, or supplies the raw inline answer to the consumer. `received.bin` contains the bytes the recipient saw. A missing file leads to a recorded failure with no received bytes. An unchanged, verified handoff requires an independent consumer pass and a matching successful producer-buffer-to-delivery receipt. A correct inline answer can earn the raw-correct endpoint. Retyping, fences, broken links and extra output can lose credit. `verified_link_delivery` additionally requires that the host served the content-addressed file named by the actual final link.

From the repository root, rerun the captures on a macOS Codex host with a supported file-backed CLI session:

```sh
python3 -B evaluations/delivery/runner/matrix.py --repo . \
  --cases evaluations/delivery/cases --out /tmp/fresh-swe-delivery
```

Choose a new empty output directory. The first run is a smoke trial, followed by seven fresh sessions with at most two in flight. The base capture protocol, privacy limits and sandbox are in [the previous benchmark](../../hard/README.md). For this host the recipient’s document root is the trial directory. The native-shell trials exercise the desktop-style absolute artifact links separately.

To independently reopen the actual file, regrade it, and verify receipt lineage without requesting more model sessions:

```sh
python3 -B evaluations/delivery/runner/audit.py --repo . \
  --cases evaluations/delivery/cases --trials evaluations/delivery/adapter-trials \
  --out /tmp/regraded-delivery.json
python3 -B evaluations/delivery/runner/test_recipient.py \
  --gate solve-with-evidence/scripts/json_handoff.py
```

Each trial records the complete model-visible instructions, prompt, tool descriptions, public completed model items, exact tool arguments, calculator streams, delivery receipts and attempts, final message, recipient readback, result and usage. The traces exclude private reasoning, duplicated network deltas, provider-internal prompts and credentials. Digests bind the exported files. They cannot authenticate a provider independently of the instrumented host.
