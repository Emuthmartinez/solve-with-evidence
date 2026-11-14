"""Exercise the installed CLI and reopen its receipt's file in a separate recipient process."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

# The payload deliberately contains JSON escape sequences and multibyte UTF-8.
SOURCE = 'def field():\n    return "x" + chr(92) + "t" + chr(10)\n'
EDGE = {'job': {'rows': ['A\tB', 'e\u0301', '🪁']}, 'expected': 'x\\t\n'}
VALID = (json.dumps({'source': SOURCE, 'edge': EDGE}, ensure_ascii=False,
                    indent=1).replace('\n', '\r\n') + '\r\n').encode()
VALIDATE = (
    'import json,sys; p=json.load(sys.stdin); '
    f'sys.exit(0 if p.get("source")=={SOURCE!r} and p.get("edge")=={EDGE!r} else 1)'
)
RECEIVE = (
    'import json,pathlib,sys; r=json.load(sys.stdin); '
    'sys.stdout.buffer.write(pathlib.Path(r["path"]).read_bytes())'
)


class Handoff(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.dest = self.root / 'outputs with spaces'
        self.original = self.root / 'received'
        self.original.write_bytes(VALID)

    def handoff(self, *options, checker=VALIDATE):
        command = [sys.executable, '-B', str(CLI), str(self.original),
                   '--deliver-to', str(self.dest), *options, '--', sys.executable, '-c', checker]
        return subprocess.run(command, capture_output=True, timeout=15)

    def receive(self, result, expected=VALID):
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        digest = hashlib.sha256(expected).hexdigest()
        self.assertEqual(receipt, {
            'path': str(self.dest.resolve() / (digest + '.json')),
            'sha256': digest, 'bytes': len(expected),
        })
        actual = subprocess.run([sys.executable, '-c', RECEIVE], input=result.stdout,
                                capture_output=True, check=True, timeout=10)
        self.assertEqual(actual.stdout, expected)

    def test_receives_exact_wire_bytes_after_producer_changes(self):
        result = self.handoff()
        self.original.write_bytes(b'{"source":"a different message"}')
        self.receive(result)

    def test_legacy_stream_still_delivers_identical_bytes(self):
        cmd = [sys.executable, '-B', str(CLI), str(self.original), '--',
               sys.executable, '-c', VALIDATE]
        self.assertEqual(subprocess.run(cmd, capture_output=True, check=True).stdout, VALID)

    def test_rejected_and_failed_checks_emit_no_receipt_or_artifact(self):
        wrong = {'source': SOURCE, 'edge': {'job': EDGE['job']['rows'], 'expected': EDGE['expected']}}
        bad_source = {'source': SOURCE.replace('chr(92)', 'chr(9)'), 'edge': EDGE}
        for bad in [b'{', b'{"a":1,"a":1}', json.dumps(wrong).encode(), json.dumps(bad_source).encode()]:
            self.original.write_bytes(bad)
            result = self.handoff()
            self.assertEqual((result.returncode, result.stdout, self.dest.exists()), (1, b'', False))
        self.original.write_bytes(VALID)
        for script in ['import sys; sys.exit(2)', 'import time; time.sleep(5)']:
            result = self.handoff('--timeout', '1', checker=script)
            self.assertEqual((result.returncode, result.stdout, self.dest.exists()), (2, b'', False))

    def test_checker_mutating_input_path_cannot_swap_accepted_bytes(self):
        # The consumer sees only the buffer read before validation. Change the source
        # file during the check to catch implementations that later copy by filename.
        script = f'from pathlib import Path; Path({str(self.original)!r}).write_bytes(b"null"); ' + VALIDATE
        self.receive(self.handoff(checker=script))
        self.assertEqual(self.original.read_bytes(), b'null')

    def test_replacement_goes_through_same_consumer(self):
        self.original.write_bytes(b'{"edge":{}}')
        other = self.root / 'replacement'
        other.write_bytes(b'{}')
        rejected = self.handoff('--replacement', str(other))
        self.assertEqual((rejected.returncode, rejected.stdout, self.dest.exists()), (1, b'', False))
        other.write_bytes(VALID)
        self.receive(self.handoff('--replacement', str(other)))
        self.assertEqual(len(list(self.dest.iterdir())), 1)

    def test_concurrent_publish_and_retry_are_idempotent(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = [future.result() for future in [pool.submit(self.handoff) for _ in range(6)]]
        for result in results:
            self.receive(result)
        target, = self.dest.iterdir()
        inode = target.stat().st_ino
        self.receive(self.handoff())
        self.assertEqual(target.stat().st_ino, inode)

    def test_name_collision_and_symlink_do_not_overwrite(self):
        self.dest.mkdir()
        target = self.dest / (hashlib.sha256(VALID).hexdigest() + '.json')
        for tag in ['same-length-corruption', 'symlink', 'fifo']:
            if tag == 'same-length-corruption':
                target.write_bytes(b'!' * len(VALID))
            elif tag == 'symlink':
                target.symlink_to(self.original)
            else:
                if not hasattr(os, 'mkfifo'):
                    continue
                os.mkfifo(target)
            failed = self.handoff()
            self.assertEqual((failed.returncode, failed.stdout), (2, b''), tag)
            if tag == 'same-length-corruption':
                self.assertEqual(target.read_bytes(), b'!' * len(VALID))
            self.assertEqual(self.original.read_bytes(), VALID)
            self.assertEqual(list(self.dest.iterdir()), [target])
            target.unlink()

    def test_partial_stage_write_never_creates_final_name(self):
        spec = importlib.util.spec_from_file_location('delivery_subject', CLI)
        subject = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(subject)
        def disk_failure(fd):
            self.assertEqual(list(self.dest.glob('*.json')), [])
            raise OSError('simulated disk failure before publication')
        with patch.object(subject.os, 'fsync', side_effect=disk_failure):
            with self.assertRaisesRegex(OSError, 'disk failure'):
                subject.deliver(VALID, self.dest)
        self.assertEqual(list(self.dest.iterdir()), [])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, help='path to the installed or source json_handoff.py')
    args, remaining = parser.parse_known_args()
    CLI = (args.cli if args.cli else
           Path(__file__).resolve().parents[2] / 'solve-with-evidence/scripts/json_handoff.py').resolve()
    unittest.main(argv=[sys.argv[0], *remaining])
