"""Verify an exported trial's public event lineage and captured file hashes."""
import argparse
import hashlib
import json
from pathlib import Path


class IntegrityError(ValueError):
    pass


def need(test, message):
    if not test:
        raise IntegrityError(message)


def verify(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    need(set(manifest) == {'trace.jsonl', 'summary.json'}, 'unexpected manifest members')
    for name, expected in manifest.items():
        actual = hashlib.sha256((folder / name).read_bytes()).hexdigest()
        need(actual == expected, 'hash mismatch: ' + name)
    rows = [json.loads(line) for line in (folder / 'trace.jsonl').read_text().splitlines()]
    summary = json.loads((folder / 'summary.json').read_text())
    need(rows and rows[-1]['kind'] == 'runner_end', 'missing end record')
    need(rows[-1]['data']['status'] == summary['status'], 'terminal outcome mismatch')
    need([r['seq'] for r in rows] == list(range(1, len(rows) + 1)), 'broken event sequence')
    need(all(a['elapsed_s'] <= b['elapsed_s'] for a, b in zip(rows, rows[1:])), 'time reversed')

    request = [r['data'] for r in rows if r['kind'] == 'thread/request']
    settings = [r['data'] for r in rows if r['kind'] == 'thread/settings']
    if summary['status'] == 'completed' or settings:
        need(len(request) == len(settings) == 1, 'missing thread setup')
        need(request[0]['environments'] == [] and request[0]['ephemeral'], 'not isolated')
        need(settings[0]['instructionSources'] == [] and settings[0]['cwd'] == '/', 'host context loaded')
        need(settings[0] == summary['settings'] and settings[0]['model'] == summary['model'],
             'model settings mismatch')
        need(summary['auth'] == 'chatgpt', 'unexpected auth mode')
    count = 0
    seen_ids = set()
    messages = []
    for index, turn in enumerate(summary['turns'], 1):
        need(turn['stage'] == index, 'stage order mismatch')
        stage = [r for r in rows if r['stage'] == index]
        prompts = [r['data']['text'] for r in stage if r['kind'] == 'user_input']
        need(len(prompts) == 1, 'missing or repeated stage input')
        messages.extend(prompts)
        pending = {}
        exact_final = ''
        usage = None
        for row in stage:
            kind, data = row['kind'], row['data']
            if kind == 'tool_call':
                call_id = data['callId']
                need(call_id not in seen_ids, 'repeated callId')
                seen_ids.add(call_id)
                pending[call_id] = data['tool']
                count += 1
            elif kind == 'tool_result':
                need(pending.pop(data['callId'], None) == data['tool'], 'orphan or repeated result')
                need(isinstance(data['result'].get('success'), bool), 'missing tool outcome')
            elif kind in ('item/started', 'item/completed'):
                item = data['item']
                need(item['type'] != 'reasoning', 'private reasoning item present')
                if kind == 'item/completed' and item['type'] == 'agentMessage' and item.get('phase') in (None, 'final_answer'):
                    exact_final = item['text']
            elif kind == 'usage':
                usage = data
        need(turn['text'] == exact_final, 'final message mismatch')
        need(turn['usage'] == usage, 'usage mismatch')
        need(turn['tool_calls'] == sum(r['kind'] == 'tool_call' for r in stage), 'stage call count mismatch')
        if turn['status'] == 'completed':
            need(not pending, 'completed turn has unfinished tool call')
            need(exact_final and any(r['kind'] == 'turn/completed' for r in stage), 'missing final message or outcome')
    need(count == summary['tool_calls'], 'total call count mismatch')
    if summary['status'] == 'completed':
        need(messages and all(t['status'] == 'completed' for t in summary['turns']), 'missing stage completion')
        digest = hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode()).hexdigest()
        need(digest == summary['case_messages_sha256'], 'task input mismatch')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trial', nargs='+', type=Path)
    for path in parser.parse_args().trial:
        passed = verify(path)
        print(f"{path.name} {passed['status']} {passed['tool_calls']} tool calls")
