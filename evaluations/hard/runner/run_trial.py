#!/usr/bin/env python3
"""Capture one fresh, sequential, synthetic two-turn Codex trial on macOS."""
import argparse
import asyncio
import datetime as dt
import hashlib
import json
import os
import pathlib
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
BASE = ("You are a problem-solving agent. Apply the supplied skill to the user's task. "
        "Each new user message continues the same task. Use the available calculation "
        "and skill-reference tools as helpful. Return the requested answer.")
DISABLED = ("apps plugins remote_plugin memories multi_agent multi_agent_v2 hooks "
            "computer_use browser_use shell_tool view_image image_generation skill_search "
            "shell_snapshot artifact in_app_browser in_app_chat workspace_dependencies "
            "chronicle unified_exec").split()
OPTIONS = ['--enable', 'skip_host_skill_discovery', '-c', 'project_doc_max_bytes=0',
           '-c', 'web_search="disabled"', '-c', 'suppress_unstable_features_warning=true']
for feature in DISABLED:
    OPTIONS.extend(['--disable', feature])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, obj):
    temp = path.with_suffix('.new')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds')


def spec(name, description, key):
    schema = {'type': 'object', 'properties': {key: {'type': 'string'}},
              'required': [key], 'additionalProperties': False}
    return {'type': 'function', 'name': name, 'description': description,
            'inputSchema': schema, 'deferLoading': False}


TOOLS = [
    spec('python', 'Run Python for local calculations. Print results. No files, '
         'network, subprocesses, or persistent state. Modules available include '
         'math, itertools, statistics, fractions, collections, heapq, re and json.', 'code'),
    spec('read_reference', 'Read a Markdown file from the supplied skill references. '
         'Pass its relative path, such as references/validation.md.', 'path'),
]


class Trial:
    def __init__(self, args, case, folder, out, scratch):
        self.args, self.out, self.scratch = args, out, scratch
        self.messages = case['messages']
        self.entry = (folder / 'SKILL.md').read_text()
        self.references = {p.relative_to(folder).as_posix(): p.read_text()
                           for p in sorted((folder / 'references').rglob('*.md')) if p.is_file()}
        self.developer = self.entry + '\n\nAvailable skill reference paths:\n' + '\n'.join(self.references)
        self.start = time.monotonic()
        self.seq = 0
        self.turn = 0
        self.thread = ''
        self.proc = None
        self.closed = False
        self.log = (out / 'trace.jsonl').open('x', encoding='utf-8', buffering=1)
        skill_hashes = {k: sha(v.encode()) for k, v in {'SKILL.md': self.entry, **self.references}.items()}
        self.meta = {
            'schema': 1, 'case_id': case['id'], 'status': 'running', 'model': None,
            'requested_model': args.model, 'effort': args.effort, 'started_at': now(),
            'auth': None, 'turn_timeout_s': args.timeout, 'tool_cap_per_turn': args.tool_cap,
            'calculator_timeout_s': 6, 'calculator_output_cap_bytes_per_stream': 65536,
            'turns': [], 'tool_calls': 0, 'skill_files_sha256': skill_hashes,
            'case_messages_sha256': sha(json.dumps(self.messages, ensure_ascii=False).encode()),
            'runner_sha256': {p: sha((HERE / p).read_bytes()) for p in ('run_trial.py', 'calculate.py')},
            'runtime': {'codex_cli': subprocess.check_output(['codex', '--version'], text=True).strip(),
                        'python': platform.python_version(), 'platform': platform.system(),
                        'arch': platform.machine(), 'cli_options': OPTIONS},
            'capture': ('Public app-server conversation, completed item payloads, exact dynamic tool '
                        'arguments and replies, calculator streams/exit, submitted instructions, '
                        'stage times, and provider-reported token usage.'),
            'unavailable': ['provider prompt serialization, server-internal instruction layers and model weights',
                            'hidden reasoning, model sampling seed and per-request price',
                            'app-server internal tool dispatch and provider-side timestamps beyond public events'],
            'excluded': ['private reasoning data', 'account metadata apart from auth mode',
                         'transport text deltas duplicated by completed items', 'app-server diagnostics'],
        }
        self.persist()

    def persist(self):
        self.meta['elapsed_s'] = round(time.monotonic() - self.start, 3)
        write_json(self.out / 'summary.json', self.meta)

    def emit(self, kind, data):
        self.seq += 1
        rec = {'seq': self.seq, 'at': now(), 'elapsed_s': round(time.monotonic() - self.start, 3),
               'stage': self.turn, 'kind': kind, 'data': data}
        self.log.write(json.dumps(rec, ensure_ascii=False, separators=(',', ':')) + '\n')

    async def send(self, obj):
        self.proc.stdin.write(json.dumps(obj).encode() + b'\n')
        await self.proc.stdin.drain()

    async def receive(self):
        raw = await self.proc.stdout.readline()
        if not raw:
            raise RuntimeError('app-server transport closed')
        return json.loads(raw)

    async def request(self, number, method, params):
        await self.send({'id': number, 'method': method, 'params': params})
        while True:
            msg = await self.receive()
            if 'method' not in msg and msg.get('id') == number:
                if 'error' in msg:
                    raise RuntimeError(f"{method}: {msg['error'].get('message', 'RPC error')}")
                return msg['result']
            await self.event(msg)

    async def calculate(self, code):
        if len(code.encode()) > 32768:
            return {'stdout': '', 'stderr': 'Code exceeds 32768 bytes', 'exit_code': None}
        with tempfile.TemporaryFile(dir=self.scratch) as stdout, tempfile.TemporaryFile(dir=self.scratch) as stderr:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, '-I', '-B', '-S', str(HERE / 'calculate.py'),
                stdin=asyncio.subprocess.PIPE, stdout=stdout, stderr=stderr, cwd='/',
                env={'LC_ALL': 'C'}, start_new_session=True)
            timed_out = False
            try:
                await asyncio.wait_for(proc.communicate(code.encode()), 6)
            except asyncio.TimeoutError:
                timed_out = True
            finally:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
            stdout.seek(0)
            stderr.seek(0)
            err = stderr.read(65536).decode(errors='replace').replace(str(HERE / 'calculate.py'), '<calculator>')
            return {'stdout': stdout.read(65536).decode(errors='replace'), 'stderr': err,
                    'exit_code': proc.returncode, 'timed_out': timed_out}

    async def tool(self, msg):
        p = msg['params']
        name, args = p['tool'], p['arguments']
        row = self.meta['turns'][-1]
        row['tool_calls'] += 1
        self.meta['tool_calls'] += 1
        self.emit('tool_call', {k: p.get(k) for k in ('tool', 'namespace', 'arguments', 'callId')})
        ok = True
        if row['tool_calls'] > self.args.tool_cap:
            value, ok = 'Trial tool call cap reached.', False
        elif name == 'read_reference':
            value = self.references.get(args.get('path'))
            if value is None:
                value, ok = 'Unknown reference path.', False
        elif name == 'python' and isinstance(args.get('code'), str):
            result = await self.calculate(args['code'])
            ok = result['exit_code'] == 0
            value = json.dumps(result, ensure_ascii=False)
        else:
            value, ok = 'Unknown tool or invalid arguments.', False
        reply = {'success': ok, 'contentItems': [{'type': 'inputText', 'text': value}]}
        self.emit('tool_result', {'callId': p['callId'], 'tool': name, 'result': reply})
        await self.send({'id': msg['id'], 'result': reply})

    async def event(self, msg):
        method = msg.get('method', '')
        p = msg.get('params', {})
        if 'id' in msg and method:
            if method != 'item/tool/call':
                raise RuntimeError('unexpected app-server request: ' + method)
            await self.tool(msg)
        elif method in ('item/started', 'item/completed'):
            item = p['item']
            if item['type'] == 'reasoning':
                return
            # Retain the public structured item. Account/service metadata is never an item.
            self.emit(method, {'item': item, 'at_ms': p.get('startedAtMs', p.get('completedAtMs'))})
            if item['type'] == 'agentMessage' and method == 'item/completed' and self.turn:
                if item.get('phase') in (None, 'final_answer'):
                    self.meta['turns'][-1]['text'] = item['text']
        elif method == 'thread/tokenUsage/updated' and self.turn:
            usage = p['tokenUsage']
            self.emit('usage', usage)
            self.meta['turns'][-1]['usage'] = usage
        elif method == 'turn/completed':
            status = p['turn']['status']
            row = self.meta['turns'][-1]
            row.update(status=status, completed_at=now())
            timing = {k: v for k, v in p['turn'].items() if k in
                      ('id', 'status', 'startedAt', 'completedAt', 'durationMs', 'startedAtMs', 'completedAtMs')}
            self.emit(method, timing)
            self.persist()
            if status != 'completed':
                raise RuntimeError('turn ' + status + ': ' + str(p['turn'].get('error')))
            if not row['text']:
                raise RuntimeError('No public final answer for completed turn')
            self.closed = True
        elif method in ('error', 'model/rerouted', 'model/verification'):
            safe = str(p).replace(str(self.scratch), '<isolated-home>')
            self.emit(method, safe)
            if method == 'model/rerouted':
                raise RuntimeError('model rerouted during trial')
        elif method == 'turn/started':
            self.emit(method, {'id': p['turn']['id']})

    async def stage(self, prompt):
        await self.request(100 + self.turn, 'turn/start', {
            'threadId': self.thread, 'effort': self.args.effort,
            'environments': [], 'input': [{'type': 'text', 'text': prompt}],
        })
        while not self.closed:
            await self.event(await self.receive())

    async def run(self):
        credential = pathlib.Path(os.environ.get('CODEX_HOME') or pathlib.Path.home() / '.codex') / 'auth.json'
        # Only the parent transport can resolve this symlink. No model environment has a filesystem.
        if not credential.is_file():
            raise RuntimeError('Existing ChatGPT file-backed CLI session unavailable')
        (self.scratch / 'auth.json').symlink_to(credential.resolve())
        env = {'HOME': str(self.scratch), 'CODEX_HOME': str(self.scratch), 'LC_ALL': 'C',
               'PATH': '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin', 'TMPDIR': str(self.scratch), 'RUST_LOG': 'off'}
        cmd = [shutil.which('codex'), '--no-daemon', 'app-server', '--stdio', *OPTIONS,
               '-c', 'model_reasoning_effort="' + self.args.effort + '"']
        self.proc = await asyncio.create_subprocess_exec(*cmd, env=env, cwd='/',
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                limit=8 * 1024 * 1024, start_new_session=True)
        await self.request(1, 'initialize', {'clientInfo': {'name': 'synthetic-evals', 'version': '1'},
                                             'capabilities': {'experimentalApi': True}})
        await self.send({'method': 'initialized', 'params': {}})
        account = await self.request(2, 'account/read', {'refreshToken': False})
        self.meta['auth'] = (account.get('account') or {}).get('type')
        if self.meta['auth'] != 'chatgpt':
            raise RuntimeError('Runner requires existing ChatGPT subscription auth')
        params = {'cwd': '/', 'ephemeral': True, 'sandbox': 'read-only', 'environments': [],
                  'selectedCapabilityRoots': [], 'approvalPolicy': 'never', 'baseInstructions': BASE,
                  'developerInstructions': self.developer, 'dynamicTools': TOOLS,
                  'allowProviderModelFallback': False}
        if self.args.model:
            params['model'] = self.args.model
        self.emit('thread/request', params)
        r = await self.request(3, 'thread/start', params)
        self.thread = r['thread']['id']
        info = {k: r.get(k) for k in ('model', 'modelProvider', 'reasoningEffort', 'serviceTier',
                                      'instructionSources', 'cwd', 'approvalPolicy')}
        if info['instructionSources'] != [] or info['cwd'] != '/':
            raise RuntimeError('Unexpected personal instruction source or working directory')
        self.meta.update(model=r['model'], provider=r['modelProvider'], thread_id=self.thread, settings=info)
        if self.args.model and r['model'] != self.args.model:
            raise RuntimeError('Requested model differs from resolved model')
        self.emit('thread/settings', info)
        self.persist()
        for self.turn, prompt in enumerate(self.messages, 1):
            self.closed = False
            row = {'stage': self.turn, 'status': 'running', 'text': '', 'usage': None,
                   'tool_calls': 0, 'started_at': now()}
            self.meta['turns'].append(row)
            self.emit('user_input', {'text': prompt})
            self.persist()
            start = time.monotonic()
            try:
                await asyncio.wait_for(self.stage(prompt), self.args.timeout)
            finally:
                row['elapsed_s'] = round(time.monotonic() - start, 3)
                self.persist()
        self.meta['status'] = 'completed'

    async def capture(self):
        try:
            await asyncio.wait_for(self.run(), self.args.timeout * len(self.messages) + 45)
        except Exception as exc:
            self.meta['status'] = 'failed'
            error = (str(exc) or type(exc).__name__).replace(str(self.scratch), '<isolated-home>')
            self.meta['error'] = error
            if self.meta['turns'] and self.meta['turns'][-1]['status'] == 'running':
                self.meta['turns'][-1]['status'] = 'failed'
            self.emit('runner_error', {'message': error})
        finally:
            if self.proc is not None and self.proc.returncode is None:
                self.proc.stdin.close()
                try:
                    await asyncio.wait_for(self.proc.wait(), 2)
                except asyncio.TimeoutError:
                    try:
                        os.killpg(self.proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    await self.proc.wait()
            self.meta['ended_at'] = now()
            self.meta['app_server_exit_code'] = self.proc.returncode if self.proc else None
            self.emit('runner_end', {'status': self.meta['status']})
            self.log.close()
            self.persist()
            write_json(self.out / 'manifest.json', {n: sha((self.out / n).read_bytes())
                       for n in ('trace.jsonl', 'summary.json')})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case', type=pathlib.Path, required=True)
    ap.add_argument('--skill', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    ap.add_argument('--model', default=None)
    ap.add_argument('--effort', choices=('low', 'medium', 'high'), default='medium')
    ap.add_argument('--timeout', type=int, default=200)
    ap.add_argument('--tool-cap', type=int, default=24)
    a = ap.parse_args()
    case = json.loads(a.case.read_text())
    if platform.system() != 'Darwin' or not a.timeout > 0 or not a.tool_cap > 0:
        ap.error('macOS and positive timeout/tool cap required')
    if not isinstance(case.get('messages'), list) or not case['messages'] or not all(
            isinstance(p, str) and p for p in case['messages']) or not isinstance(case.get('id'),str):
        ap.error('case must have id and nonempty messages (list of strings)')
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        ap.error('trial output directory must be fresh')
    folder = a.skill if a.skill.is_dir() else a.skill.parent
    with tempfile.TemporaryDirectory(dir=out.parent, prefix='.solver-runtime-') as tmp:
        t = Trial(a, case, folder, out, pathlib.Path(tmp))
        asyncio.run(t.capture())
    print(f"{case['id']} {t.meta['status']} {t.meta['elapsed_s']}s")
    return 0 if t.meta['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
