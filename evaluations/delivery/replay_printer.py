"""Run both earlier failing printer trials through the installed file-delivery CLI."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def run(cli, hard):
    sys.path.insert(0, str(hard / 'handoff'))
    from replay import BAD, capture, correction

    results = []
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        original, replacement = root / 'received', root / 'replacement'
        for repeat in (1, 2):
            trial = f'artifact-h3-shipped-r{repeat}'
            stages, _ = capture(hard / 'trials' / trial)
            for stage, (raw, events) in enumerate(stages, 1):
                original.write_bytes(raw)
                dest = root / f'{trial}-stage{stage}'
                consumer = [sys.executable, '-B', str(hard / 'handoff/transfer_consumer.py'),
                            'artifact-h3', str(stage)]
                command = [sys.executable, '-B', str(cli), str(original), '--deliver-to', str(dest)]
                attempt = subprocess.run([*command, '--', *consumer], capture_output=True, timeout=30)
                provenance = None
                if (trial, stage) in BAD:
                    if (attempt.returncode, attempt.stdout, dest.exists()) != (1, b'', False):
                        raise RuntimeError(f'{trial}/{stage}: defective original reached recipient')
                    expected, provenance = correction(trial, stage, raw, events)
                    replacement.write_bytes(expected)
                    attempt = subprocess.run([*command, '--replacement', str(replacement), '--', *consumer],
                                             capture_output=True, timeout=30)
                else:
                    expected = raw
                if attempt.returncode:
                    raise RuntimeError(f'{trial}/{stage}: valid bytes withheld: {attempt.stderr.decode()}')
                receipt = json.loads(attempt.stdout)
                found = Path(receipt['path'])
                digest = hashlib.sha256(expected).hexdigest()
                if receipt != {'path': str(dest.resolve() / (digest + '.json')), 'sha256': digest, 'bytes': len(expected)}:
                    raise RuntimeError(f'{trial}/{stage}: receipt differs from independently sourced bytes')
                actual = found.read_bytes()
                if actual != expected:
                    raise RuntimeError(f'{trial}/{stage}: final linked file differs')
                subprocess.run(consumer, input=actual, check=True, capture_output=True, timeout=30)
                results.append({'trial':trial, 'stage':stage, 'original_sha256':hashlib.sha256(raw).hexdigest(),
                                'original_accepted':provenance is None, 'replacement_provenance':provenance,
                                'delivered':{'filename':found.name, 'sha256':digest, 'bytes':len(actual)}})
    return results


if __name__ == '__main__':
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, default=repo / 'solve-with-evidence/scripts/json_handoff.py')
    parser.add_argument('--hard', type=Path, default=repo / 'evaluations/hard')
    args = parser.parse_args()
    print(json.dumps(run(args.cli.resolve(), args.hard.resolve()), indent=2))
