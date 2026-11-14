"""Exercise the wire contract using an independently launched consumer."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class Handoff(unittest.TestCase):
    def test_cli(self):
        checker = 'import json,sys; sys.exit(0 if json.load(sys.stdin)=={"v":1} else 1)'
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / 'original'
            replacement = Path(directory) / 'replacement'

            def run(raw, retry=None, validator=checker):
                original.write_bytes(raw)
                args = [sys.executable,str(Path(__file__).resolve().parents[3] / 'solve-with-evidence/scripts/json_handoff.py'),str(original)]
                if retry is not None:
                    replacement.write_bytes(retry)
                    args.extend(['--replacement',str(replacement)])
                return subprocess.run([*args,'--',sys.executable,'-c',validator],capture_output=True,timeout=10)

            good = b'  {"v": 1 }\r\n'
            for invalid in (b'{"v":2}', b'{', b'{"v":2,"v":1}', b'{"v":NaN}', b'[1]', b'\xff', b'{"v":1} extra'):
                with self.subTest(invalid=invalid):
                    p = run(invalid)
                    self.assertEqual((p.returncode,p.stdout),(1,b''))
            for first,second,status,payload in [
                (good,b'{',0,good), (b'{',good,0,good), (b'{',b'{"v":9}',1,b''),
            ]:
                p = run(first,second)
                self.assertEqual((p.returncode,p.stdout),(status,payload))
            p = run(good,good,'import sys; sys.exit(2)')
            self.assertEqual((p.returncode,p.stdout),(2,b''))
            self.assertNotIn(b'replacement',p.stderr)


if __name__ == '__main__':
    unittest.main()
