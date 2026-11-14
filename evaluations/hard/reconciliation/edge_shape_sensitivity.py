"""Post-hoc sensitivity to the one-argument stage-one edge.job representation.

Use original final answer strings. Run the frozen outcome grader once on
their original decoded objects and once on a copy that wraps a direct, valid
stage-one rows argument as {"rows": rows}. Stage two is never normalized.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import artifact_transfer

CASE = artifact_transfer.CASE
ARMS = ('baseline', 'published')
REPEATS = (1, 2)


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def decode(raw):
    # Match the preregistered dispatcher's sole concession to presentation.
    text = raw.strip()
    if text.startswith('```') and text.endswith('```') and '\n' in text:
        text = text.split('\n', 1)[1][:-3].strip()
    try:
        value = json.loads(text)
    except ValueError:
        return {}, False
    return (value, True) if isinstance(value, dict) else ({}, False)


def normalize(original):
    answer = deepcopy(original)
    edge = answer.get('edge')
    if not isinstance(edge, dict):
        return answer, False
    rows = edge.get('job')
    if (not isinstance(rows, list) or len(rows) > 2 or
        any(not isinstance(row, list) or not 1 <= len(row) <= 128 or
            any(not isinstance(field, str) or len(field) > 4096 for field in row) for row in rows)):
        return answer, False
    edge['job'] = {'rows': rows}
    return answer, True


def reduced(score):
    return {key: score[key] for key in ('points', 'max_points', 'pass', 'critical_failures')}


def assess(path):
    summary_text = (path/'summary.json').read_text()
    trace_text = (path/'trace.jsonl').read_text()
    hashes = json.loads((path/'manifest.json').read_text())
    if hashes['summary.json'] != digest(summary_text) or hashes['trace.jsonl'] != digest(trace_text):
        raise ValueError('captured trial checksum mismatch')
    summary = json.loads(summary_text)
    if summary['case_id'] != CASE or summary['status'] != 'completed' or len(summary['turns']) != 2:
        raise ValueError('need two completed artifact-h3 stages')
    events = [json.loads(line) for line in trace_text.splitlines()]
    raw = []
    for stage, turn in enumerate(summary['turns'], 1):
        final = [e['data']['item']['text'] for e in events if e['stage'] == stage and
                 e['kind'] == 'item/completed' and e['data']['item']['type'] == 'agentMessage' and
                 e['data']['item'].get('phase') in (None, 'final_answer')]
        if not final or final[-1] != turn['text'] or turn['stage'] != stage or turn['status'] != 'completed':
            raise ValueError('summary is not the recorded final answer')
        raw.append(final[-1])
    decoded = [decode(value) for value in raw]
    originals = [value for value, ok in decoded]
    strict = artifact_transfer.grade(CASE, originals)
    recorded = json.loads((path/'grade.json').read_text())['score']
    if strict != recorded:
        raise ValueError('strict replay does not match frozen recorded outcome: ' + path.name)
    stage_one, changed = normalize(originals[0])
    alternative = artifact_transfer.grade(CASE, [stage_one, originals[1]])
    changed_checks = [k for k in strict['checks'] if strict['checks'][k] != alternative['checks'][k]]
    if set(changed_checks) - {'stage1_counterexample'}:
        raise ValueError('alternate interpretation affected a different endpoint')
    return {
        'trial':path.name, 'trace_sha256':hashes['trace.jsonl'],
        'final_answer_sha256':[digest(t) for t in raw],
        'final_parsed_as_object':[ok for value, ok in decoded],
        'stage1_job_wrapped':changed, 'strict_replay_matches_original_grade':True,
        'strict':reduced(strict), 'alternate_interpretation':reduced(alternative),
        'changed_checks':changed_checks,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('trials',type=Path)
    p.add_argument('--out',type=Path)
    args = p.parse_args()
    rows = [assess(args.trials/f'{CASE}-{arm}-r{repeat}') for arm in ARMS for repeat in REPEATS]
    totals = {}
    for arm in ARMS:
        selected = [r for r in rows if f'-{arm}-' in r['trial']]
        totals[arm] = {metric:{'passes':sum(r[metric]['pass'] for r in selected),
                               'trials':len(selected),'points':sum(r[metric]['points'] for r in selected),
                               'maximum':sum(r[metric]['max_points'] for r in selected)}
                       for metric in ('strict','alternate_interpretation')}
    result = {'case':CASE, 'analysis':'Post-hoc alternate interpretation of one-argument edge.job',
              'independent_outcome':False,
              'normalization':'Wrap a valid direct stage-1 rows argument in a rows object. All other fields, '
                              'invalid answers, and stage 2 remain as delivered.',
              'frozen_grader_sha256':hashlib.sha256(Path(artifact_transfer.__file__).read_bytes()).hexdigest(),
              'trials':rows,'totals':totals}
    if args.out:
        temp = args.out.with_suffix('.tmp')
        temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        temp.replace(args.out)
    print(json.dumps(totals, ensure_ascii=False))


if __name__ == '__main__':
    main()
