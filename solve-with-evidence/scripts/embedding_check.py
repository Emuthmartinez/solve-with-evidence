"""Optional embedding similarity checks. They warn. They never block and never judge correctness.

Similarity measures "about the same thing". "Revenue grew 20%" and "revenue fell 20%" sit
together, and so do a correct function and a buggy one. Use this only for coverage, source
lookup, novelty against old or banned examples, and a calibrated style margin.

The embedding model is yours: --embed is a command that reads a JSON list of strings on stdin
and prints a JSON list of vectors. This script always exits 0 once its arguments parse.
"""
import argparse
import json
import math
import shlex
import subprocess
import sys
from pathlib import Path


def embed(command, texts):
    done = subprocess.run(shlex.split(command), input=json.dumps(texts), capture_output=True,
                          text=True, timeout=120, check=True)
    vectors = json.loads(done.stdout)
    if len(vectors) != len(texts):
        raise ValueError('embed command returned a different number of vectors')
    return vectors


def cosine(a, b):
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / norm if norm else 0.0


def chunks(paths):
    """Paragraphs of every file, or of every .md and .txt file under a directory."""
    for path in paths:
        files = sorted(p for p in path.rglob('*') if p.suffix in ('.md', '.txt')) if path.is_dir() else [path]
        for file in files:
            for block in file.read_text(encoding='utf-8').split('\n\n'):
                if block.strip():
                    yield ' '.join(block.split())


def nearest(command, queries, corpus, top=1):
    vectors = embed(command, queries + corpus)
    split = len(queries)
    for index, query in enumerate(queries):
        scored = sorted(((cosine(vectors[index], vectors[split + j]), text) for j, text in enumerate(corpus)),
                        reverse=True)[:top]
        yield query, [{'score': round(score, 4), 'text': text} for score, text in scored]


def margins(command, texts, good, bad):
    """Mean similarity to the good set minus mean similarity to the bad set, per text."""
    vectors = embed(command, texts + good + bad)
    good_v = vectors[len(texts):len(texts) + len(good)]
    bad_v = vectors[len(texts) + len(good):]
    return [sum(cosine(v, g) for g in good_v) / len(good_v) - sum(cosine(v, b) for b in bad_v) / len(bad_v)
            for v in vectors[:len(texts)]]


def run(args):
    out = {'check': args.mode, 'blocking': False, 'judges_correctness': False, 'warnings': []}
    warn = out['warnings'].append
    if args.mode == 'coverage':
        items = [line.strip() for line in args.items.read_text(encoding='utf-8').splitlines() if line.strip()]
        out['results'] = [{'item': q, 'best': hits[0]} for q, hits in nearest(args.embed, items, list(chunks([args.text])))]
        for row in out['results']:
            if args.min is not None and row['best']['score'] < args.min:
                warn(f"possibly not addressed: {row['item']} (best {row['best']['score']} < {args.min})")
    elif args.mode == 'lookup':
        items = [line.strip() for line in args.items.read_text(encoding='utf-8').splitlines() if line.strip()]
        out['results'] = [{'item': q, 'candidates': hits}
                          for q, hits in nearest(args.embed, items, list(chunks(args.source)), args.top)]
        out['note'] = 'Candidates to read. A near passage is not a supporting passage.'
    elif args.mode == 'novelty':
        out['results'] = [{'chunk': q, 'nearest': hits[0]}
                          for q, hits in nearest(args.embed, list(chunks([args.text])), list(chunks(args.against)))]
        for row in out['results']:
            if args.max is not None and row['nearest']['score'] > args.max:
                warn(f"close to an old or banned example ({row['nearest']['score']} > {args.max}): {row['chunk'][:80]}")
    elif args.mode == 'calibrate':
        pairs = [json.loads(line) for line in args.pairs.read_text(encoding='utf-8').splitlines() if line.strip()]
        texts = [p[side] for p in pairs for side in ('better', 'worse')]
        scores = margins(args.embed, texts, list(chunks(args.good)), list(chunks(args.bad)))
        better, worse = scores[0::2], scores[1::2]
        # The threshold that best splits the labelled better texts from the worse ones.
        threshold = max(sorted(scores), key=lambda t: sum(b > t for b in better) + sum(w <= t for w in worse))
        calibration = {'pairs': len(pairs), 'threshold': threshold,
                       'pair_accuracy': round(sum(b > w for b, w in zip(better, worse)) / len(pairs), 3)}
        args.out.write_text(json.dumps(calibration, indent=2) + '\n')
        out['calibration'] = calibration
        if len(pairs) < 30:
            warn(f'{len(pairs)} labelled pairs; use at least 30 before reading the style margin')
    elif args.mode == 'style':
        calibration = json.loads(args.calibration.read_text())
        margin = margins(args.embed, [' '.join(args.text.read_text(encoding='utf-8').split())],
                         list(chunks(args.good)), list(chunks(args.bad)))[0]
        out.update(margin=round(margin, 4), calibration=calibration)
        if calibration['pairs'] < 30 or calibration['pair_accuracy'] < 0.7:
            warn('calibration is too weak to read this margin: '
                 f"{calibration['pairs']} pairs, pair accuracy {calibration['pair_accuracy']}")
        elif margin <= calibration['threshold']:
            warn(f"style margin {round(margin, 4)} is at or below the calibrated threshold "
                 f"{round(calibration['threshold'], 4)}")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--embed', required=True, metavar='COMMAND',
                        help='command: JSON list of strings on stdin, JSON list of vectors on stdout')
    modes = parser.add_subparsers(dest='mode', required=True)
    coverage = modes.add_parser('coverage', help='was each sub-problem addressed somewhere in the text?')
    coverage.add_argument('--items', type=Path, required=True, help='one sub-problem per line')
    coverage.add_argument('--text', type=Path, required=True)
    coverage.add_argument('--min', type=float, help='warn below this similarity; no default, it depends on your model')
    lookup = modes.add_parser('lookup', help='find candidate source passages for each claim')
    lookup.add_argument('--items', type=Path, required=True, help='one claim per line')
    lookup.add_argument('--source', type=Path, nargs='+', required=True)
    lookup.add_argument('--top', type=int, default=3)
    novelty = modes.add_parser('novelty', help='is the text too close to old or banned examples?')
    novelty.add_argument('--text', type=Path, required=True)
    novelty.add_argument('--against', type=Path, nargs='+', required=True)
    novelty.add_argument('--max', type=float, help='warn above this similarity; no default, it depends on your model')
    for name in ('calibrate', 'style'):
        mode = modes.add_parser(name, help='good-minus-bad style margin' if name == 'style'
                                else 'fit the style threshold on human-labelled better/worse pairs')
        mode.add_argument('--good', type=Path, nargs='+', required=True, help='examples of the wanted style')
        mode.add_argument('--bad', type=Path, nargs='+', required=True, help='examples of the unwanted style')
        if name == 'style':
            mode.add_argument('--text', type=Path, required=True)
            mode.add_argument('--calibration', type=Path, required=True)
        else:
            mode.add_argument('--pairs', type=Path, required=True, help='JSON lines: {"better": "...", "worse": "..."}')
            mode.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        out = run(args)
    except Exception as exc:  # an unavailable or broken embedding model must not stop a delivery
        out = {'check': args.mode, 'blocking': False, 'judges_correctness': False,
               'warnings': [f'embedding check unavailable: {type(exc).__name__}: {exc}']}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    for warning in out['warnings']:
        print('WARNING (not blocking):', warning, file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
