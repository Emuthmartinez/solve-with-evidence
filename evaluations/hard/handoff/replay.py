"""Reproduce a post-hoc delivery replay. Never write to solver traces or historical grades."""
import argparse
import ast
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from transfer_consumer import MODULES, ROOT, ledger, printer, verify
from json_handoff import Reject, check, parse

SMALL = {family+'-'+case for family in ('roster','probe','linkage') for case in ('d1','d2','h1')} | {
    'ledger-d1','ledger-h1','closure-d1','closure-h1'}
LARGE = SMALL | {'ledger-h2','closure-h2'}
COMPLETE = LARGE | {'artifact-h3'}
GRIDS = {'baseline':COMPLETE, 'candidate':SMALL, 'release':SMALL, 'final':LARGE, 'published':COMPLETE}
ORIGINAL_IDS = {f'{case}-{arm}-r{n}' for arm,grid in GRIDS.items() for case in grid for n in (1,2)}
SHIPPED_TRANSFERS = {f'{case}-shipped-r{n}' for case in MODULES for n in (1,2)}
BAD = {
    ('artifact-h3-published-r1',1): 'exec-e76a4347-3b93-4f76-8a2c-0ad4fcdbe882',
    ('artifact-h3-published-r2',1): 'exec-0020c613-32de-447b-a10d-ffbc63fe83a5',
    ('ledger-h2-final-r2',1): 'exec-823e7470-5f7c-467a-8baa-c307454b3a52',
    ('artifact-h3-shipped-r1',1): 'exec-d3a4812a-a444-47c4-a1a1-82e43ea0f4b8',
    ('artifact-h3-shipped-r2',1): 'exec-2f78ea9f-118e-4b1f-b450-183e2bde5baf',
    ('artifact-h3-shipped-r2',2): 'exec-74d970fd-2712-4386-9ec5-cf6ca7f5a0f7',
    ('ledger-h2-final-r1',2): 'exec-ad63fd45-bcac-42a7-8b35-54f652f7ac10',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def untrusted_parse(raw):
    try:
        return parse(raw)
    except Reject:
        return {}


def capture(path):
    hashes = json.loads((path/'manifest.json').read_bytes())
    for name in ('summary.json','trace.jsonl'):
        require(sha((path/name).read_bytes()) == hashes[name], f'bad {path.name}/{name} digest')
    meta = json.loads((path/'summary.json').read_bytes())
    events = [json.loads(line) for line in (path/'trace.jsonl').read_bytes().splitlines()]
    require(meta['status'] == 'completed' and len(meta['turns']) == 2, 'incomplete transfer')
    out = []
    for stage, turn in enumerate(meta['turns'],1):
        rows = [r for r in events if r['stage'] == stage]
        finals = [r['data']['item'] for r in rows if r['kind'] == 'item/completed'
                  and r['data']['item']['type'] == 'agentMessage' and r['data']['item'].get('phase') in (None,'final_answer')]
        require(finals and finals[-1]['text'] == turn['text'] and turn['stage'] == stage and turn['status'] == 'completed',
                'summary does not match the stage final message')
        start = min(r['seq'] for r in rows if r['kind'] == 'item/started' and r['data']['item']['id'] == finals[-1]['id'])
        out.append((turn['text'].encode(), [r for r in rows if r['seq'] < start]))
    return out, hashes


def correction(trial, stage, raw, rows):
    """A deliberately *fixture-specific* producer reconstruction; never used by json_handoff."""
    call_id = BAD[trial,stage]
    calls = [r for r in rows if r['kind'] == 'tool_call' and r['data']['tool'] == 'python' and r['data']['callId'] == call_id]
    results = [r for r in rows if r['kind'] == 'tool_result' and r['data']['tool'] == 'python' and r['data']['callId'] == call_id]
    require(len(calls) == len(results) == 1 and calls[0]['seq'] < results[0]['seq'], 'need the original producer call/result')
    result = results[0]['data']['result']
    outcome = json.loads(result['contentItems'][0]['text'])
    require(result['success'] is True and outcome['exit_code'] == 0 and outcome['timed_out'] is False, 'failed producer test')
    code = calls[0]['data']['arguments']['code']
    provenance = {'call_id':call_id, 'call_seq':calls[0]['seq'], 'result_seq':results[0]['seq']}
    if trial.startswith('artifact'):
        obj = deepcopy(parse(raw))
        tested = parse(outcome['stdout'].splitlines()[0].encode())
        if trial == 'artifact-h3-shipped-r2':
            require(obj['result'] == tested['result'] and obj['edge'] == tested['edge']
                    and obj['source'] != tested['source'], 'different producer artifact')
            obj['source'] = tested['source']
            provenance['operation'] = 'Restore exact source from the successful producer-serialized payload.'
        else:
            require(tested == obj, 'unmatched serialized producer test')
        if stage == 1:
            obj['edge']['job'] = {'rows':obj['edge']['job']}
            provenance['operation'] = (provenance.get('operation','') +
                ' Wrap only the same producer-tested rows under the required job.rows name.').strip()
    elif stage == 1:
        # The tool body actually exercised this function. A one-character insertion into this
        # specific received message must reproduce that source verbatim; no JSON guessing in the gate.
        source = ast.get_source_segment(code, ast.parse(code).body[0])
        old = raw.decode()
        try:
            json.loads(old)
        except json.JSONDecodeError as e:
            require(old[e.pos:e.pos+2] == chr(92)+' ', 'different damaged escape')
            fixed = old[:e.pos+1] + 'n' + old[e.pos+1:]
        else:
            raise ValueError('expected invalid serialization')
        obj = parse(fixed.encode())
        returned = ast.literal_eval(outcome['stdout'])
        require(obj['source'] == source and obj['result'] == returned['result'] and obj['edge']['expected'] == returned['edge_expected'],
                'repair does not recover original tested source/results')
        provenance['operation'] = 'Restore one missing n in the JSON newline escape; source matches the successful original tool call, other bytes unchanged.'
        return fixed.encode(), provenance
    else:
        obj = deepcopy(parse(raw))
        # Pick a producer-tested input/result, not an oracle-generated case or expected value.
        tree = ast.parse(code)
        source = ast.get_source_segment(code, tree.body[0])
        require(source == obj['source'] and isinstance(tree.body[1], ast.Assign)
                and ast.unparse(tree.body[1].targets[0]) == 'charges', 'unexpected producer source or input binding')
        charges = ast.literal_eval(tree.body[1].value)
        output = ast.literal_eval(outcome['stdout'].splitlines()[0])
        observed_call = tree.body[-2].value
        require(isinstance(observed_call,ast.Call) and ast.unparse(observed_call.func) == 'print'
                and ast.unparse(observed_call.args[0]) == 'settle(charges, 11)' and obj['result'] == output,
                'expected producer result from known input')
        obj['edge'] = {'charges':charges,'slots':observed_call.args[0].args[1].value,'expected':output}
        provenance['operation'] = 'Replace the false witness with the five-identifier supplied input and return value executed by the original producer in the same stage.'
    return json.dumps(obj, ensure_ascii=False, separators=(',',':')).encode(), provenance


def replay(ids):
    ledger_rows = []
    totals = {'historical_scored_trials':0,'historical_full_passes':0,'replayed_transfers':0,
              'unchanged_answers_accepted':0,'original_answers_rejected':0,'reconstructions_accepted':0}
    repairs = set()
    for p in sorted((ROOT/'trials').glob('*/grade.json')):
        record = json.loads(p.read_bytes())
        if p.parent.name not in ids:
            continue
        if not record.get('score'):
            continue
        case, score = record['case'], record['score']
        totals['historical_scored_trials'] += 1
        totals['historical_full_passes'] += int(score['pass'])
        if case not in MODULES:
            require(score['pass'], 'an unexpected historical failure outside these transfers')
            continue
        totals['replayed_transfers'] += 1
        trial = p.parent.name
        captures, hashes = capture(p.parent)
        original = [untrusted_parse(raw) for raw, _ in captures]
        require(MODULES[case].grade(case, original) == score, 'frozen grade differs on replay')
        after = list(original)
        stages = []
        for stage,(raw, events) in enumerate(captures,1):
            consumer = lambda data: verify(case,stage,data)
            row = {'stage':stage,'received_sha256':sha(raw)}
            try:
                require(check(raw,consumer) == raw, 'bytes changed')
            except Reject as e:
                require((trial,stage) in BAD, f'unexpected rejection on {trial}/{stage}: {e}')
                row.update(received='rejected',reason=str(e))
                totals['original_answers_rejected'] += 1
                replacement, source = correction(trial,stage,raw,events)
                delivered = check(replacement,consumer)
                require(delivered == replacement, 'replacement bytes changed')
                after[stage-1] = parse(delivered)
                row.update(replacement='accepted', replacement_sha256=sha(delivered), provenance=source)
                if case == ledger.CASE:
                    choices = [('replacement',after[stage-1])]
                    if original[stage-1]:
                        choices.insert(0,('received',original[stage-1]))
                    for label, choice in choices:
                        edge = choice['edge']
                        args = edge['charges'],edge['slots']
                        row[label+'_witness'] = {'input':{'charges':args[0],'slots':args[1]},'correct':ledger.canonical(*args),
                                                 'faulty':ledger.canonical(*args,'clip_once' if stage == 2 else 'insertion')}
                repairs.add((trial,stage))
                totals['reconstructions_accepted'] += 1
            else:
                require((trial,stage) not in BAD, 'missed known bad answer')
                row['received'] = 'accepted_unchanged'
                totals['unchanged_answers_accepted'] += 1
            stages.append(row)
        result = MODULES[case].grade(case,after)
        require(result['pass'], 'reconstructed pair does not pass functional grader')
        brief = lambda g: {k:g[k] for k in ('pass','points','max_points','critical_failures')}
        ledger_rows.append({'trial':trial,'trace_sha256':hashes['trace.jsonl'],'stages':stages,'historical_grade':brief(score),
                            'after_replay_grade':brief(result)})
    require(repairs == {k for k in BAD if k[0] in ids} and totals['historical_scored_trials'] == len(ids), 'missing trial or stages')
    return {'totals':totals,'trials':ledger_rows}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, help='write reproducible report (no original files are changed)')
    a = p.parse_args()
    report = {'kind':'targeted post-hoc harness replay; no solver reruns',
              'original_five_arms':replay(ORIGINAL_IDS), 'shipped_two_transfer_cases':replay(SHIPPED_TRANSFERS)}
    if a.out:
        a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v['totals'] for k,v in report.items() if isinstance(v,dict)}))
