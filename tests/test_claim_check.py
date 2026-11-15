import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'solve-with-evidence' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from claim_check import check

NOTES = """# Harbor notes

Harbor is a scheduling tool for community clinics. It launched on 3 March 2026.

- Dana Okafor, clinic manager at Eastfield, said: "We stopped double-booking the first week."
- Revenue fell 20% in February after the pricing change.
- The outage on 12 March lasted 47 minutes and affected 312 clinics.
- 1,200 clinics signed up; two of them churned. The round raised $2 million.
"""


def flags(text, min_overlap=0.4):
    return check(text, [('notes.md', NOTES)], min_overlap)['flags']


def items(text):
    return [(i['type'], i['text'], i['reason']) for flag in flags(text) for i in flag['items']]


class ClaimCheck(unittest.TestCase):
    def test_sourced_sentences_map_to_their_passage(self):
        report = check('Harbor launched on 3 March 2026. The outage lasted 47 minutes.', [('notes.md', NOTES)])
        self.assertEqual((report['outcome'], report['mapped'], report['flags']), ('all_mapped', 2, []))
        self.assertEqual(report['map'][1]['nearest']['line'], 7)

    def test_number_absent_from_sources_is_flagged(self):
        self.assertEqual(items('The outage lasted 90 minutes.'), [('number', '90 minutes', 'not in any source')])

    def test_number_in_another_context_is_flagged(self):
        self.assertEqual(items('We fixed the outage in 2 days.'),
                         [('number', '2 days', 'in the sources only in another context')])

    def test_number_forms_are_compared_by_value(self):
        for sentence in ('Harbor has 1200 clinics signed up.', 'Two clinics churned.',
                         'The round raised $2,000,000.', 'The round raised $2M.'):
            self.assertEqual(flags(sentence), [], sentence)

    def test_percent_is_not_a_bare_number(self):
        self.assertEqual(items('Revenue fell 47% in February.'), [('number', '47% in', 'not in any source')])

    def test_unknown_name_and_altered_quote_are_flagged(self):
        found = items('Priya Raman said "We stopped double-booking in the first week."')
        self.assertIn(('name', 'Priya Raman', 'not in any source'), found)
        self.assertIn(('quote', 'We stopped double-booking in the first week.', 'not in any source'), found)

    def test_verbatim_quote_and_known_name_pass(self):
        self.assertEqual(flags('Dana Okafor said: "We stopped double-booking the first week."'), [])

    def test_unknown_opening_word_is_a_soft_flag(self):
        flag, = flags('Zentrix praised the scheduling tool for clinics.')
        self.assertEqual((flag['kind'], flag['items'][0]['type']), ('unmatched', 'possible name'))
        self.assertEqual(flags('Clinics use the scheduling tool.'), [])

    def test_sentence_with_no_similar_passage_is_unmatched(self):
        flag, = flags('Our investors expect a strong hiring season across engineering.')
        self.assertEqual((flag['kind'], flag['items']), ('unmatched', []))

    def test_short_remarks_and_code_blocks_are_not_claims(self):
        report = check('Thanks for reading!\n\n```\nrate = 99\n```\n', [('notes.md', NOTES)])
        self.assertEqual((report['sentences'], report['skipped'], report['flags']), (1, 1, []))

    def test_a_flag_names_the_line_inside_a_wrapped_paragraph(self):
        flag, = flags('Harbor launched on 3 March 2026.\nThe outage lasted\n90 minutes.')
        self.assertEqual((flag['line'], flag['sentence']), (2, 'The outage lasted 90 minutes.'))

    def test_does_not_judge_entailment(self):
        # The stated limit: the opposite claim shares the number and the wording, so it maps.
        self.assertEqual(flags('Revenue grew 20% in February.'), [])

    def test_cli_exit_codes_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes, good, bad = (Path(tmp) / name for name in ('notes.md', 'good.md', 'bad.md'))
            notes.write_text(NOTES)
            good.write_text('Harbor launched on 3 March 2026.\n')
            bad.write_text('Harbor launched on 9 March 2026.\n')
            run = lambda *a: subprocess.run([sys.executable, str(SCRIPTS / 'claim_check.py'), *map(str, a)],
                                            capture_output=True, text=True)
            self.assertEqual(run(good, '--source', tmp).returncode, 0)
            flagged = run(bad, '--source', notes, '--json')
            self.assertEqual(flagged.returncode, 1)
            self.assertEqual(json.loads(flagged.stdout)['flags'][0]['items'][0]['text'], '9 March')
            self.assertEqual(run(good, '--source', Path(tmp) / 'missing.md').returncode, 2)


if __name__ == '__main__':
    unittest.main()
