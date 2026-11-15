import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HANDOFF = Path(__file__).resolve().parents[1] / 'solve-with-evidence' / 'scripts' / 'json_handoff.py'
ACCEPT = [sys.executable, '-c', 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("ok") is True else 1)']


class UncheckedReceipt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_handoff(self, payload, *options):
        candidate = Path(self.tmp.name) / 'candidate.json'
        candidate.write_text(payload)
        return subprocess.run([sys.executable, str(HANDOFF), str(candidate), *options, '--', *ACCEPT],
                              capture_output=True, text=True)

    def test_receipt_lists_what_was_not_checked(self):
        done = self.run_handoff('{"ok":true}\n', '--deliver-to', str(Path(self.tmp.name) / 'out'),
                                '--unchecked', 'live availability', '--unchecked', 'downstream import')
        receipt = json.loads(done.stdout)
        self.assertEqual(done.returncode, 0)
        self.assertEqual(receipt['outcome'], 'delivered_unchecked')
        self.assertEqual(receipt['unchecked'], ['live availability', 'downstream import'])
        self.assertEqual(Path(receipt['path']).read_text(), '{"ok":true}\n')

    def test_default_receipt_is_unchanged(self):
        done = self.run_handoff('{"ok":true}\n', '--deliver-to', str(Path(self.tmp.name) / 'out'))
        self.assertEqual(sorted(json.loads(done.stdout)), ['bytes', 'path', 'sha256'])

    def test_unchecked_never_delivers_rejected_bytes(self):
        done = self.run_handoff('{"ok":false}\n', '--deliver-to', str(Path(self.tmp.name) / 'out'),
                                '--unchecked', 'everything')
        self.assertEqual((done.returncode, done.stdout), (1, ''))

    def test_unchecked_needs_a_receipt_and_a_reason(self):
        self.assertEqual(self.run_handoff('{"ok":true}\n', '--unchecked', 'x').returncode, 2)
        self.assertEqual(self.run_handoff('{"ok":true}\n', '--deliver-to', str(Path(self.tmp.name) / 'out'),
                                          '--unchecked', ' ').returncode, 2)


if __name__ == '__main__':
    unittest.main()
