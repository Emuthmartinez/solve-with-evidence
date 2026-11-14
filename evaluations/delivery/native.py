"""Exercise the ordinary Codex CLI shell and open the actual final Markdown link."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from contextlib import ExitStack
from checker_host import serve
from markdown_link import destination
from importlib.metadata import version
import shutil
import stat
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODEL = 'gpt-6.1-sol'
BASE = ('Apply the supplied Solve with Evidence skill in skill/SKILL.md. Use the ordinary shell when useful. '
        'The trusted receiver command for this job is ./case-check. It accepts JSON on stdin and reports its verdict. '
        'Treat it as an opaque tool. Do not inspect or modify its implementation or search for its tests. '
        'Write working files in the current directory. Put files for the user inside the outputs directory. '
        'The recipient resolves Markdown file links from the current directory and can open absolute local paths.\n\n')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def files(root):
    return {p.relative_to(root).as_posix():digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}


def receive(message, workspace, directory):
    """Resolve the emitted local link within the original, pinned outputs directory."""
    target = destination(message)
    if target is None:
        return 'inline', message, None
    try:
        path = Path(target)
        if path.is_absolute():
            path = path.relative_to(workspace)
        if '..' in path.parts or path.parts[:1] != ('outputs',) or len(path.parts) < 2:
            raise ValueError('outside output root')
        info = (workspace/'outputs').lstat()
        if not stat.S_ISDIR(info.st_mode) or not os.path.samestat(info,os.fstat(directory)):
            raise ValueError('output root changed')
        with ExitStack() as scope:
            parent = directory
            for part in path.parts[1:-1]:
                parent = os.open(part,os.O_DIRECTORY | os.O_NOFOLLOW | os.O_RDONLY, dir_fd=parent)
                scope.callback(os.close,parent)
            fd = os.open(path.name, os.O_NOFOLLOW | os.O_NONBLOCK | os.O_RDONLY, dir_fd=parent)
            with os.fdopen(fd,'rb',buffering=0) as stream:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 131073:
                    raise ValueError('invalid artifact')
                raw = stream.read(131074)
                if len(raw)>131073: raise ValueError('oversized artifact')
        return 'file',raw,path.as_posix()
    except (OSError, ValueError):
        return 'broken_link',None,None


def run(arm, case, repeat, out, unavailable=False):
    if out.exists():
        raise ValueError('use a new trial directory')
    out.mkdir(parents=True)
    with ExitStack() as stack:
        runtime = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='swe-native-',dir='/private/tmp')))
        return session(arm,case,repeat,out,unavailable,runtime,stack)


def session(arm,case,repeat,out,unavailable,runtime,stack):
    job, home = runtime/'workspace', runtime/'session'
    job.mkdir(); home.mkdir()
    (job/'outputs').mkdir()
    directory=os.open(job/'outputs',os.O_DIRECTORY | os.O_NOFOLLOW | os.O_RDONLY)
    stack.callback(os.close,directory)
    auth = Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))/'auth.json'
    (home/'auth.json').symlink_to(auth)
    package = HERE/'snapshots/candidate' if arm == 'candidate' else ROOT/'evaluations/hard/snapshots/shipped'
    shutil.copytree(package,job/'skill')
    suite = HERE / ('transfer' if case == 'packet-map' else 'cases')
    consumer = suite / 'consumer.py'
    original = json.loads((suite/'inputs'/f'{case}.json').read_text())
    task = BASE + original['messages'][0]
    recorder = stack.enter_context(serve(job,out,consumer,case,unavailable))
    checker = job/'case-check'
    checker.write_bytes(b'#!/usr/bin/env python3\n' + (HERE/'checker_client.py').read_bytes())
    checker_identity=digest(checker.read_bytes())
    checker.chmod(0o755)
    env = {'HOME':str(home),'CODEX_HOME':str(home),'PATH':'/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin','SHELL':'/bin/bash','TMPDIR':str(runtime),'LC_ALL':'C','LANG':'C','PYTHONDONTWRITEBYTECODE':'1'}
    command = ['codex','--no-daemon','-a','never','exec','--ephemeral','--ignore-user-config','--ignore-rules',
               '--disable','plugins','--disable','apps','--disable','memories','--disable','hooks','--disable','shell_snapshot',
               '--enable','skip_host_skill_discovery','-c','project_doc_max_bytes=0','-c','web_search="disabled"',
               '-c','model_reasoning_effort="medium"','-c','suppress_unstable_features_warning=true',
               '--skip-git-repo-check','-s','workspace-write','-C',str(job),'-m',MODEL,'--json','-o',str(runtime/'last-message'),'-']
    save(out/'request.json',{'case':case,'arm':arm,'repeat':repeat,'message':task,'link_parser':'markdown-it-py/'+version('markdown-it-py')+' commonmark','skill_sha256':files(package),
                             'consumer_sha256':digest(consumer.read_bytes()),'unavailable':unavailable,'workspace':str(job),'command':command,
                             'timeout_seconds':300,'cli':subprocess.check_output(['codex','--version'],text=True).strip()})
    started=time.monotonic()
    stamp=lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds')
    events=[]; errors=[]; reply=None; usage=None
    with (out/'trace.jsonl').open('w') as trace:
        def emit(kind,data):
            trace.write(json.dumps({'at':stamp(),'kind':kind,'data':data},ensure_ascii=False)+'\n');trace.flush()
        emit('request',task)
        with tempfile.TemporaryFile() as stderr:
            proc=subprocess.Popen(command,env=env,cwd=job,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,start_new_session=True)
            def stop(*_):
                if proc.poll() is None: os.killpg(proc.pid,signal.SIGKILL)
            prior=signal.signal(signal.SIGALRM,stop);signal.alarm(300)
            try:
                proc.stdin.write(task.encode());proc.stdin.close()
                for line in proc.stdout:
                    e=json.loads(line);item=e.get('item',{})
                    if item.get('type')=='reasoning': continue
                    emit('codex',e);events.append(e)
                    if e['type']=='item.completed':
                        if item.get('type')=='agent_message':
                            reply=item['text'].encode(); final_at=time.time_ns()
                    if e['type']=='turn.completed': usage=e.get('usage')
                    if e['type'] in ('error','turn.failed'): errors.append(e['type'])
                proc.wait()
            finally:
                stop(); proc.wait(); signal.alarm(0); signal.signal(signal.SIGALRM,prior)
            stderr.seek(0);log=stderr.read().decode(errors='replace')
            if proc.returncode and not events:
                emit('startup_diagnostic',log[-1600:].replace(str(Path.home()),'<home>'))
        if digest(checker.read_bytes()) != checker_identity:
            raise ValueError('trusted checker was replaced')
        accepted=[]
        if recorder.exists():
            for path in sorted((out/'checker-receipts').glob('*/result.json')):
                record = json.loads(path.read_bytes())
                payload=(path.parent/'input.bin').read_bytes()
                if digest(payload)!=record['sha256']: raise ValueError('corrupt checker receipt')
                if record['exit']==0 and reply is not None and record['time_ns']<=final_at:
                    accepted.append({'receipt':path.parent.name, 'sha256':record['sha256']})
        result={'status':'infrastructure_failure','case':case,'arm':arm,'repeat':repeat,'exit':proc.returncode,
                'runtime_seconds':round(time.monotonic()-started,3),'tokens':usage,'checker_acceptances':accepted,'errors':errors}
        if reply is not None and proc.returncode==0 and usage is not None:
            exported=(runtime/'last-message').read_bytes()
            if reply!=exported: raise ValueError('last-message export differs from final assistant item')
            (out/'response.md').write_bytes(exported)
            channel,raw,opened=receive(exported,job,directory)
            result.update(status='completed',channel=channel,opened=opened,correct=False,verified=False)
            if raw is not None:
                (out/'received.json').write_bytes(raw)
                verdict=subprocess.run([sys.executable,'-B',str(consumer),case],input=raw,capture_output=True,timeout=25)
                if channel=='file':
                    actual_path=job/opened
                    copy=out/actual_path.relative_to(job)
                    copy.parent.mkdir(parents=True,exist_ok=True);copy.write_bytes(raw)
                identifier=digest(raw)
                result.update(received_sha256=identifier,received_bytes=len(raw),correct=verdict.returncode==0,
                              verified=(verdict.returncode==0 and any(r['sha256']==identifier for r in accepted)),
                              consumer_exit=verdict.returncode,consumer_stderr=verdict.stderr.decode())
        emit('recipient',result)
    save(out/'result.json',result)
    save(out/'manifest.json',files(out))
    print(arm,case,repeat,result['status'],result.get('correct'),result.get('verified'),flush=True)
    return int(result['status']!='completed')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('arm',choices=('baseline','candidate'))
    p.add_argument('case',choices=('night-window','octet-frame','packet-map'))
    p.add_argument('repeat',type=int)
    p.add_argument('out',type=Path)
    p.add_argument('--unavailable',action='store_true',help='exercise an explicit checker outage')
    a=p.parse_args()
    raise SystemExit(run(a.arm,a.case,a.repeat,a.out.resolve(),a.unavailable))
