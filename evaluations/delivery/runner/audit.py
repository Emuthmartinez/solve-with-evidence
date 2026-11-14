"""Replay the recipient and bind its material to the recorded model inputs, tool events and final message."""
import argparse
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from recipient import inspect
from run import load_core


CORE_DIR = Path(__file__).resolve().parents[2] / "hard" / "runner"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(file):
    return json.loads(file.read_bytes())


def check_chronology(entries, prompt, turn, cap):
    kinds = [e['kind'] for e in entries]
    need(kinds[:4] == ['thread/request', 'thread/settings', 'user_input', 'turn/started']
         and kinds[-3:] == ['turn/completed', 'recipient', 'runner_end'], 'trial boundaries')
    need([e['stage'] for e in entries] == [0, 0] + [1] * (len(entries)-2), 'wrong stage')
    need(entries[3]['data']['id'] == entries[-3]['data']['id'], 'turn identity')
    started, finished, calls, results, echoes = {}, set(), {}, {}, set()
    user = final = usage = None
    for row in entries[4:-3]:
        kind, data = row['kind'], row['data']
        if kind == 'usage':
            usage = data
            continue
        if kind in ('item/started', 'item/completed'):
            item = data['item']
            item_id, typ = item['id'], item['type']
            need(typ in ('userMessage','agentMessage','dynamicToolCall'), 'unexpected provider item')
            if kind == 'item/started':
                need(item_id not in started and final is None, 'unexpected or late item start')
                started[item_id] = item
            else:
                need(item_id in started and item_id not in finished and typ == started[item_id]['type'],
                     'unpaired provider item')
                finished.add(item_id)
            if typ == 'userMessage':
                content = item['content']
                need(len(content) == 1 and content[0]['type'] == 'text' and content[0]['text'] == prompt,
                     'provider user prompt differs')
                need(user is None, 'duplicate provider user')
                if kind == 'item/completed':
                    user = item_id
            else:
                need(user in finished, 'provider user must precede model output')
            if typ == 'dynamicToolCall' and kind == 'item/completed':
                need(item_id in results, 'provider tool echo before host result')
                call, result = calls[item_id], results[item_id]
                need(all(item[k] == call[k] for k in ('tool','namespace','arguments'))
                     and all(item[k] == result[k] for k in ('success','contentItems')), 'provider tool echo differs')
                echoes.add(item_id)
            if typ == 'agentMessage' and item.get('phase') in (None, 'final_answer'):
                if kind == 'item/started':
                    need(set(calls) == echoes and set(started) - finished == {item_id},
                         'final started before earlier items or checks completed')
                    final = item_id
                else:
                    need(item_id == final, 'final start/completion mismatch')
            continue
        need(user in finished and final is None, 'tool event outside producer window')
        if kind == 'tool_call':
            cid = data['callId']
            need(cid not in calls and cid in started and started[cid]['type'] == 'dynamicToolCall'
                 and all(started[cid][k] == data[k] for k in ('tool','namespace','arguments')),
                 'host call differs from provider start')
            need(data['tool'] in ('python','read_reference','deliver_json'), 'unknown tool')
            calls[cid] = data
        elif kind == 'tool_result':
            cid = data['callId']
            need(cid in calls and cid not in results and calls[cid]['tool'] == data['tool'], 'unpaired tool result')
            result = data['result']
            need(type(result['success']) is bool and len(result['contentItems']) == 1
                 and result['contentItems'][0]['type'] == 'inputText', 'invalid tool result')
            if list(calls).index(cid) >= cap:
                need(not result['success'] and result['contentItems'][0]['text'] == 'Trial tool call cap reached.',
                     'tool cap not enforced')
            results[cid] = result
        elif kind == 'delivery':
            cid = data['delivery_call_id']
            need(cid in calls and cid not in results and calls[cid]['tool'] == 'deliver_json',
                 'checker outside a delivery call')
        else:
            raise ValueError('unexpected event in completed turn: ' + kind)
    need(user in finished and final in finished and set(started) == finished, 'missing provider echo or final')
    need(set(calls) == set(results) == echoes == {k for k,v in started.items() if v['type'] == 'dynamicToolCall'},
         'provider tool cardinality')
    need(usage is not None and usage == turn['usage'], 'provider usage differs')


def audit(folder, casefile, consumer, gate, skill):
    summary=load(folder/'summary.json')
    manifest=load(folder/'manifest.json')
    inventory={f.relative_to(folder).as_posix():sha(f.read_bytes()) for f in folder.rglob('*')
               if f.is_file() and f != folder/'manifest.json'}
    need(inventory==manifest,'manifest/inventory differs')
    for name,path in [('gate_sha256',gate),('consumer_sha256',consumer),('recipient_sha256',Path(__file__).with_name('recipient.py')),
                      ('delivery_runner_sha256',Path(__file__).with_name('run.py'))]:
        need(summary[name]==sha(path.read_bytes()),name)
    core = load_core(CORE_DIR)
    need(summary['runner_sha256'] == {f: sha((CORE_DIR / f).read_bytes())
                                      for f in ('run_trial.py', 'calculate.py')}, 'core runner hashes')
    need(summary['runtime']['cli_options'] == core.OPTIONS and summary['runtime']['platform'] == 'Darwin',
         'runtime configuration')
    need((summary['requested_model'], summary['effort'], summary['turn_timeout_s'], summary['tool_cap_per_turn'],
          summary['calculator_timeout_s'], summary['calculator_output_cap_bytes_per_stream'])
         == ('gpt-6.1-sol', 'medium', 200, 24, 6, 65536), 'wrong model, effort or resource limits')
    original=load(casefile)
    need(summary['case_messages_sha256'] == sha(json.dumps(original['messages'], ensure_ascii=False).encode()),
         'case digest')
    need(summary['case_id']==original['id'],'case identity')
    entries=[json.loads(line) for line in (folder/'trace.jsonl').read_text().splitlines()]
    need([x['seq'] for x in entries]==list(range(1,len(entries)+1)),'event sequence')
    need([x['elapsed_s'] for x in entries]==sorted(x['elapsed_s'] for x in entries),'event order')
    need(entries[-1]['kind']=='runner_end' and entries[-1]['data']['status']==summary['status'],'end record')
    def events(name):return [x['data'] for x in entries if x['kind']==name]
    if summary['status']!='completed':
        need(len(events('runner_error'))==1,'missing runtime error')
        return {'status':summary['status'],'error':summary.get('error')}
    req,=events('thread/request')
    settings,=events('thread/settings')
    need(settings == summary['settings'] and settings['model'] == req['model'] == summary['model']
         == summary['requested_model'] and settings['reasoningEffort'] == summary['effort'], 'resolved settings')
    need(settings['modelProvider'] == summary['provider'] == 'openai' and summary['auth'] == 'chatgpt',
         'provider/auth')
    need(settings['instructionSources'] == [] and settings['approvalPolicy'] == 'never'
         and settings['cwd'] == '/', 'host sources')
    fixed = dict(cwd='/', ephemeral=True, sandbox='read-only', environments=[], selectedCapabilityRoots=[],
                 approvalPolicy='never', baseInstructions=core.BASE, dynamicTools=core.TOOLS,
                 allowProviderModelFallback=False)
    need(all(req[k] == v for k, v in fixed.items()), 'thread inputs or capabilities')
    need(len(summary['turns']) == len(original['messages']) == 1 and summary['turns'][0]['stage']==1
         and summary['turns'][0]['status']=='completed','stage')
    need([v['text'] for v in events('user_input')]==original['messages'],'case input')
    check_chronology(entries, original['messages'][0], summary['turns'][0], summary['tool_cap_per_turn'])
    filelist={'SKILL.md':(skill/'SKILL.md').read_bytes(), **{f.relative_to(skill).as_posix():f.read_bytes()
              for f in sorted((skill/'references').rglob('*.md'))}}
    need({n:sha(b) for n,b in filelist.items()}==summary['skill_files_sha256'],'skill')
    expected=filelist['SKILL.md'].decode()+'\n\nAvailable skill reference paths:\n'+'\n'.join(list(filelist)[1:])
    need(req['developerInstructions']==expected,'instructions')
    outputs={}; pending={}; calls={}; deliveries=[]; finals=[]; closed=False
    for e in entries:
        k,d=e['kind'],e['data']
        if k in ('tool_call','tool_result','delivery'):
            need(not finals and not closed,'event occurred after final message')
        if k=='tool_call':
            cid=d['callId']; need(cid not in calls,'duplicate call');calls[cid]=d;pending[cid]=d
        if k=='delivery':
            cid=d['delivery_call_id']
            need(cid in pending and pending[cid]['tool']=='deliver_json','delivery outside a call')
            previous=pending[cid]['arguments']['source']
            source=next(reversed(outputs),None) if previous=='last' else previous
            need(d['producer_call_id']==source,'receipt selects wrong producer')
            if d['status']=='accepted':
                need(source in outputs,'missing successful producer')
                payload=outputs[source]
                identity=sha(payload)
                need(d['receipt']=={'path':f'artifacts/{identity}.json','sha256':identity,'bytes':len(payload)}
                     and d['producer_sha256']==identity and d['producer_bytes']==len(payload),'checker bytes')
                need(d['exit'] == 0 and d['link'] == f"[Download verified JSON]({d['receipt']['path']})",
                     'consumer receipt')
                replayed = subprocess.run([sys.executable, '-B', str(consumer.resolve()), original['id']],
                                          input=payload, capture_output=True, timeout=30)
                need(replayed.returncode == 0, 'consumer rejects captured accepted producer bytes')
                need((folder/d['receipt']['path']).read_bytes()==payload,'producer file differs')
            deliveries.append(d)
        if k=='tool_result':
            cid=d['callId'];call=pending.pop(cid);r=d['result']
            need(call['tool']==d['tool'],'tool names disagree')
            value=r['contentItems'][0]['text']
            if r['success'] and d['tool']=='python':
                v=json.loads(value);raw=base64.b64decode(v['stdout_base64']) if 'stdout_base64' in v else v['stdout'].encode()
                need(sha(raw)==v['stdout_sha256'] and len(raw)==v['stdout_bytes'] and v['exit_code']==0,'python stdout')
                outputs[cid]=raw
            if r['success'] and d['tool']=='read_reference':
                need(filelist[call['arguments']['path']]==value.encode(),'reference')
            if d['tool']=='deliver_json' and value!='Trial tool call cap reached.':
                rec=json.loads(value)
                need(rec==deliveries[-1] and rec['delivery_call_id']==cid and r['success']==(rec['status']=='accepted'),
                     'tool reply differs from checker receipt')
        if k=='item/completed':
            item=d['item']
            if item['type']=='agentMessage' and item.get('phase') in (None,'final_answer'):
                finals.append(item['text'])
        if k=='turn/completed':
            need(not closed and bool(finals) and d['status']=='completed','turn end');closed=True
    need(not pending and closed and len(finals)==1 and summary['turns'][0]['text']==finals[0],'final cardinality')
    need(len(calls)==summary['tool_calls']==summary['turns'][0]['tool_calls'],'call total')
    need(deliveries==load(folder/'attempts.json'),'delivery ledger')
    need(finals[0].encode()==(folder/'response.md').read_bytes(),'wire message changed')
    replay,raw=inspect(original['id'],folder/'response.md',consumer,deliveries)
    need(replay==load(folder/'recipient.json')==summary['recipient']==events('recipient')[0],'recipient read differs')
    need(raw==(folder/'received.bin').read_bytes() if raw is not None else not (folder/'received.bin').exists(),
         'retained receiver payload differs')
    return {'trial':folder.name,'status':'completed','case':summary['case_id'],'arm':summary['arm'],
            'repeat':summary['repeat'],'channel':replay['channel'],'raw_correct':replay['consumer_accepted'],
            'checked_bytes_delivered':replay['checked_before_delivery'] and replay['consumer_accepted'],
            'verified_link_delivery':replay['verified_link_delivery'], 'attempts':len(deliveries),
            'gate_rejections':sum(d['status']=='rejected' for d in deliveries),
            'elapsed_s':summary['elapsed_s'],'provider_tokens':summary['turns'][0]['usage']['total']['totalTokens']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['trials','cases','repo','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--candidate', type=Path, help='frozen candidate package; also provides the shared checker')
    a=p.parse_args()
    candidate = a.candidate or a.repo/'evaluations/delivery/snapshots/candidate'
    case_names = {f.stem for f in (a.cases/'inputs').glob('*.json')}
    freeze = load(a.cases/'freeze.json')['files']
    need(case_names and case_names == {Path(f).stem for f in freeze if f.startswith('inputs/')}, 'frozen case list')
    for name, expected in freeze.items():
        need(sha((a.cases/name).read_bytes()) == expected, 'frozen case differs: ' + name)
    results=[]; observed=set(); threads=set()
    for f in sorted(a.trials.iterdir()):
        if not f.is_dir() or f.name.startswith('.'): continue
        summary=load(f/'summary.json')
        arm,case,repeat=(summary[k] for k in ('arm','case_id','repeat'))
        need(arm in ('baseline', 'candidate') and case in case_names and type(repeat) is int and repeat in (1,2),
             'trial outside expected matrix')
        need(f.name == f'{case}-{arm}-r{repeat}', 'trial directory identity differs')
        key=(arm,case,repeat); need(key not in observed,'duplicate trial')
        observed.add(key)
        if summary['status']=='completed':
            need(summary['thread_id'] not in threads,'reused thread'); threads.add(summary['thread_id'])
        skill = candidate if arm == 'candidate' else a.repo/'evaluations/hard/snapshots/shipped'
        result=audit(f,a.cases/'inputs'/f'{case}.json',a.cases.resolve()/'consumer.py',
                     candidate/'scripts/json_handoff.py',skill)
        results.append(result)
    need(observed=={(arm,case,rep) for arm in ('baseline','candidate') for case in case_names
                    for rep in (1,2)},'incomplete or unexpected matrix')
    a.out.write_text(json.dumps(results,indent=2)+'\n')
    print('Audited',len(results),'trials; distinct completed threads:',len(threads))


if __name__=='__main__':
    main()
