"""Corrupt a real capture, refresh its manifest, and require the semantic audit to refuse it."""
import copy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from audit import audit

DELIVERY = Path(__file__).resolve().parents[1]
PILOT = DELIVERY / 'iterations/pilot'
SOURCE = PILOT / 'adapter-trials/night-window-candidate-r1'


def inspect_trial(folder):
    return audit(folder, DELIVERY/'cases/inputs/night-window.json', DELIVERY/'cases/consumer.py',
                 PILOT/'scripts/json_handoff.py', PILOT)


class AuditControls(unittest.TestCase):
    def test_positive_and_regenerated_manifest_mutations(self):
        self.assertTrue(inspect_trial(SOURCE)['verified_link_delivery'])
        for fault, diagnostic in [
            ('limits','resource limits'), ('runner','core runner hashes'), ('runtime flags','runtime configuration'),
            ('wrong effort','resource limits'), ('provider user','provider user prompt'),
            ('missing tool echo','earlier items'), ('changed completed arguments','provider tool echo'),
            ('changed started arguments','host call differs'), ('early final','provider user must precede'),
            ('late checker','producer window'), ('case digest','case digest'),
        ]:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                trial = Path(tmp)/SOURCE.name
                shutil.copytree(SOURCE,trial)
                events = list(map(json.loads,(trial/'trace.jsonl').read_bytes().splitlines()))
                summary = json.loads((trial/'summary.json').read_bytes())
                def item(kind,typ):
                    return next(e for e in events if e['kind']==kind and e['data']['item']['type']==typ)
                if fault == 'limits':
                    summary.update(tool_cap_per_turn=100,turn_timeout_s=1)
                elif fault == 'runner':
                    summary['runner_sha256']['run_trial.py'] = '0'*64
                elif fault == 'runtime flags':
                    summary['runtime']['cli_options'] = []
                elif fault == 'wrong effort':
                    summary['effort'] = 'low'
                elif fault == 'provider user':
                    item('item/completed','userMessage')['data']['item']['content'][0]['text'] = 'different prompt'
                elif fault == 'missing tool echo':
                    events.remove(item('item/completed','dynamicToolCall'))
                elif fault.startswith('changed'):
                    edge = 'item/started' if 'started' in fault else 'item/completed'
                    item(edge,'dynamicToolCall')['data']['item']['arguments']['code'] = 'print("different")'
                elif fault == 'early final':
                    msg = item('item/started','agentMessage')
                    events.remove(msg)
                    events.insert(4,msg)
                elif fault == 'late checker':
                    delivery = next(e for e in events if e['kind']=='delivery')
                    events.insert(events.index(item('item/completed','agentMessage')),copy.deepcopy(delivery))
                else:
                    summary['case_messages_sha256'] = 'f'*64
                for i,e in enumerate(events,1):
                    e.update(seq=i, elapsed_s=i/10)
                (trial/'trace.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
                (trial/'summary.json').write_text(json.dumps(summary))
                files=json.loads((trial/'manifest.json').read_bytes())
                for name in ['trace.jsonl','summary.json']:
                    files[name]=sha256((trial/name).read_bytes()).hexdigest()
                (trial/'manifest.json').write_text(json.dumps(files))
                with self.assertRaisesRegex(ValueError, diagnostic):
                    inspect_trial(trial)


if __name__ == '__main__':
    unittest.main()
