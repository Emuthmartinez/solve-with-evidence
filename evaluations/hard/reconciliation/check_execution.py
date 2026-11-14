"""Audit pre-submission test evidence without changing the frozen scoring endpoint.

The automatic rule matches executed top-level audit source (as parsed Python AST)
and witnesses a call on concrete records. Stage 2 must exercise its amendment or
fence. A reported dictionary must appear in the captured stdout on that call,
or a concrete expected-return assertion must run successfully. All positive
static matches are leads requiring independent trace readback before credit. No candidate
Python is executed here. Runtime checks come only from the captured calculator.

Different ASTs, helpers, loops, indirect invocation, and opaque output formats
can require review. An independent reviewer may inspect the linked call, result
and submitted code for semantic equivalence on the full documented domain.
Record the justification with --reviews; never certify from similar outputs
alone. The automated result stays visible beside that review.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

from ledger import CASES, reference


UNKNOWN = object()
DATA = 'data'
FN = 'function'
OUT = 'output'
BUILTIN = 'builtin'
MANUAL = 'manual_review'


def blob(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def tree_key(node):
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def literal(node):
    try:
        return ast.literal_eval(node)
    except (TypeError, ValueError, SyntaxError, RecursionError):
        return UNKNOWN


def fn_nodes(source):
    root = ast.parse(source)
    defs = [s for s in root.body if isinstance(s, ast.FunctionDef) and s.name == 'audit']
    return root, defs[-1] if defs else None


def self_contained(root, func):
    # Imports are commonly factored differently inside and outside the function.
    # Any other top-level state/helper could change what the same audit body does.
    return all(s is func or isinstance(s, (ast.Import, ast.ImportFrom)) or
               isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and
               isinstance(s.value.value, str) for s in root.body)


def import_bindings(statement):
    if isinstance(statement, ast.Import):
        return {a.asname or a.name.split('.')[0]: ('import', a.name) for a in statement.names}
    if isinstance(statement, ast.ImportFrom):
        return {a.asname or a.name: ('from', statement.level, statement.module, a.name)
                for a in statement.names}
    return {}


def representative(case, stage, events, at):
    if type(at) != int or not isinstance(events, list) or not events or len(events) > 500:
        return None
    allowed = ('ack', 'fence') if case == CASES[1] else ('obs', 'fix')
    try:
        if any(not isinstance(r.get('key'), str) or r['kind'] not in allowed[:stage] or
               type(r['seen']) != int for r in events):
            return None
        eligible = [r for r in events if r['seen'] <= at]
        if stage == 2 and not any(r['kind'] == allowed[1] for r in eligible):
            return None
        result = reference(case, stage, events, at)
        # A fence-only key has observable semantics; unseen future-only inputs do not.
        return result if result else None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def stdout_contains(stdout, expected):
    for line in [stdout.strip()]:
        # Accept a standalone dict or the dict portion of a labelled output.
        if '\n' in line or '\r' in line:
            continue
        left, right = line.find('{'), line.rfind('}')
        if left < 0 or right < left:
            continue
        value = line[left:right + 1]
        try:
            observed = json.loads(value)
        except ValueError:
            try:
                observed = ast.literal_eval(value)
            except (ValueError, SyntaxError, RecursionError):
                continue
        if observed == expected:
            return True
    return False


class Inspection:
    def __init__(self, case, stage, source, stdout):
        self.case, self.stage, self.stdout = case, stage, stdout
        tree, target = fn_nodes(source)
        self.target = tree_key(target) if target is not None else ''
        self.simple = target is not None and self_contained(tree, target)
        self.imports = {}
        self.required_imports = {}
        for statement in tree.body:
            self.required_imports.update(import_bindings(statement))
        self.env = {}
        self.modules = {}
        self.invoked = False
        self.ambiguous = False
        self.proof = None

    def expr(self, node):
        if isinstance(node, ast.Name):
            return self.env.get(node.id, (BUILTIN, node.id))
        if isinstance(node, ast.Subscript):
            space, member = self.expr(node.value), literal(node.slice)
            if space[0] == DATA and isinstance(space[1], dict):
                if id(space[1]) in self.modules and isinstance(member, str):
                    return self.modules[id(space[1])].get(member)
            return None
        val = literal(node)
        if val is not UNKNOWN:
            return DATA, val
        if not isinstance(node, ast.Call):
            return None
        callee = self.expr(node.func)
        if callee and callee[0] == FN:
            self.invoked = True
            params = dict(zip(('events', 'at'), [self.expr(a) for a in node.args]))
            params.update({a.arg: self.expr(a.value) for a in node.keywords})
            records, at = params.get('events'), params.get('at')
            imports_match = all(self.imports.get(name) == origin for name, origin in self.required_imports.items())
            self.ambiguous |= not callee[1] or not self.simple or not imports_match
            if not (records and at and records[0] == at[0] == DATA):
                self.ambiguous = True
                return None
            expected = representative(self.case, self.stage, records[1], at[1])
            if expected is not None:
                return OUT, {'matches': callee[1] and self.simple and imports_match, 'expected': expected,
                             'input_sha256': hashlib.sha256(blob([records[1], at[1]])).hexdigest()}
        if callee == (BUILTIN, 'compile') and node.args:
            return self.expr(node.args[0])
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == 'json' and node.args:
                first = self.expr(node.args[0])
                if node.func.attr == 'dumps' and first and first[0] == OUT:
                    return first
                if node.func.attr == 'loads' and first and first[0] == DATA:
                    try:
                        return DATA, json.loads(first[1])
                    except (ValueError, TypeError):
                        return None
        return None

    def certify(self, origin, evidence):
        if evidence and evidence[0] == OUT:
            info = evidence[1]
            if info['matches']:
                self.proof = {'evidence': origin, 'input_sha256': info['input_sha256']}
            else:
                self.ambiguous = True

    def statements(self, statements, depth=0):
        if depth > 4:
            self.ambiguous = True
            return
        for statement in statements:
            if isinstance(statement, ast.Raise):
                return  # Unconditional termination precludes later top-level assertions.
            if isinstance(statement, (ast.Import, ast.ImportFrom)):
                self.imports.update(import_bindings(statement))
            elif isinstance(statement, ast.FunctionDef):
                if statement.name == 'audit':
                    self.env['audit'] = (FN, tree_key(statement) == self.target)
                else:
                    self.env[statement.name] = ('helper', statement.name)
            elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
                value = self.expr(statement.value)
                targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        self.env[target.id] = value
                        self.imports.pop(target.id, None)
                    else:
                        self.ambiguous = True
            elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                call = statement.value
                callee = self.expr(call.func)
                if callee == (BUILTIN, 'exec') and call.args:
                    source = self.expr(call.args[0])
                    if not source or source[0] != DATA or not isinstance(source[1], str):
                        self.ambiguous = True
                        continue
                    dest = self.env
                    if len(call.args) > 1:
                        ns = self.expr(call.args[1])
                        if ns and ns[0] == DATA and isinstance(ns[1], dict):
                            dest = self.modules.setdefault(id(ns[1]), {})
                        elif not (isinstance(call.args[1], ast.Call) and isinstance(call.args[1].func, ast.Name)
                                  and call.args[1].func.id in ('globals','locals')):
                            self.ambiguous = True
                            continue
                    original = self.env
                    self.env = dest
                    try:
                        self.statements(ast.parse(source[1]).body, depth + 1)
                    finally:
                        self.env = original
                elif callee == (BUILTIN, 'print'):
                    for arg in call.args:
                        ev = self.expr(arg)
                        if ev and ev[0] == OUT and stdout_contains(self.stdout, ev[1]['expected']):
                            self.certify('reported audit output', ev)
                else:
                    self.expr(call)
            elif isinstance(statement, ast.Assert):
                t = statement.test
                if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
                    a, b = self.expr(t.left), self.expr(t.comparators[0])
                    for ev, expected in ((a,b), (b,a)):
                        if ev and expected and ev[0] == OUT and expected[0] == DATA and ev[1]['expected'] == expected[1]:
                            self.certify('executed oracle-checked assertion', ev)
            elif not isinstance(statement, (ast.Import, ast.ImportFrom, ast.Pass)):
                # Bodies may never have been entered. Their text is never execution evidence.
                self.ambiguous |= any(isinstance(n, ast.Call) for n in ast.walk(statement))


def inspect_call(case, stage, source, code, stdout):
    try:
        check = Inspection(case, stage, source, stdout)
        check.statements(ast.parse(code).body)
        return check.proof, check.ambiguous
    except (SyntaxError, ValueError, TypeError, RecursionError):
        return None, True


def answer(text):
    s = text.strip()
    if s.startswith('```') and s.endswith('```') and '\n' in s:
        s = s.split('\n', 1)[1][:-3].strip()
    try:
        parsed = json.loads(s)
    except ValueError:
        return None
    return parsed.get('source') if isinstance(parsed, dict) else None


def assess(case, turn, rows):
    stage = turn['stage']
    source = answer(turn['text'])
    limits = [r['seq'] for r in rows if r['kind'] == 'item/completed' and
              r['data']['item']['type'] == 'agentMessage' and
              r['data']['item'].get('phase') in (None, 'final_answer') and
              r['data']['item']['text'] == turn['text']]
    result = {'stage': stage, 'automated': 'no_evidence', 'python_calls': 0,
              'successful_calls_before_answer': [], 'manual_candidates': [], 'proof': None}
    if not limits or not isinstance(source, str):
        result['automated'] = 'unassessable'
        return result
    final_seq = limits[-1]
    # A tool result after the final message began cannot establish a pre-submission check.
    item_id = next(r['data']['item']['id'] for r in rows if r['seq'] == final_seq)
    begins = [r['seq'] for r in rows if r['kind'] == 'item/started' and
              r['data']['item'].get('id') == item_id]
    boundary = min(begins + [final_seq])
    calls = {}
    for row in rows:
        if row['seq'] >= boundary:
            continue
        kind, data = row['kind'], row['data']
        if kind == 'tool_call' and data['tool'] == 'python':
            result['python_calls'] += 1
            calls[data['callId']] = data['arguments'].get('code', '')
        elif kind == 'tool_result' and data['callId'] in calls and data['tool'] == 'python':
            try:
                reply = data['result']
                run = json.loads(reply['contentItems'][0]['text'])
                if reply['success'] is not True or type(run['exit_code']) != int or run['exit_code'] != 0 or run['timed_out']:
                    continue
            except (ValueError, TypeError, AttributeError, KeyError, IndexError):
                continue
            call_id = data['callId']
            result['successful_calls_before_answer'].append(call_id)
            proof, ambiguous = inspect_call(case, stage, source, calls[call_id], run['stdout'])
            if proof:
                result['automated'] = MANUAL
                result['manual_candidates'].append(call_id)
                result['proof'] = {'call_id':call_id, 'result_seq':row['seq'], **proof}
            elif ambiguous:
                result['manual_candidates'].append(call_id)
    if not result['proof'] and result['manual_candidates']:
        result['automated'] = MANUAL
    return result


def apply_review(item, review):
    item['verdict'] = item['automated']
    if not review:
        return
    if (item['automated'] != MANUAL or review.get('call_id') not in item['manual_candidates']
        or review.get('verdict') not in ('verified','no_evidence') or
        not all(isinstance(review.get(k),str) and review[k].strip() for k in ('reviewer','reason'))):
        raise ValueError('Invalid independent trace review')
    item.update(verdict=review['verdict'], manual_review=review)


def report(path, reviews=None):
    files = json.loads((path / 'manifest.json').read_text())
    for key in ('trace.jsonl','summary.json'):
        if hashlib.sha256((path / key).read_bytes()).hexdigest() != files[key]:
            raise ValueError('Trial integrity mismatch: ' + key)
    summary = json.loads((path / 'summary.json').read_text())
    case = summary['case_id']
    if case not in CASES:
        raise ValueError('Not a ledger trial')
    rows = [json.loads(x) for x in (path / 'trace.jsonl').read_text().splitlines()]
    replies = []
    for turn in summary['turns']:
        stage = turn['stage']
        item = assess(case, turn, [r for r in rows if r['stage'] == stage])
        apply_review(item, (reviews or {}).get(f'{path.name}/{stage}'))
        replies.append(item)
    return {'trial':path.name, 'case':case, 'trial_status':summary['status'], 'turns':replies}


def fixtures():
    # Named controls are records in the exact runner event shape, without executing fixture code.
    src = "def audit(events, at):\n    return {r['key']: r['state'] for r in events}"
    data = [{'kind':'obs','key':'a','rev':1,'seen':5,'stamp':5,'state':'arrived'}]
    call = f"audit({data!r}, 7)"
    check = "assert got == {'a': 'arrived'}"
    observed = "{'a': 'arrived'}\n"
    cases = {
        'direct_print': (src + '\nprint(' + call + ')', observed, 0, False, MANUAL),
        'assigned_result_assert': (src + '\ngot = ' + call + '\n' + check, '', 0, False, MANUAL),
        'exec_literal': ('exec(' + repr(src) + ')\nprint(' + call + ')', observed, 0, False, MANUAL),
        'exec_variable_namespace': ('s = ' + repr(src) + "\nns = {}\nexec(s,ns)\nf = ns['audit']\ngot = f(" +
                                    repr(data) + ",7)\n" + check, '', 0, False, MANUAL),
        'conflicting_source': (src.replace("r['state']", "'arrived'") + '\nprint(' + call + ')',
                               observed, 0, False, MANUAL),
         'changed_import': ('import cmath as math\n' + src + '\nprint(' + call + ')', observed, 0, False, MANUAL),
        'defined_only': (src + "\nprint({'a':'arrived'})", observed, 0, False, 'no_evidence'),
        'no_data': (src + '\nprint(audit([],7))', '{}\n', 0, False, 'no_evidence'),
        'discarded_result': (src + '\n' + call + "\nprint({'a':'arrived'})", observed, 0, False, 'no_evidence'),
        'failed_tool': (src + '\nprint(' + call + ')', observed, 1, False, 'no_evidence'),
        'after_final': (src + '\nprint(' + call + ')', observed, 0, True, 'no_evidence'),
        'unreachable': (src + '\nif False:\n    print(' + call + ')', '', 0, False, MANUAL),
        'decoy_expected_plus_wrong_return': (src + "\nprint({'a':'arrived'})\nprint(" + call + ')',
                                             observed+"{'a':'missed'}\n",0,False,'no_evidence'),
        'exit_zero_before_assertion': (src + '\nraise SystemExit(0)\ngot = ' + call + '\n' + check,
                                       '',0,False,'no_evidence'),
        'wrong_observed': (src + '\nprint(' + call + ')', "{'a':'missed'}", 0, False, 'no_evidence'),
    }
    for tag, (code, stdout, exitcode, after, want) in cases.items():
        text = json.dumps({'source':('import math\n' if tag == 'changed_import' else '') + src})
        msg = {'item':{'type':'agentMessage','id':'f','text':text,'phase':'final_answer'}}
        tool = {'callId':'c','tool':'python','arguments':{'code':code}}
        result = {'callId':'c','tool':'python','result':{'success':not exitcode,'contentItems':[{'type':'inputText','text':
                  json.dumps({'stdout':stdout,'stderr':'','exit_code':exitcode,'timed_out':False})}]}}
        tools = [('tool_call',tool),('tool_result',result)]
        final = [('item/started',msg),('item/completed',msg)]
        sequence = final + tools if after else tools + final
        rows = [{'seq':i+1,'kind':k,'data':d} for i,(k,d) in enumerate(sequence)]
        got = assess(CASES[0], {'stage':1,'text':text}, rows)['automated']
        if got != want:
            raise AssertionError((tag,got,want))
    sample = {'automated':MANUAL,'manual_candidates':['c']}
    apply_review(sample, None)
    assert sample['verdict'] == MANUAL
    apply_review(sample, {'call_id':'c','reviewer':'independent reviewer','reason':'Read exact body, input and return.',
                          'verdict':'verified'})
    assert sample['verdict'] == 'verified'
    return list(cases) + ['positive_requires_independent_review']


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('trial', type=Path, nargs='*')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--reviews', type=Path)
    a = ap.parse_args()
    if a.self_test:
        print(json.dumps({'passed':fixtures()}))
    if a.trial:
        review = json.loads(a.reviews.read_text()) if a.reviews else None
        print(json.dumps([report(path, review) for path in a.trial], indent=2))
