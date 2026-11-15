"""Independently open archived final links, regrade bytes and corroborate pre-delivery checker receipts."""
import argparse
import ast
from contextlib import ExitStack
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
import datetime as dt
import hashlib
import os
import stat
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys


class Invalid(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise Invalid(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def filemap(root):
    result = {}
    for p in root.rglob('*'):
        need(not p.is_symlink(), 'archive contains a symbolic link')
        if p.is_file() and p != root / 'manifest.json':
            need(stat.S_ISREG(p.lstat().st_mode) and p.lstat().st_nlink==1, 'archive contains an aliased file')
            result[p.relative_to(root).as_posix()] = digest(p.read_bytes())
    return result


def millis(row):
    return round(dt.datetime.fromisoformat(row['at']).timestamp()*1000)


LINK = re.compile(r'\[[^\]\n]+\]\((?:<([^>\n]+)>|([^()\s]+))\)')
CASES = ('night-window','octet-frame','packet-map')


def rendered_link(message):
    """Inspect the rendered HTML structure using an independent receiver implementation."""
    import markdown_it
    need(markdown_it.__version__=='4.0.0', 'the recorded renderer requires markdown-it-py 4.0.0')
    class Link(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.events=[]
        def handle_starttag(self,tag,attrs):
            self.events.append(('open',tag,dict(attrs)))
        def handle_endtag(self,tag):
            self.events.append(('close',tag,{}))
        def handle_data(self,data):
            if data.strip():
                self.events.append(('text',data,{}))
        def handle_comment(self,data):
            self.events.append(('comment',data,{}))
    document=Link()
    # Neutralize raw HTML so that a purported JSON response is not allowed to
    # manufacture an anchor tag directly. The measured interface is Markdown.
    document.feed(markdown_it.MarkdownIt('commonmark',{'html':False}).render(message))
    xs=document.events
    if len(xs)<4 or [(k,t) for k,t,_ in (xs[0],xs[1],xs[-2],xs[-1])] != [('open','p'),('open','a'),('close','a'),('close','p')]:
        return None
    if any(tag in ('a','p') and kind in ('open','close') for kind,tag,_ in xs[2:-2]):
        return None
    return xs[1][2].get('href')


def locate(message, workspace, parser=None):
    text=message.decode('utf-8').strip()
    if parser is None:
        link=LINK.fullmatch(text)
        href = (link[1] or link[2]) if link else None
    else:
        need(parser=='markdown-it-py/4.0.0 commonmark', 'unknown recipient link parser')
        href=rendered_link(text)
    if href is None:
        return 'inline', None
    if parser is not None:
        parsed=urlsplit(href)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            return 'broken_link', None
        href=unquote(parsed.path,errors='strict')
    path=PurePosixPath(href)
    if path.is_absolute() and path.is_relative_to(workspace):
        path = path.relative_to(workspace)
    if path.is_absolute() or '..' in path.parts or path.parts[:1] != ('outputs',) or len(path.parts)<2:
        return 'broken_link', None
    return 'file', path.as_posix()


def open_artifact(trial, rel):
    parts=PurePosixPath(rel).parts
    need(parts[0]=='outputs' and '..' not in parts,'path outside output directory')
    with ExitStack() as stack:
        fd=os.open(trial,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        stack.callback(os.close,fd)
        for entry in parts[:-1]:
            fd=os.open(entry,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            stack.callback(os.close,fd)
        fp=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
        with os.fdopen(fp,'rb') as f:
            st=os.fstat(fp)
            need(stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<=131073,
                 'invalid archived recipient file')
            data=f.read(131074)
            need(len(data)==st.st_size,'artifact changed while read')
            return data


def replay_consumer(consumer, case, payload):
    p = subprocess.run([sys.executable,'-I','-B',str(consumer),case],input=payload,capture_output=True,timeout=30)
    need(p.returncode in (0,1), 'regrading consumer unavailable: '+str(p.returncode))
    return p.returncode, p.stderr.decode()


def checker_command(command):
    """Recognize a reference to the actual checker in an executing line of this native corpus."""
    try:
        words=shlex.split(command)
    except ValueError:
        return False
    if len(words)!=3 or Path(words[0]).name not in ('zsh','bash','sh') or 'c' not in words[1]:
        return False
    for line in words[2].splitlines():
        line=line.strip()
        if re.search(r'(?:^|(?:&&|[;|])\s*)\./case-check(?=\s|$|<)', line):
            return True
        # A solver may call the trusted CLI from a Python subprocess in a heredoc.
        if 'subprocess.run(' in line:
            try:
                nodes=ast.walk(ast.parse(line))
                for node in nodes:
                    if isinstance(node,ast.Call) and ast.unparse(node.func)=='subprocess.run' and node.args:
                        argv=node.args[0]
                        if isinstance(argv,(ast.List,ast.Tuple)) and argv.elts and isinstance(argv.elts[0],ast.Constant) and argv.elts[0].value=='./case-check':
                            return True
            except SyntaxError:
                pass
        if re.match(r'(?:python(?:3(?:\.\d+)?)?|[^ ]*/python3)\s+.*json_handoff\.py\s+',line) and re.search(r'--\s+\./case-check(?=\s|$)',line):
            return True
    return False


def audit(trial, evaluation, candidate=None):
    req, score = (read(trial/name) for name in ('request.json','result.json'))
    need(type(req.get('unavailable')) is bool,'missing consumer scenario')
    inventory = filemap(trial)
    need(read(trial/'manifest.json')==inventory, 'file manifest differs')
    case,arm,rep = (req[k] for k in ('case','arm','repeat'))
    need(case in CASES and arm in ('baseline','candidate') and rep in (1,2), 'unexpected comparison cell')
    need(trial.name==f'{case}-{arm}-r{rep}' and all(req[k]==score[k] for k in ('case','arm','repeat')), 'trial identity mismatch')
    suite=evaluation / ('transfer' if case=='packet-map' else 'cases')
    consumer=suite/'consumer.py'
    need(digest(consumer.read_bytes())==req['consumer_sha256'], 'consumer digest differs')
    original=read(suite/'inputs'/f'{case}.json')['messages']
    need(len(original)==1 and req['message'].endswith(original[0]), 'input differs from frozen task')
    # Candidate trials recorded the frozen package, not whatever solve-with-evidence/ says now.
    root=evaluation.parents[1]
    pkg=(candidate or root/'evaluations/delivery/measured-package') if arm=='candidate' else root/'evaluations/hard/snapshots/shipped'
    actual_files={p.relative_to(pkg).as_posix():digest(p.read_bytes()) for p in pkg.rglob('*') if p.is_file()}
    need(actual_files==req['skill_sha256'], 'supplied package differs from selected version')
    workspace=PurePosixPath(req['workspace'])
    cmd=req['command']
    need(re.fullmatch(r'/private/tmp/swe-native-[a-zA-Z0-9_-]+/workspace',str(workspace)) and
         cmd[cmd.index('-C')+1]==str(workspace) and cmd[cmd.index('-m')+1]=='gpt-6.1-sol' and
         'model_reasoning_effort="medium"' in cmd and '--json' in cmd and '--ephemeral' in cmd and
         cmd[cmd.index('-o')+1]==str(workspace.parent/'last-message'), 'unexpected CLI settings')
    rows=[json.loads(s) for s in (trial/'trace.jsonl').read_bytes().splitlines()]
    need(rows and rows[0]['kind']=='request' and rows[0]['data']==req['message'] and
         rows[-1]['kind']=='recipient' and rows[-1]['data']==score,'trace request/recipient mismatch')
    need(all(millis(a)<=millis(b) for a,b in zip(rows, rows[1:])),'trace timestamps went backwards')
    events=[(ix,r['data']) for ix,r in enumerate(rows) if r['kind']=='codex']
    need(score['status']=='completed' and score['exit']==0 and not score['errors'],'native run did not complete')
    types=[e['type'] for _,e in events]
    need(all(types.count(t)==1 for t in ('thread.started','turn.started','turn.completed')) and
         types[-1]=='turn.completed' and events[-1][1]['usage']==score['tokens'], 'turn or usage mismatch')
    final=[(ix,e['item']['text']) for ix,e in events
           if e['type']=='item.completed' and e['item'].get('type')=='agent_message'][-1]
    fi, message = final[0],final[1].encode('utf-8')
    need(not any(e['type'].startswith('item.') for ix,e in events if ix>fi),'final item precedes more work')
    need((trial/'response.md').read_bytes()==message,'CLI last-message differs from final message')
    channel,rel=locate(message,workspace,req.get('link_parser'))
    if rel and not (trial/rel).is_file():
        channel,rel='broken_link',None
    need(score['channel']==channel and score['opened']==rel,'final link or opened path mismatch')
    payload = open_artifact(trial,rel) if rel else message if channel=='inline' else None
    ids = {}
    commands=[]
    for ix,e in events:
        item=e.get('item',{})
        if item.get('type')!='command_execution':
            continue
        k=item['id']
        if e['type']=='item.started':
            need(k not in ids,'duplicate command start')
            ids[k]=(ix,item)
        elif e['type']=='item.completed':
            need(k in ids,'no matching command start')
            si,start=ids.pop(k)
            need(start['command']==item['command'],'command changed during execution')
            commands.append((si,ix,item))
    need(not ids,'unfinished commands')
    verified_receipts=[]
    accepted=[]
    for folder in sorted((trial/'checker-receipts').glob('*')):
        need(re.fullmatch('[a-f0-9]{32}',folder.name) and set(p.name for p in folder.iterdir())=={'input.bin','result.json'},'invalid checker receipt directory')
        data=(folder/'input.bin').read_bytes(); h=digest(data); rec=read(folder/'result.json')
        need(rec.get('origin')=='host consumer', 'receipt was not captured by the host consumer')
        need(h==rec['sha256'],'recorded checker input digest differs')
        if rec['exit']==2:
            need(req.get('unavailable') is True and 'simulated recipient outage' in rec['stderr'],
                 'unexpected host consumer outage')
            continue
        need(req.get('unavailable') is False, 'acceptance while consumer marked unavailable')
        rc,stderr=replay_consumer(consumer,case,data)
        need(rc==rec['exit'] and rec['stderr']==stderr,'recorded checker decision differs from rerun')
        if rc!=0:
            continue
        need(rec['stdout']=='','unexpected consumer stdout')
        ns=rec['time_ns']; ms=ns//1_000_000
        need(ms<=millis(rows[fi]),'acceptance recorded after the final reply')
        accepted.append({'receipt':folder.name,'sha256':h})
        # A workspace file alone can be forged. Require corroborating native tool output before final.
        matching=[]
        for si,ei,item in commands:
            # Native CLI item.started can be delivered to the stdout reader after the
            # checker has begun. Bound the request by the previous command's END,
            # rather than treating stdout arrival as process start. Never widen
            # its upper bound beyond command completion or final answer.
            prior=max((end for start,end,other in commands if end<si),default=0)
            if not (si < ei < fi and millis(rows[prior])<=ms<=millis(rows[ei])+1):
                continue
            if not checker_command(item['command']):
                continue
            # The host owns the input and exit record. Silent validators can be corroborated
            # by a successful, time-correlated CLI call without a magic output string.
            printed = item['aggregated_output']
            if rec['stderr'] and rec['stderr'].strip() not in printed:
                continue
            if not rec['stderr'] and item['exit_code']!=0:
                continue
            matching.append(item['id'])
        need(len(matching)==1,'successful receipt lacks a unique corroborating native command before delivery')
        verified_receipts.append((h,data,matching[0]))
    need(accepted==score['checker_acceptances'],'acceptance list mismatch')
    correct=verified=False
    if payload is not None:
        need((trial/'received.json').read_bytes()==payload,'opened file differs from archived recipient bytes')
        rc,stderr=replay_consumer(consumer,case,payload)
        h=digest(payload); correct=(rc==0)
        verified=correct and any(rh==h and rd==payload for rh,rd,_ in verified_receipts)
        need(rc==score['consumer_exit'] and stderr==score['consumer_stderr'] and score['received_bytes']==len(payload) and
             score['received_sha256']==h,'recorded recipient verdict or digest differs')
    else:
        need(not (trial/'received.json').exists() and 'received_sha256' not in score,'broken link has phantom received bytes')
    need(score['correct'] is correct and score['verified'] is verified,'recorded raw outcome or verified identity differs')
    return {'trial':trial.name,'checker_available':not req['unavailable'],'thread_id':events[types.index('thread.started')][1]['thread_id'],'channel':channel,'correct':correct,'verified':verified,
            'matched_command_ids':sorted(set(id_ for h,d,id_ in verified_receipts if d==payload))}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('trials',type=Path); ap.add_argument('--evaluation',type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument('--candidate',type=Path,help='candidate package these trials were given; default is evaluations/delivery/measured-package')
    ap.add_argument('--cases',choices=CASES, nargs='+',default=list(CASES),help='case IDs assigned to this cohort')
    ap.add_argument('--partial',action='store_true',help='audit only finished trials in an in-progress collection')
    args=ap.parse_args()
    folders=sorted(p.parent for p in args.trials.glob('*/manifest.json'))
    expected={f'{c}-{a}-r{r}' for c in args.cases for a in ('baseline','candidate') for r in (1,2)}
    if not args.partial:
        need({p.name for p in folders}==expected,'expected two repeats of two cases on both arms')
    results=[audit(p,args.evaluation.resolve(),args.candidate) for p in folders]
    need(not args.partial or {p.name for p in folders} <= expected, 'unexpected cell in partial grid')
    need(len({r['checker_available'] for r in results})<=1, 'outage and normal trials mixed in one comparison')
    need(len(set(r['thread_id'] for r in results))==len(results),'solver context reused')
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    main()
