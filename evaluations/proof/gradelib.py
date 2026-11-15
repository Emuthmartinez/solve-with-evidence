"""Run a task's hidden checks against a module in WORKDIR and print one JSON verdict."""
import contextlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main(checks, module='solution'):
    """checks: list of (name, function(module) -> truthy when the check holds).
    module: dotted name of the delivered module, imported from WORKDIR."""
    # A solution may print. Its output goes to stderr so stdout carries only the verdict.
    with contextlib.redirect_stdout(sys.stderr):
        verdict = run(checks, module)
    print(json.dumps(verdict))


def run(checks, module):
    failed = []
    try:
        # The grader runs isolated (-I). The work directory goes first on the path so the
        # delivered module can import the files beside it, as it did where the agent ran it.
        sys.path.insert(0, sys.argv[1])
        solution = importlib.import_module(module)
    except BaseException as exc:  # a solution that cannot load fails every check
        return {'pass': False, 'passed': 0, 'total': len(checks), 'failed': [f'load: {type(exc).__name__}: {exc}'[:200]]}
    for name, check in checks:
        try:
            ok = check(solution)
        except BaseException as exc:
            ok = False
            name = f'{name} ({type(exc).__name__})'
        if not ok:
            failed.append(name)
    return {'pass': not failed, 'passed': len(checks) - len(failed), 'total': len(checks), 'failed': failed}


def raises(error, call, *args):
    try:
        call(*args)
    except error:
        return True
    except Exception:
        return False
    return False


def tests_pass(test_file, replace=None):
    """Run the delivered test file as the agent was told it would be run: `python3 <test_file>`
    in the work directory. `replace` maps relative paths to other source text, written over a
    copy of the work directory first. True when the run exits 0."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / 'work'
        shutil.copytree(sys.argv[1], work, ignore=shutil.ignore_patterns('__pycache__'))
        for name, source in (replace or {}).items():
            (work / name).write_text(source)
        try:
            # The limit only stops a hung run from outliving the grader.
            done = subprocess.run([sys.executable, '-B', test_file], cwd=work, capture_output=True, timeout=30,
                                  stdin=subprocess.DEVNULL, env={'PATH': os.environ.get('PATH', '')})
        except subprocess.TimeoutExpired:
            return False
        return done.returncode == 0
