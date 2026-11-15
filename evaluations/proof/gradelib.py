"""Run a task's hidden checks against WORKDIR/solution.py and print one JSON verdict."""
import importlib.util
import json
import sys
from pathlib import Path


def main(checks):
    """checks: list of (name, function(solution_module) -> truthy when the check holds)."""
    failed = []
    try:
        path = Path(sys.argv[1]) / 'solution.py'
        spec = importlib.util.spec_from_file_location('solution', path)
        solution = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(solution)
    except BaseException as exc:  # a solution that cannot load fails every check
        print(json.dumps({'pass': False, 'passed': 0, 'total': len(checks),
                          'failed': [f'load: {type(exc).__name__}: {exc}'[:200]]}))
        return
    for name, check in checks:
        try:
            ok = check(solution)
        except BaseException as exc:
            ok = False
            name = f'{name} ({type(exc).__name__})'
        if not ok:
            failed.append(name)
    print(json.dumps({'pass': not failed, 'passed': len(checks) - len(failed),
                      'total': len(checks), 'failed': failed}))


def raises(error, call, *args):
    try:
        call(*args)
    except error:
        return True
    except Exception:
        return False
    return False
