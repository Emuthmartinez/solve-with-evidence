"""Run a task's hidden checks against WORKDIR/solution.py and print one JSON verdict."""
import contextlib
import importlib.util
import json
import sys
from pathlib import Path


def main(checks):
    """checks: list of (name, function(solution_module) -> truthy when the check holds)."""
    # A solution may print. Its output goes to stderr so stdout carries only the verdict.
    with contextlib.redirect_stdout(sys.stderr):
        verdict = run(checks)
    print(json.dumps(verdict))


def run(checks):
    failed = []
    try:
        path = Path(sys.argv[1]) / 'solution.py'
        spec = importlib.util.spec_from_file_location('solution', path)
        solution = importlib.util.module_from_spec(spec)
        # As import does: code that looks its own module up while loading (dataclasses do) must find it.
        sys.modules[spec.name] = solution
        spec.loader.exec_module(solution)
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
