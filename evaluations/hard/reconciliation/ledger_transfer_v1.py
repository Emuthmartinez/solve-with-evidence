"""Frozen two-turn transfer. Export only prompt() to solvers after the parent freeze."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile

import check_execution as activity
from ledger import CALCULATOR

CASE = 'ledger-h2'

RULES = """Implement settle(charges, slots), a pure integer apportionment function. charges is a dictionary from distinct nonempty ASCII identifiers to nonnegative integer weights. slots is a nonnegative integer. Return a dictionary containing every input identifier with its nonnegative integer allocation, including zero recipients. Empty input returns {}. When the total weight is positive, assign each identifier its floor of (slots * weight / total_weight). Award the unallocated slots one each in descending order of the exact fractional remainder, breaking ties by ascending identifier using Python string order. With zero total weight return all zero allocations even if slots are available. Counts and weights may exceed 2**53. For positive total weight the returned integers must sum to slots regardless of insertion order. Leave the input unchanged."""
AMEND = """A contract update adds mixed inputs and individual ceilings. Keep the same function interface. A bare integer value still denotes its old weight and an unlimited ceiling. A value of the form {"weight":w,"cap":c} denotes a nonnegative integer weight and a nonnegative integer hard ceiling. Start all allocations at zero. Only positive-weight identifiers with remaining capacity participate. In each round, compute the full ordinary largest-remainder proposals from the remaining slots and eligible weights, applying the previous tie rule. Grant each proposal up to the remaining capacity of that identifier. Subtract the actual grants, then repeat with remaining eligible identifiers until the slots are assigned or nobody eligible remains. Return every input identifier. Unassigned slots are allowed when capacity or positive weights are exhausted. Preserve stage-one behavior for bare integer inputs."""
FORMAT = """Return only JSON with 'source', 'result', and 'edge'. 'source' is a standalone standard-library Python definition of settle(charges, slots); use no I/O or environment access. 'result' is the returned dictionary on the supplied instance. 'edge' is an object with keys 'charges', 'slots' and 'expected' for a valid input of at most five identifiers whose correct allocation differs from the faulty implementation described below. General correctness and agreement on the supplied instance both count."""
BUG1 = 'The faulty allocator resolves equal fractional remainders by original dictionary insertion order instead of ascending identifier; every other rule is unchanged.'
BUG2 = 'The faulty allocator computes the first round and clips grants to ceilings correctly, then stops, even if slots remain and another eligible identifier has capacity.'


def instance(stage):
    if stage == 1:
        return {'zebra': 7, 'gale': 5, 'fern': 5, 'iris': 0, 'alder': 5}, 7
    return {'zebra': {'weight': 7, 'cap': 1}, 'gale': 5, 'fern': {'weight': 5, 'cap': 2},
            'iris': {'weight': 0, 'cap': 9}, 'alder': {'weight': 5, 'cap': 4}}, 11


def prompt(case, stage):
    if case != CASE or stage not in (1, 2):
        raise ValueError('unknown transfer case or stage')
    charges, slots = instance(stage)
    return '\n\n'.join([RULES if stage == 1 else AMEND, FORMAT, BUG1 if stage == 1 else BUG2,
                        'Supplied instance: ' + json.dumps({'charges':charges, 'slots':slots}, separators=(',', ':'))])


def canonical(charges, slots, mutant=None):
    weights = {k: v if type(v) is int else v['weight'] for k,v in charges.items()}
    capacity = {k: slots if type(v) is int else v['cap'] for k,v in charges.items()}
    grants = {k:0 for k in charges}
    left = slots
    while left:
        eligible = [k for k in weights if weights[k] and grants[k] < capacity[k]]
        if not eligible:
            break
        total = sum(weights[k] for k in eligible)
        allocation, residue = {}, {}
        for k in eligible:
            allocation[k], residue[k] = divmod(left * weights[k], total)
        remaining = left - sum(allocation.values())
        order = sorted(eligible, key=lambda k: -residue[k]) if mutant == 'insertion' else sorted(
            eligible, key=lambda k: (-residue[k], k))
        for k in order[:remaining]:
            allocation[k] += 1
        last_left = left
        for k in eligible:
            given = min(allocation[k], capacity[k] - grants[k])
            grants[k] += given
            left -= given
        if mutant == 'clip_once':
            break
        if left >= last_left:
            raise AssertionError('reference made no progress')
    return grants


def valid(charges, slots, stage):
    if not isinstance(charges,dict) or type(slots) != int or not 0 <= slots <= 10**80:
        return False
    for key, value in charges.items():
        if not isinstance(key,str) or not key or not key.isascii():
            return False
        if stage == 2 and isinstance(value,dict):
            if set(value) != {'weight','cap'} or any(type(x) != int or not 0 <= x <= 10**80 for x in value.values()):
                return False
        elif type(value) != int or not 0 <= value <= 10**80:
            return False
    return True


def inputs(stage):
    numeric = [({}, 7), ({'x':0,'y':0}, 9), ({'x':2}, 0), ({'z':3,'a':3}, 1),
               ({'z':2**55+1,'a':2**55}, 1), ({'b':3,'Z':2,'x':0}, 2**54+7)]
    amendments = [
        ({'a':{'weight':4,'cap':1},'b':1}, 9),
        ({'a':{'weight':9,'cap':0},'b':{'weight':1,'cap':2},'z':0}, 4),
        ({'z': {'weight':12,'cap':1}, 'x':{'weight':6,'cap':4},'a':2},13),
        ({'y':{'weight':0,'cap':2},'x':0},20),
        ({'z':{'weight':1,'cap':0},'a':{'weight':0,'cap':3}},5),
        ({'a':{'weight':2**55,'cap':2**18},'z':2**55+1,'q':1},2**20+3),
    ]
    groups = {'instance':[instance(stage)], 'exact_and_edge':numeric}
    if stage == 2:
        groups['ceiling_rounds'] = amendments
    rng = random.Random(147881 + stage)
    generated = []
    for _ in range(32):
        keys = list('czkAye')[:rng.randint(1,6)]
        rng.shuffle(keys)
        charges = {}
        for key in keys:
            weight = rng.choice((0,1,2,3,4,17,2**55+1,2**55+2))
            charges[key] = ({'weight':weight,'cap':rng.choice((0,1,2,9,17))}
                            if stage == 2 and rng.random() < .65 else weight)
        generated.append((charges, rng.choice((0,1,2,6,11,43,2**54+3))))
    groups['seeded'] = generated
    groups['metamorphic'] = []
    for charges,slots in [instance(stage), *generated[:7]]:
        groups['metamorphic'].append((dict(reversed(list(charges.items()))),slots))
        scaled = {k: v*13 if type(v) is int else {'weight':v['weight']*13,'cap':v['cap']}
                  for k,v in charges.items()}
        groups['metamorphic'].append((scaled,slots))
    return groups


CHILD = """
space = {"__name__": "__candidate__"}
exec(compile(src, "<submitted function>", "exec"), space)
actual = []
for original, slots in batch:
    charges = json.loads(json.dumps(original))
    try:
        result = space["settle"](charges, slots)
        valid = isinstance(result, dict) and all(isinstance(k,str) and type(v) is int for k,v in result.items())
        actual.append({"result": dict(result) if valid else None, "pure": charges == original})
    except Exception as exc:
        actual.append({"error":type(exc).__name__})
print(json.dumps(actual,separators=(",",":")))
"""


def execute(src, batch):
    if not isinstance(src,str) or len(src.encode()) > 32768:
        return [], 'missing or oversized source'
    code = f'src = {src!r}\nbatch = {batch!r}\n' + CHILD
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            p = subprocess.run([sys.executable, '-I', '-B', '-S', str(CALCULATOR)],input=code.encode(),
                               env={'LC_ALL':'C'}, cwd='/', stdout=stdout, stderr=stderr, timeout=6)
        except subprocess.TimeoutExpired:
            return [], 'calculator timeout'
        if p.returncode:
            return [], 'calculator exit ' + str(p.returncode)
        stdout.seek(0)
        try:
            results = json.loads(stdout.read(65536))
        except (ValueError,UnicodeDecodeError):
            return [], 'invalid calculator output'
        return (results, None) if isinstance(results,list) and len(results) == len(batch) else ([], 'count mismatch')


def exact_dict(value, expected):
    return isinstance(value, dict) and all(type(x) is int for x in value.values()) and value == expected


def grade(case, replies):
    if case != CASE:
        raise ValueError('unknown transfer case')
    checks, details = {}, {}
    for stage in (1,2):
        response = replies[stage-1] if len(replies) >= stage and isinstance(replies[stage-1],dict) else {}
        suites = inputs(stage)
        flat = [(g, data, slots) for g,pairs in suites.items() for data,slots in pairs]
        actual, error = execute(response.get('source'), [(data,slots) for _,data,slots in flat])
        tally = dict.fromkeys(suites,0)
        pure = len(actual) == len(flat)
        for (g, data, slots), observed in zip(flat, actual):
            ok = isinstance(observed,dict) and observed.get('pure') is True
            pure &= ok
            if ok and exact_dict(observed.get('result'), canonical(data,slots)):
                tally[g] += 1
        detail = {g: tally[g] == len(pairs) for g,pairs in suites.items()}
        detail['pure'] = pure
        detail['reported_result'] = exact_dict(response.get('result'),canonical(*instance(stage)))
        edge = response.get('edge')
        edge = edge if isinstance(edge,dict) else {}
        charges,slots = edge.get('charges'),edge.get('slots')
        witness = isinstance(charges,dict) and 0 < len(charges) <= 5 and valid(charges,slots,stage)
        if witness:
            answer = canonical(charges,slots)
            witness = (exact_dict(edge.get('expected'),answer) and answer !=
                       canonical(charges,slots,'insertion' if stage == 1 else 'clip_once'))
        detail['counterexample'] = witness
        for name,ok in detail.items():
            checks[f'stage{stage}_{name}'] = {'passed':bool(ok),'weight':2 if name in ('seeded','ceiling_rounds') else 1}
        details[str(stage)] = {'matched':tally,'totals':{g:len(pairs) for g,pairs in suites.items()},'runtime_error':error}
    failures = [k for k,v in checks.items() if not v['passed']]
    return {'case':case,'pass':not failures,'points':sum(v['weight'] for v in checks.values() if v['passed']),
            'max_points':sum(v['weight'] for v in checks.values()),'critical_failures':failures,
            'checks':checks,'execution':details}


class TransferInspection(activity.Inspection):
    """Reuse evidence handling, substituting the transfer signature and oracle."""
    def __init__(self, stage, src, stdout):
        brain = ast.parse(src)
        definitions = [n for n in brain.body if isinstance(n, ast.FunctionDef) and n.name == 'settle']
        self.target = activity.tree_key(definitions[-1]) if definitions else ''
        self.simple = bool(definitions) and activity.self_contained(brain, definitions[-1])
        self.imports, self.required_imports, self.env, self.modules = {}, {}, {}, {}
        for stmt in brain.body:
            self.required_imports.update(activity.import_bindings(stmt))
        self.stdout, self.stage, self.invoked, self.ambiguous, self.proof = stdout, stage, False, False, None

    def statements(self, statements, depth=0):
        for stmt in statements:
            if isinstance(stmt, ast.FunctionDef) and stmt.name == 'settle':
                self.env['settle'] = (activity.FN, activity.tree_key(stmt) == self.target)
            else:
                super().statements([stmt], depth)

    def expr(self, node):
        if isinstance(node, ast.Call):
            fn = self.expr(node.func)
            if fn and fn[0] == activity.FN:
                self.invoked = True
                imports_ok = all(self.imports.get(n) == val for n,val in self.required_imports.items())
                matches = fn[1] and self.simple and imports_ok
                self.ambiguous |= not matches
                args = dict(zip(('charges','slots'),[self.expr(arg) for arg in node.args]))
                args.update({kw.arg:self.expr(kw.value) for kw in node.keywords})
                charges, slots = args.get('charges'), args.get('slots')
                if not charges or not slots or charges[0] != activity.DATA or slots[0] != activity.DATA:
                    self.ambiguous = True
                    return None
                data, count = charges[1], slots[1]
                if not valid(data,count,self.stage) or not data or count == 0:
                    return None
                if self.stage == 2 and not any(isinstance(v,dict) for v in data.values()):
                    return None
                expected = canonical(data,count)
                return activity.OUT, {'matches':matches, 'expected':expected,
                    'input_sha256':hashlib.sha256(activity.blob([data,count])).hexdigest()}
        return super().expr(node)


def assess(stage, text, rows):
    answer = activity.answer(text)
    item_ids = [r['data']['item']['id'] for r in rows if r['kind'] == 'item/completed' and
                r['data']['item']['type'] == 'agentMessage' and r['data']['item'].get('phase') in (None,'final_answer')
                and r['data']['item']['text'] == text]
    record = {'stage':stage,'automated':'no_evidence','proof':None,'python_calls':0,
              'successful_calls_before_answer':[],'manual_candidates':[]}
    if not item_ids or not isinstance(answer,str):
        record['automated'] = 'unassessable'
        return record
    final = min(r['seq'] for r in rows if r['kind'] in ('item/started','item/completed') and
                r['data']['item']['id'] == item_ids[-1])
    calls = {}
    for row in rows:
        if row['seq'] >= final:
            break
        kind, data = row['kind'], row['data']
        if kind == 'tool_call' and data['tool'] == 'python':
            record['python_calls'] += 1
            calls[data['callId']] = data['arguments']['code']
        elif kind == 'tool_result' and data['tool'] == 'python' and data['callId'] in calls:
            try:
                reply = data['result']
                execution = json.loads(reply['contentItems'][0]['text'])
                if reply['success'] is not True or type(execution['exit_code']) != int or execution['exit_code'] or execution['timed_out']:
                    continue
            except (KeyError, ValueError, IndexError, TypeError):
                continue
            call_id = data['callId']
            record['successful_calls_before_answer'].append(call_id)
            try:
                check = TransferInspection(stage, answer, execution['stdout'])
                check.statements(ast.parse(calls[call_id]).body)
            except (TypeError, ValueError, SyntaxError, RecursionError):
                record['manual_candidates'].append(call_id)
                continue
            if check.proof:
                record['proof'] = {'call_id':call_id,'result_seq':row['seq'],**check.proof}
                record['automated'] = 'verified'
            elif check.ambiguous:
                record['manual_candidates'].append(call_id)
    if record['manual_candidates'] and not record['proof']:
        record['automated'] = activity.MANUAL
    return record


def report(path, reviews=None):
    path = Path(path)
    manifest = json.loads((path/'manifest.json').read_text())
    for name in ('trace.jsonl','summary.json'):
        if hashlib.sha256((path/name).read_bytes()).hexdigest() != manifest[name]:
            raise ValueError('trial integrity mismatch')
    meta = json.loads((path/'summary.json').read_text())
    if meta['case_id'] != CASE:
        raise ValueError('unknown transfer case')
    rows = [json.loads(row) for row in (path/'trace.jsonl').read_text().splitlines()]
    results = []
    for turn in meta['turns']:
        stage = turn['stage']
        item = assess(stage, turn['text'], [r for r in rows if r['stage'] == stage])
        item['verdict'] = item['automated']
        review = (reviews or {}).get(f'{path.name}/{stage}')
        if review:
            if (item['automated'] != activity.MANUAL or review.get('call_id') not in item['manual_candidates'] or
                review.get('verdict') not in ('verified','no_evidence') or
                not all(isinstance(review.get(k),str) and review[k].strip() for k in ('reviewer','reason'))):
                raise ValueError('invalid independent equivalence review')
            item.update(manual_review=review, verdict=review['verdict'])
        results.append(item)
    return {'trial':path.name,'case':CASE,'trial_status':meta['status'],'turns':results}


def controls():
    import inspect
    baseline = inspect.getsource(canonical)
    def submission(stage, fault):
        example = ({'z':1,'a':1}, 1) if stage == 1 else ({'a':{'weight':9,'cap':1},'b':1},10)
        return {'source':baseline + f'\ndef settle(charges,slots):\n    return canonical(charges,slots,{fault!r})',
                'result':canonical(*instance(stage)), 'edge':{'charges':example[0],'slots':example[1],
                                                               'expected':canonical(*example)}}
    good = [submission(1,None),submission(2,None)]
    if not grade(CASE,good)['pass']:
        raise AssertionError('reference fails')
    controls = {'reference_passed':True}
    for key, mutation in [('wrong_tie',[submission(1,'insertion'),good[1]]),
                          ('clipped_once',[good[0],submission(2,'clip_once')]),
                          ('constant',[dict(x,source='def settle(charges,slots):\n    return ' + repr(x['result']))
                                       for x in good]),
                          ('false_witness',[dict(x,edge={}) for x in good]),
                          ('host_read',[dict(x,source="def settle(charges,slots):\n    return open('/etc/hosts').read()")
                                        for x in good])]:
        if grade(CASE,mutation)['pass']:
            raise AssertionError(key)
        controls[key] = 'rejected'
    source = 'def settle(charges,slots):\n    return {"k":slots}'
    for name, stage, code, expected, ambiguous in [
        ('direct',1,source + '\nprint(settle({"k":1}, 3))',True,False),
        ('exec_bind',2,'s='+repr(source)+'\nns={}\nexec(s,ns)\nf=ns["settle"]\nx=f({"k":{"weight":4,"cap":3}},3)\nassert x == {"k":3}',True,False),
        ('no_new_semantics',2,source+'\nprint(settle({"k":1},3))',False,False),
        ('unapplied',1,source+'\nprint({"k":3})',False,False),
        ('requires_equivalence',1,source.replace('slots}', 'int(slots)}')+'\nprint(settle({"k":1},3))',False,True)]:
        insp = TransferInspection(stage, source, '{"k":3}\n')
        insp.statements(ast.parse(code).body)
        if bool(insp.proof) != expected or insp.ambiguous != ambiguous:
            raise AssertionError(name)
        controls[name] = 'passed'
    return controls


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--controls',action='store_true')
    ap.add_argument('--reviews',type=Path)
    ap.add_argument('trial',type=Path,nargs='*')
    args = ap.parse_args()
    if args.controls:
        print(json.dumps(controls(),indent=2))
    if args.trial:
        reviews = json.loads(args.reviews.read_text()) if args.reviews else None
        print(json.dumps([report(path,reviews) for path in args.trial],indent=2))
