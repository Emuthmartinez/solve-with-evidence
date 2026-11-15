# Optional embedding check

`scripts/embedding_check.py` compares texts by embedding similarity. It is optional, it only warns, and it never blocks a delivery. The script exits 0 on every path, including when the embedding model is unreachable.

## What similarity can and cannot tell you

Similarity measures whether two texts are about the same thing. That is useful for four jobs:

| Mode | Question | Warns when |
|---|---|---|
| `coverage` | Was each sub-problem addressed somewhere in the output? | An item's best match is below `--min` |
| `lookup` | Which source passages are candidates for this claim? | Never. It returns passages to read |
| `novelty` | Is the output too close to an old post or a banned example? | A chunk's nearest example is above `--max` |
| `style` | Is the output closer to the wanted style than to the unwanted one? | The good-minus-bad margin is at or below a calibrated threshold |

It must not judge correctness:

- "Revenue grew 20%" and "revenue fell 20%" embed almost identically. So do a correct function and a buggy one.
- Checking an output against the research it was generated from is circular. The output sits near its own sources, and the top score goes to a paraphrase.
- A text gets one vector, dominated by topic and length. There is no embedding "on a dimension".
- An embedding model's space is not the generating model's internal state. Distance in one says little about the other.

Check correctness by problem type instead: run code, recompute decisions, trace facts to passages, and have an independent reviewer apply a rubric to writing.

## Use

You supply the embedding model as a command. It reads a JSON list of strings on stdin and prints a JSON list of vectors. Nothing is bundled and no service is called unless your command calls one.

```sh
python3 scripts/embedding_check.py --embed "python3 my_embedder.py" coverage --items subproblems.txt --text draft.md --min 0.55
python3 scripts/embedding_check.py --embed "python3 my_embedder.py" lookup --items claims.txt --source notes/
python3 scripts/embedding_check.py --embed "python3 my_embedder.py" novelty --text draft.md --against old-posts/ banned.md --max 0.9
```

`--min` and `--max` have no defaults, because a useful value depends on the embedding model. Without one, the script reports scores and warns about nothing.

The style margin needs calibration first, on at least 30 pairs where a person marked which text is better:

```sh
python3 scripts/embedding_check.py --embed "python3 my_embedder.py" calibrate \
  --pairs labelled.jsonl --good my-writing/ --bad generic-examples/ --out style-calibration.json
python3 scripts/embedding_check.py --embed "python3 my_embedder.py" style \
  --text draft.md --good my-writing/ --bad generic-examples/ --calibration style-calibration.json
```

Each line of `labelled.jsonl` is `{"better": "...", "worse": "..."}`. With fewer than 30 pairs, or when the margin orders fewer than 70% of the pairs correctly, the script says the calibration is too weak to read.

Every warning goes in the report as a warning. None changes the outcome. An embedding gate would reward paraphrase, which is why there is none.
