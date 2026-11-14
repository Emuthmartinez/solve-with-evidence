"""Run one instrumented Codex app-server trial against the actual installed-format delivery CLI."""
import argparse
import asyncio
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_core(folder):
    spec = importlib.util.spec_from_file_location('capture_core', folder / 'run_trial.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TOOLS.append(module.spec('deliver_json',
        'Submit an earlier successful Python tool call’s exact stdout bytes to the configured trusted '
        'consumer for this task. Print only the complete deliverable JSON in that call. Pass source '
        '"last" for the most recent successful Python call, or its call ID. On acceptance this '
        'tool returns a Markdown link to a verified file for the user. On rejection use the feedback '
        'to correct the producer and submit again. Each link is relative to the final message.', 'source'))
    return module


class Delivery:
    async def calculate(self, code):
        if len(code.encode()) > 32768:
            return {'stdout': '', 'stderr': 'Code exceeds 32768 bytes', 'exit_code': None,
                    'timed_out': False}
        with tempfile.TemporaryFile(dir=self.scratch) as out, tempfile.TemporaryFile(dir=self.scratch) as err:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, '-I', '-B', '-S', str(self.args.core / 'calculate.py'),
                stdin=asyncio.subprocess.PIPE, stdout=out, stderr=err, cwd='/',
                env={'LC_ALL':'C'}, start_new_session=True)
            timed_out = False
            try:
                await asyncio.wait_for(proc.communicate(code.encode()), 6)
            except asyncio.TimeoutError:
                timed_out = True
            finally:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
            out.seek(0); err.seek(0)
            raw, errors = out.read(), err.read()
            text = raw.decode('utf8', errors='replace')
            error = errors.decode('utf8', errors='replace').replace(str(self.args.core / 'calculate.py'), '<calculator>')
            result = {'stdout': text, 'stderr': error, 'exit_code': proc.returncode, 'timed_out': timed_out,
                      'stdout_sha256': digest(raw), 'stdout_bytes': len(raw)}
            if text.encode() != raw:
                result['stdout_base64'] = base64.b64encode(raw).decode('ascii')
            if proc.returncode == 0 and not timed_out:
                self.producers[self.active_call] = raw
            return result

    def deliver(self, source, call_id):
        source_id = next(reversed(self.producers), None) if source == 'last' else source
        record = {'delivery_call_id':call_id, 'producer_call_id':source_id, 'status':'unavailable'}
        self.attempts.append(record)
        if source_id not in self.producers:
            record['diagnostic'] = 'No such successful Python call.'
            return record
        payload = self.producers[source_id]
        record.update(producer_sha256=digest(payload), producer_bytes=len(payload))
        submitted = self.scratch / 'producer.stdout'
        submitted.write_bytes(payload)
        try:
            result = subprocess.run([sys.executable,'-B',str(self.args.gate),str(submitted),'--deliver-to',
                                     'artifacts','--',sys.executable,'-B',str(self.args.consumer),self.meta['case_id']],
                                    cwd=self.out, capture_output=True, timeout=30)
        except (subprocess.TimeoutExpired, OSError) as error:
            record['diagnostic'] = type(error).__name__
            return record
        record['exit'] = result.returncode
        record['diagnostic'] = result.stderr.decode('utf8', errors='replace').replace(str(self.out),'<trial>').replace(str(self.scratch),'<runtime>')
        if result.returncode:
            record['status'] = 'rejected' if result.returncode == 1 else 'unavailable'
            if result.stdout:
                raise ValueError('checker emitted data on rejection')
            return record
        receipt = json.loads(result.stdout)
        filename = f"artifacts/{digest(payload)}.json"
        expected = self.out / filename
        if (Path(receipt['path']) != expected or receipt['sha256'] != digest(payload)
                or receipt['bytes'] != len(payload) or expected.is_symlink() or expected.read_bytes() != payload):
            raise ValueError('checker receipt or written bytes disagree with producer stdout')
        record.update(status='accepted', receipt={'path':filename, 'sha256':digest(payload), 'bytes':len(payload)},
                      link=f'[Download verified JSON]({filename})')
        return record

    async def tool(self, msg):
        p = msg['params']
        self.active_call = p['callId']
        if p['tool'] != 'deliver_json':
            await super().tool(msg)
            return
        self.meta['turns'][-1]['tool_calls'] += 1
        self.meta['tool_calls'] += 1
        self.emit('tool_call', {k:p.get(k) for k in ('tool','namespace','arguments','callId')})
        if self.meta['turns'][-1]['tool_calls'] > self.args.tool_cap:
            value, ok = 'Trial tool call cap reached.', False
        else:
            record = self.deliver(p['arguments'].get('source'),p['callId'])
            self.emit('delivery', record)
            value, ok = json.dumps(record, ensure_ascii=False), record['status']=='accepted'
        reply = {'success':ok,'contentItems':[{'type':'inputText','text':value}]}
        self.emit('tool_result', {'callId':p['callId'],'tool':p['tool'],'result':reply})
        await self.send({'id':msg['id'],'result':reply})

    async def run(self):
        self.producers = {}
        self.attempts = []
        await super().run()
        raw = self.meta['turns'][0]['text'].encode('utf8')
        (self.out / 'response.md').write_bytes(raw)
        self.core.write_json(self.out/'attempts.json',self.attempts)
        # This separate process only gets the final message, its document root, receipts and the trusted checker.
        result = subprocess.run([sys.executable,'-B',str(HERE/'recipient.py'),'--case',self.meta['case_id'],
                                 '--message',str(self.out/'response.md'),'--receipts',str(self.out/'attempts.json'),
                                 '--consumer',str(self.args.consumer),'--out',str(self.out/'recipient.json')],
                                capture_output=True,timeout=45)
        if result.returncode:
            raise RuntimeError('recipient process failed: '+result.stderr.decode(errors='replace')[-200:])
        report = json.loads((self.out/'recipient.json').read_bytes())
        self.emit('recipient',report)
        self.meta['recipient'] = report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['case','skill','consumer','gate','out']:
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--core',type=Path,default=HERE.parents[1]/'hard'/'runner')
    p.add_argument('--arm',required=True)
    p.add_argument('--repeat',type=int,required=True)
    p.add_argument('--model',default='gpt-6.1-sol')
    p.add_argument('--effort',default='medium',choices=['low','medium','high'])
    p.add_argument('--timeout',type=int,default=200)
    p.add_argument('--tool-cap',type=int,default=24)
    args = p.parse_args()
    for name in ['case','skill','consumer','gate','out','core']:
        setattr(args,name,getattr(args,name).resolve())
    case = json.loads(args.case.read_bytes())
    if (platform.system()!='Darwin' or args.timeout<1 or args.tool_cap<1 or args.repeat<1 or
            len(case['messages'])!=1 or not isinstance(case['messages'][0],str)):
        p.error('macOS, one full prompt, positive caps and repeat number required')
    args.out.mkdir(parents=True,exist_ok=True)
    if any(args.out.iterdir()):
        p.error('provide a new output directory')
    core = load_core(args.core)
    class Trial(Delivery,core.Trial):
        pass
    with tempfile.TemporaryDirectory(dir=args.out.parent,prefix='.solver-runtime-') as tmp:
        trial=Trial(args,case,args.skill,args.out,Path(tmp))
        trial.core=core
        trial.meta.update(arm=args.arm, repeat=args.repeat, delivery_runner_sha256=digest(Path(__file__).read_bytes()),
                          gate_sha256=digest(args.gate.read_bytes()),consumer_sha256=digest(args.consumer.read_bytes()),
                          recipient_sha256=digest((HERE/'recipient.py').read_bytes()),
                          file_link_base='directory containing response.md')
        asyncio.run(trial.capture())
    files={p.relative_to(args.out).as_posix():digest(p.read_bytes()) for p in sorted(args.out.rglob('*'))
           if p.is_file() and p.name!='manifest.json'}
    core.write_json(args.out/'manifest.json',files)
    print(json.dumps({'status':trial.meta['status'],'gate_attempts':len(trial.attempts),
                      'result':trial.meta.get('recipient')}))
    return int(trial.meta['status']!='completed')


if __name__ == '__main__':
    raise SystemExit(main())
