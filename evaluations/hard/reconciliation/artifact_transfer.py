"""Prospective transfer for the JSON delivery of an executable text artifact."""
import argparse
import inspect
import json
import random
import subprocess
import sys
import tempfile

from ledger import CALCULATOR

CASE = 'artifact-h3'
RULES = """A label printer stores rows in a small text format. Deliver a pure Python function render(rows) that returns the exact wire text. 'rows' is a list of rows, each a nonempty list of Unicode strings. Encode each input character exactly once. Backslash becomes two backslashes, a vertical bar becomes backslash followed by vertical bar, a line feed becomes backslash followed by the lowercase letter n; other characters (including a double quote, a carriage return, a tab and non-ASCII text) pass through unchanged. Join fields with one raw vertical bar. End every row with one actual line feed; empty input returns the empty string. Do not edit the input. Literal backslash+n and an actual line feed are different inputs. The returned text must preserve that difference."""
DELTA = """A printer update adds optional multiline labels. Update the function to render(rows, block=False). Calls with no second argument or with False must preserve the original format. With block=True, any field that contains an actual line feed uses block encoding: surround the original field with one double quote at each end, double every original double quote, and leave all its other original characters (including backslash, vertical bar, and line feed) untouched. A field without an actual line feed still uses the original encoding even if it contains a quote or the two literal characters backslash+n. Row and field delimiters do not change, and empty input still returns the empty string."""
FORMAT = """Return only a JSON object with keys 'source', 'result', and 'edge'. 'source' is the complete standalone standard-library Python function, ready for a caller to import. 'result' is the exact string your function returns for the supplied job. 'edge' is an object containing a valid job with at most two rows under 'job' and its exact correct string under 'expected'. Choose an edge where the specific faulty encoder below disagrees with the correct output. No I/O or process access."""
BUG = ["The faulty encoder treats a literal backslash immediately followed by a lowercase n as if those two characters were one actual line feed before it encodes the input.",
       "The faulty encoder uses block encoding for the entire row whenever any field in the row contains an actual line feed; it wraps and double-quotes every field in that row instead of only the multiline fields."]


def instance(stage):
    rows = [['rack|7', 'C:\\lot\\new', 'S\nT'], ['"ok"', '', 'line\\n', 'mā']]
    return {'rows':rows} if stage == 1 else {'rows':[rows[0], ['"one"\n|two\\', 'C:\\new', ''], ['plain','|']], 'block':True}


def prompt(case, stage):
    if case != CASE or stage not in (1, 2):
        raise ValueError('unknown case/stage')
    return '\n\n'.join([RULES if stage == 1 else DELTA, FORMAT, BUG[stage-1],
                        'Supplied job (JSON): ' + json.dumps(instance(stage), ensure_ascii=False)])


def duplicate(obj):
    return json.loads(json.dumps(obj,ensure_ascii=False))


def wire(rows, block=False, fault=''):
    slash = chr(92)
    encode = {slash:slash*2, '|':slash+'|', '\n':slash+'n'}
    out = []
    for row in rows:
        any_multiline = any('\n' in s for s in row)
        fields = []
        for field in row:
            if fault == 'literal_n':
                field = field.replace(slash+'n','\n')
            block_field = any_multiline if fault == 'whole_row' else '\n' in field
            if block and block_field:
                fields.append('"' + field.replace('"','""') + '"')
            else:
                fields.append(''.join(encode.get(ch,ch) for ch in field))
        out.append('|'.join(fields) + '\n')
    return ''.join(out)


def suites(stage):
    groups = {'supplied':[instance(stage)], 'edges': [{'rows':rs} for rs in
              ([], [['']], [['a','']], [['','a']], [['\n','\\n','|','\\']],
               [['\r\n','\t','"','ñ']], [['\\|\\n'],['foo','|','']])]}
    if stage == 2:
        groups['block'] = [{'rows':rs,'block':True} for rs in (
            [], [['"']], [['\n']], [['x\ny','|\\n','z']], [['"\n"','\n\\|']],
            [['','\n'],['"plain"']], [['\r','x\\n','\r\n']]
        )] + [{'rows':[['a\\n','x\nz','"']],'block':False}]
    rng = random.Random(372191 + stage)
    alphabet = ['a','|','\\','n','\n','"','\r','\t','ñ','中','😀']
    groups['generated'] = []
    for i in range(24):
        rows = [[''.join(rng.choice(alphabet) for _ in range(rng.randrange(10))) for _ in range(rng.randint(1,4))]
                for _ in range(rng.randrange(5))]
        job = {'rows':rows}
        if stage == 2 and i % 3 != 0:
            job['block'] = i % 3 == 1
        groups['generated'].append(job)
    groups['row_composition'] = []
    for job in [instance(stage),*groups['generated'][:5]]:
        groups['row_composition'].extend([{**job,'rows':job['rows']+job['rows']},
                                          {**job,'rows':list(reversed(job['rows']))}])
    return groups


CHILD = """
space = {"__name__":"__candidate__"}
exec(compile(candidate,"<delivered source>","exec"),space)
actual = []
for item in inputs:
    job = json.loads(json.dumps(item))
    try:
        result = space["render"](**job)
        actual.append({"result":result if type(result) is str else None, "pure":job==item})
    except Exception as exc:
        actual.append({"error":type(exc).__name__})
print(json.dumps(actual, ensure_ascii=True))
"""


def run(src, inputs):
    if not isinstance(src,str) or not src.strip() or len(src.encode()) > 32768:
        return [], 'missing or oversized decoded source'
    code = f'candidate = {src!r}\ninputs = {inputs!r}\n' + CHILD
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            p = subprocess.run([sys.executable,'-I','-B','-S',str(CALCULATOR)],input=code.encode(),
                               cwd='/', env={'LC_ALL':'C'}, stdout=out,stderr=err,timeout=6)
        except subprocess.TimeoutExpired:
            return [], 'calculator timeout'
        if p.returncode:
            return [], 'calculator exit ' + str(p.returncode)
        out.seek(0)
        try:
            actual = json.loads(out.read(65536))
        except (ValueError,UnicodeDecodeError):
            return [], 'invalid calculator result'
    if not isinstance(actual,list) or len(actual) != len(inputs):
        return [], 'result count mismatch'
    return actual,None


def valid_edge(edge, stage):
    if not isinstance(edge,dict) or not isinstance(edge.get('job'),dict):
        return False
    job = edge['job']
    if (set(job) not in ({'rows'},{'rows','block'}) or
        'block' in job and (stage == 1 or type(job['block']) is not bool)):
        return False
    rows = job['rows']
    if (not isinstance(rows,list) or len(rows) > 2 or
        any(not isinstance(r,list) or not r or len(r)>128 or
            any(not isinstance(f,str) or len(f)>4096 for f in r) for r in rows)):
        return False
    correct = wire(**job)
    return edge.get('expected') == correct != wire(**job,fault='literal_n' if stage == 1 else 'whole_row')


def grade(case,replies):
    if case != CASE:
        raise ValueError('unknown case')
    checks,execution = {},{}
    for stage in (1,2):
        answer = replies[stage-1] if len(replies) >= stage and isinstance(replies[stage-1],dict) else {}
        groups = suites(stage)
        flat = [(group,job) for group,jobs in groups.items() for job in jobs]
        actual,error = run(answer.get('source'), [job for _,job in flat])
        matched = dict.fromkeys(groups,0)
        pure = len(actual) == len(flat)
        for (group,job),item in zip(flat,actual):
            intact = isinstance(item,dict) and item.get('pure') is True
            pure &= intact
            if intact and item.get('result') == wire(**job):
                matched[group] += 1
        fields = {g:matched[g] == len(jobs) for g,jobs in groups.items()}
        fields.update(delivered_fields=(set(answer)=={'source','result','edge'} and
                                        isinstance(answer.get('source'),str) and isinstance(answer.get('result'),str)
                                        and isinstance(answer.get('edge'),dict)),
                      reported_result=answer.get('result') == wire(**instance(stage)),
                      counterexample=valid_edge(answer.get('edge'),stage), pure=pure)
        for name,passed in fields.items():
            checks[f'stage{stage}_{name}'] = {'passed':bool(passed),'weight':1}
        execution[str(stage)] = {'matched':matched, 'totals':{g:len(v) for g,v in groups.items()}, 'runtime_error':error}
    failures = [k for k,x in checks.items() if not x['passed']]
    return {'case':case,'points':len(checks)-len(failures),'max_points':len(checks),'pass':not failures,
            'critical_failures':failures,'checks':checks,'execution':execution}


def controls():
    template = inspect.getsource(wire)
    good = []
    for stage in (1,2):
        job = {'rows':[['\\n']]} if stage == 1 else {'rows':[['\n','x']],'block':True}
        good.append({'source':template+'\ndef render(rows,block=False):\n    return wire(rows,block)',
                     'result':wire(**instance(stage)), 'edge':{'job':job,'expected':wire(**job)}})
    if not grade(CASE,good)['pass']:
        raise AssertionError('reference rejected')
    def check(tag,replies):
        if grade(CASE,replies)['pass']:
            raise AssertionError(tag)
        return tag
    receipts = ['reference accepted']
    for stage,bug in enumerate(('literal_n','whole_row'),1):
        altered = duplicate(good)
        altered[stage-1]['source'] = template+f'\ndef render(rows,block=False):\n    return wire(rows,block,{bug!r})'
        receipts.append(check(bug,altered))
    wrong = duplicate(good)
    wrong[0]['source'] = 'def render(rows):\n    return "unterminated'
    receipts.append(check('JSON-decodable but invalid delivered Python',wrong))
    try:
        json.loads(r'{"source":"def render(rows):\q"}')
    except ValueError:
        receipts.append(check('malformed delivery object as received by dispatcher',[{},good[1]]))
    else:
        raise AssertionError('invalid JSON control was not invalid')
    receipts.append(check('correct answer with wrong code',[dict(x,source='def render(rows,block=False):\n    return ""') for x in good]))
    receipts.append(check('wrong reported escape',[dict(x,result=x['result'].replace('\\','')) for x in good]))
    receipts.append(check('host read',[dict(x,source="def render(rows,block=False):\n    return open('/etc/hosts').read()") for x in good]))
    return receipts


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--controls',action='store_true')
    if p.parse_args().controls:
        print(json.dumps({'passed':controls()}))
