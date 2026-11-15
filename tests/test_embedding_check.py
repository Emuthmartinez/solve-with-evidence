import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'solve-with-evidence' / 'scripts' / 'embedding_check.py'
EMBED = f'{sys.executable} {ROOT / "tests" / "fake_embed.py"}'


class EmbeddingCheck(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def file(self, name, text):
        path = self.dir / name
        path.write_text(text)
        return str(path)

    def run_check(self, *args, embed=EMBED):
        done = subprocess.run([sys.executable, str(SCRIPT), '--embed', embed, *args], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        out = json.loads(done.stdout)
        self.assertIs(out['blocking'], False)
        self.assertIs(out['judges_correctness'], False)
        return out

    def test_coverage_warns_about_an_unaddressed_item_without_failing(self):
        text = self.file('text.md', 'The outage lasted 47 minutes and affected clinics.\n\nPricing changes in June.\n')
        items = self.file('items.txt', 'outage duration and affected clinics\nrefund policy for annual plans\n')
        out = self.run_check('coverage', '--items', items, '--text', text, '--min', '0.5')
        self.assertEqual(len(out['warnings']), 1)
        self.assertIn('refund policy', out['warnings'][0])

    def test_thresholds_have_no_default(self):
        text = self.file('text.md', 'Pricing changes in June.\n')
        items = self.file('items.txt', 'refund policy for annual plans\n')
        self.assertEqual(self.run_check('coverage', '--items', items, '--text', text)['warnings'], [])

    def test_lookup_returns_candidates_and_never_warns(self):
        source = self.file('notes.md', 'Revenue fell 20% in February.\n\nThe outage lasted 47 minutes.\n')
        items = self.file('claims.txt', 'Revenue grew 20% in February.\n')
        out = self.run_check('lookup', '--items', items, '--source', source, '--top', '1')
        # The opposite claim is the nearest passage: similarity cannot tell them apart.
        self.assertEqual(out['results'][0]['candidates'][0]['text'], 'Revenue fell 20% in February.')
        self.assertEqual(out['warnings'], [])

    def test_novelty_warns_when_close_to_a_banned_example(self):
        text = self.file('text.md', 'This changes everything for busy teams.\n')
        banned = self.file('banned.md', 'This changes everything for busy teams everywhere.\n')
        out = self.run_check('novelty', '--text', text, '--against', banned, '--max', '0.8')
        self.assertEqual(len(out['warnings']), 1)

    def test_style_margin_needs_enough_labelled_pairs(self):
        good = self.file('good.md', 'We shipped the fix on Tuesday. Two clinics reported it.\n')
        bad = self.file('bad.md', 'We are thrilled to announce a game-changing synergy.\n')
        pairs = self.file('pairs.jsonl', json.dumps({'better': 'We shipped the fix.', 'worse': 'We are thrilled.'}) + '\n')
        cal = str(self.dir / 'cal.json')
        out = self.run_check('calibrate', '--pairs', pairs, '--good', good, '--bad', bad, '--out', cal)
        self.assertEqual(out['calibration']['pairs'], 1)
        self.assertIn('at least 30', out['warnings'][0])
        text = self.file('text.md', 'We are thrilled to announce synergy.\n')
        out = self.run_check('style', '--text', text, '--good', good, '--bad', bad, '--calibration', cal)
        self.assertIn('too weak', out['warnings'][0])
        self.assertLess(out['margin'], 0)

    def test_broken_embedder_warns_and_still_exits_zero(self):
        text = self.file('text.md', 'Anything.\n')
        out = self.run_check('novelty', '--text', text, '--against', text, embed=f'{sys.executable} -c "raise SystemExit(3)"')
        self.assertIn('unavailable', out['warnings'][0])


if __name__ == '__main__':
    unittest.main()
