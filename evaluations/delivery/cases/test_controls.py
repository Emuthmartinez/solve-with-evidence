"""Frozen positive and negative controls using hand-derived answers and a second implementation."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from consumer import CASES, QUERIES, route

HERE = Path(__file__).resolve().parent
GOOD_SOURCE = r'''def frame(*, fields, sequence):
    answer = str(sequence) + '|'
    for text in fields:
        safe = text.replace('\\', '\\\\').replace(';', '\\;').replace('\r', '\\r').replace('\n', '\\n')
        answer += str(len(safe.encode('utf-8'))) + ':' + safe + ';'
    return answer + '\r\n'
'''


def witness(d, m, expected):
    return {'job': {'receiver': {'day': d, 'minute': m}}, 'expected':expected}


NIGHT_GOOD = {
    'routes':'reed plum reed reed cobalt plum plum plum elm cobalt idle shell gold gold idle cobalt idle reed'.split(),
    'witnesses':{'day_owner':witness(0,90,'idle'),'first_match':witness(0,0,'gold')},
}
OCTET_GOOD = {
    'source':GOOD_SOURCE,
    'sample':'41|3:e\u0301;9:水\\;🚲;6:A\\r\\nB;3:\\\\r;1:";0:;\r\n',
    'edge':{'job':{'fields':['é'],'sequence':7},'expected':'7|2:é;\r\n'},
}


def run():
    results = []
    def controls(case, title, data, expected):
        raw = data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
        p = subprocess.run([sys.executable,'-B',str(HERE/'consumer.py'),case],input=raw,capture_output=True)
        if p.returncode != expected:
            raise RuntimeError((case, title, expected, p.returncode, p.stderr.decode()))
        results.append({'case':case,'control':title,'exit':p.returncode})

    n, o = CASES
    controls(n, 'hand-traced 18 jobs and isolated witnesses', NIGHT_GOOD, 0)
    x = deepcopy(NIGHT_GOOD); x['witnesses']['day_owner']['job'] = {'day':0, 'minute':90}
    controls(n, 'removed receiver envelope', x, 1)
    x = deepcopy(NIGHT_GOOD); x['witnesses']['first_match'] = witness(1,29,'reed')
    controls(n, 'witness detects both faults without isolating first_match', x, 1)
    x = deepcopy(NIGHT_GOOD); x['witnesses']['day_owner']['job']['receiver']['day'] = False
    controls(n, 'boolean admitted as day zero', x, 1)
    x = deepcopy(NIGHT_GOOD); x['routes'] = [route(d,m,'first_match') for d,m in QUERIES]
    controls(n, 'ordered-first receiver', x, 1)
    x = deepcopy(NIGHT_GOOD); x['routes'] = [route(d,m,'day_owner') for d,m in QUERIES]
    controls(n, 'current-day-only receiver', x, 1)
    controls(o, 'independent sequential-replace encoder', OCTET_GOOD, 0)
    x = deepcopy(OCTET_GOOD); x['source'] = GOOD_SOURCE.replace("len(safe.encode('utf-8'))", 'len(safe)')
    controls(o, 'source counts characters on hidden inputs', x, 1)
    x = deepcopy(OCTET_GOOD); x['sample'] = x['sample'].replace('\r\n','\n')
    controls(o, 'newline normalization changes sample', x, 1)
    x = deepcopy(OCTET_GOOD); x['source'] = GOOD_SOURCE.replace(r"'\r\n'", "'\r\n'")
    controls(o, 'string literal corrupted by output escaping', x, 1)
    x = deepcopy(OCTET_GOOD); x['edge'] = {'job':{'fields':['x'],'sequence':0},'expected':'0|1:x;\r\n'}
    controls(o, 'witness agrees with faulty encoder', x, 1)
    x = deepcopy(OCTET_GOOD); x['edge']['job'] = ['é']
    controls(o, 'job object replaced by positional list', x, 1)
    x = deepcopy(OCTET_GOOD); x['source']=GOOD_SOURCE.replace('    return answer','    fields.clear()\n    return answer')
    controls(o, 'correct frame with mutated input', x, 1)
    x = json.dumps(OCTET_GOOD,ensure_ascii=False)
    controls(o, 'object with duplicate top-level key', ('{"sample":null,' + x[1:]).encode(),1)
    controls(o, 'fenced valid JSON', ('```json\n'+x+'\n```').encode(),1)
    controls(o, 'invalid UTF-8', b'{"source":"\xff"}', 1)
    return results


if __name__ == '__main__':
    print(json.dumps(run(),indent=2))
