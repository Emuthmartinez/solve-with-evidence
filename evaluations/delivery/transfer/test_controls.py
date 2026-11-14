"""Hand-worked byte positions, alternate witnesses and malformed/semantic controls."""
import copy
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
# Offsets and reads derived by counting each record on paper, independently of consumer.
gold = {
    'packet': {
        'wire': 'μ:n\t\x1eQ\\":雪\x1ee:e\u0301\x1eE:🪁\r\n\x1e/:\x1eμ:Ω\x1e',
        'payloads': [dict(record=i,begin=a,end=b) for i,(a,b) in enumerate(
            [(3,5),(10,13),(16,19),(22,28),(31,31),(35,37)])],
        'reads': [[],[0],[1],[2],[],[3]],
    },
    'proof': {'input': {'window': [4,10]}, 'strict':[0], 'inclusive':[0,1]},
}


def controls():
    outcomes = {}
    def check(name, raw, expected):
        result = subprocess.run([sys.executable, '-B', str(ROOT/'consumer.py'), 'packet-map'],
                                input=raw, capture_output=True, timeout=3)
        if result.returncode != expected:
            raise RuntimeError((name,result.returncode,result.stderr))
        outcomes[name] = 'accepted' if expected == 0 else 'rejected'
    def raw(v):
        return json.dumps(v, ensure_ascii=False).encode('utf-8')
    def change(name, path, val, rc=1):
        p = copy.deepcopy(gold)
        node = p
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = val
        check(name, raw(p), rc)

    encoded = raw(gold)
    check('hand counted reference', encoded, 0)
    check('different JSON serialization', json.dumps(gold, indent=2).encode()+b'\r\n', 0)
    change('alternate counterexample at empty text', ['proof'],
           {'input':{'window':[27,31]}, 'strict':[3], 'inclusive':[3,4]}, 0)
    change('valid but identical overlap predicates', ['proof'],
           {'input':{'window':[3,4]}, 'strict':[0], 'inclusive':[0]})
    change('stated outputs swapped', ['proof','strict'], [0,1])
    change('bare window in proof.input', ['proof','input'], [4,10])
    change('incorrect already-paired inclusive results', ['proof','inclusive'], [0,2])
    change('forged wider mixed integer span', ['packet','payloads',1,'begin'], 9)
    change('true used as a record ID', ['packet','payloads',1,'record'], True)
    change('NFC substitution changes wire', ['packet','wire'], gold['packet']['wire'].replace('e\u0301','é'))
    change('CRLF rewritten as LF', ['packet','wire'], gold['packet']['wire'].replace('\r\n','\n'))
    change('empty query contributes one hit', ['packet','reads',4], [2])
    check('duplicate nested key', encoded.replace(b'"strict":',b'"strict":[],"strict":',1),1)
    check('markdown fence', b'```json\n'+encoded+b'\n```',1)
    return outcomes


if __name__ == '__main__':
    print(json.dumps(controls(), indent=2))
