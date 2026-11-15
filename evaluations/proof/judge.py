"""Blind pairwise judging of the writing tasks, positions swapped, plus a slot for human picks.

    judge.py --run RUN                         model judge from a different family than the solver
    judge.py --run RUN --human-export DIR      write a blinded packet for people to fill in
    judge.py --run RUN --human-import CSV      record their picks
"""
import argparse
import csv
import json
from pathlib import Path
import re
import secrets
import sys
import tempfile

import bench

RUBRIC = """Pick the answer that better does the job in the brief for its intended reader. Weigh, in this order:
1. Every factual statement is supported by the notes. An invented or wrong number, name, date or quotation is a serious fault.
2. It follows the brief's explicit instructions and limits.
3. It says what is not known instead of guessing.
4. It is clear, specific and plainly written.
Do not reward length. Do not guess which system wrote which answer."""
PROMPT = """You are judging two answers to the same writing brief. You do not know who wrote them.

## Brief
{brief}

## Notes the writers were given
{notes}

## How to judge
{rubric}

## Answer A
{a}

## Answer B
{b}

Reply with one JSON object and nothing else: {{"winner": "A" or "B" or "tie", "reason": "one sentence"}}
"""


def writing_pairs(run):
    """Yield (task, repeat, arm_x, arm_y, text_x, text_y) for each designed comparison present in the run."""
    meta = json.loads((run / 'run.json').read_text())
    design = json.loads((bench.HERE / 'pass_bar.json').read_text())['design']
    tasks = {t['id']: t for t in bench.load_tasks() if t['kind'] == 'write'}
    for x, y in design['pairs'] + [design['budget_control']]:
        if x not in meta['arms'] or y not in meta['arms']:
            continue
        for task_id in meta['tasks']:
            for repeat in meta['repeats']:
                if task_id in tasks:
                    texts = []
                    for arm in (x, y):
                        answer = bench.trial_dir(run, task_id, arm, repeat) / 'work' / tasks[task_id]['deliverable']
                        texts.append(answer.read_text(encoding='utf-8', errors='replace').strip()
                                     if answer.is_file() else '')
                    yield tasks[task_id], repeat, x, y, texts[0], texts[1]


def mock_pick(first, second):
    """Content decides, except one pair in five always says A, to exercise the position-swap check."""
    low, high = sorted([bench.sha(first.encode()), bench.sha(second.encode())])
    if int(bench.sha((low + high).encode()), 16) % 5 == 0:
        return 'A', 'mock position bias'
    return ('A' if bench.sha(first.encode()) == low else 'B'), 'mock content pick'


def model_pick(adapter, settings, model, prompt, timeout):
    with tempfile.TemporaryDirectory(prefix='judge-') as tmp:
        reply = bench.call_agent(adapter, settings, model, prompt, Path(tmp), Path(tmp) / 'judge.jsonl', timeout)
    found = re.findall(r'\{[^{}]*"winner"[^{}]*\}', reply.get('text') or '')
    try:
        answer = json.loads(found[-1])
        if answer.get('winner') in ('A', 'B', 'tie'):
            return answer['winner'], str(answer.get('reason', ''))[:300]
    except (IndexError, ValueError):
        pass
    return None, 'unreadable judge reply'


def judge(run, adapter, allow_same_family):
    config = bench.load_config()
    meta = json.loads((run / 'run.json').read_text())
    adapter = adapter or config['adapters'][meta['adapter']]['judge']
    settings = config['adapters'][adapter]
    family = 'mock-judge' if adapter == 'mock' else settings['family']
    independent = family != meta['family']
    if not independent and not allow_same_family:
        raise SystemExit(f"judge family {family} is the solver's family; choose another --adapter "
                         'or pass --allow-same-family and accept an inconclusive writing result')
    notes = '\n\n'.join(f'### {p.name}\n{p.read_text().strip()}' for p in bench.source_notes())
    pairs = []
    for task, repeat, x, y, text_x, text_y in writing_pairs(run):
        row = {'task': task['id'], 'repeat': repeat, 'arms': [x, y], 'orders': [], 'winner': None}
        if not text_x or not text_y:
            row['winner'] = x if text_x else y if text_y else None
            row['outcome'] = 'forfeit' if row['winner'] else 'void'
        elif text_x == text_y:
            row['outcome'] = 'tie'
        else:
            brief = (task['dir'] / 'prompt.md').read_text().strip()
            for first, second, a, b in ((x, y, text_x, text_y), (y, x, text_y, text_x)):
                if adapter == 'mock':
                    pick, reason = mock_pick(a, b)
                else:
                    pick, reason = model_pick(adapter, settings, settings['models']['strong'], PROMPT.format(
                        brief=brief, notes=notes, rubric=RUBRIC, a=a, b=b), config['limits']['trial_timeout_s'])
                row['orders'].append({'first': first, 'pick': pick, 'reason': reason,
                                      'prefers': {'A': first, 'B': second}.get(pick, pick)})
            prefers = {order['prefers'] for order in row['orders']}
            if None in prefers:
                row['outcome'] = 'void'
            elif prefers == {'tie'}:
                row['outcome'] = 'tie'
            elif len(prefers) == 1:
                row['outcome'], row['winner'] = 'decided', prefers.pop()
            else:
                row['outcome'] = 'split'  # the pick followed the position, or one order was a tie
        pairs.append(row)
        print(row['task'], f'r{repeat}', x, 'vs', y, '->', row['outcome'], row['winner'] or '', flush=True)
    (run / 'judgments.json').write_text(json.dumps({
        'judge': {'adapter': adapter, 'model': settings['models']['strong'], 'family': family,
                  'solver_family': meta['family'], 'independent': independent, 'rubric': RUBRIC},
        'pairs': pairs}, indent=2) + '\n')


def human_export(run, packet):
    """Write the answers under random labels 1 and 2. The key stays in the run directory, away from raters."""
    packet.mkdir(parents=True, exist_ok=True)
    pairs = [p for p in writing_pairs(run) if p[4] and p[5]]
    order = sorted(range(len(pairs)), key=lambda _: secrets.randbits(64))
    key, lines = {}, ['# Blind picks', '', 'For each pair, read the brief and pick the answer that does the job '
                      'better. Enter 1, 2 or tie in picks.csv with your name. ' + RUBRIC.replace('\n', ' '), '']
    for number, index in enumerate(order, 1):
        task, repeat, x, y, text_x, text_y = pairs[index]
        pair_id = f'p{number:03d}'
        flipped = secrets.randbits(1)
        key[pair_id] = {'task': task['id'], 'repeat': repeat, '1': y if flipped else x, '2': x if flipped else y}
        one, two = (text_y, text_x) if flipped else (text_x, text_y)
        lines += [f'## {pair_id}', '', '**Brief.** ' + (task['dir'] / 'prompt.md').read_text().strip(), '',
                  '### Answer 1', '', one, '', '### Answer 2', '', two, '']
    (packet / 'packet.md').write_text('\n'.join(lines))
    with (packet / 'picks.csv').open('w', newline='') as stream:
        csv.writer(stream).writerows([['pair_id', 'pick', 'rater']] + [[pair_id, '', ''] for pair_id in key])
    (run / 'human-key.json').write_text(json.dumps(key, indent=2) + '\n')
    print(f'{len(key)} pairs written to {packet}. Raters also need the notes in {bench.HERE / "sources"}.')


def human_import(run, picks):
    key = json.loads((run / 'human-key.json').read_text())
    rows = []
    with picks.open(newline='') as stream:
        for line in csv.DictReader(stream):
            pick, pair = line['pick'].strip().lower(), key.get(line['pair_id'].strip())
            if not pick:
                continue
            if pair is None or pick not in ('1', '2', 'tie') or not line['rater'].strip():
                raise SystemExit(f'bad row: {line}')
            rows.append({'pair_id': line['pair_id'].strip(), 'rater': line['rater'].strip(), 'task': pair['task'],
                         'repeat': pair['repeat'], 'arms': sorted([pair['1'], pair['2']]),
                         'winner': pair.get(pick)})
    (run / 'human.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(f'{len(rows)} human picks recorded from {len({r["rater"] for r in rows})} raters')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--run', type=Path, required=True, help='output directory of a finished run')
    parser.add_argument('--adapter', help='judge CLI; default is the other family named in arms.json')
    parser.add_argument('--allow-same-family', action='store_true')
    parser.add_argument('--human-export', type=Path, metavar='DIR')
    parser.add_argument('--human-import', type=Path, metavar='CSV')
    args = parser.parse_args()
    run = args.run.resolve()
    if args.human_export:
        human_export(run, args.human_export)
    elif args.human_import:
        human_import(run, args.human_import)
    else:
        judge(run, args.adapter, args.allow_same_family)


if __name__ == '__main__':
    sys.exit(main())
