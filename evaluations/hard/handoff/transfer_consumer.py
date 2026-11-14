"""Trusted verifier for two historical transfer contracts. The generic gate never runs candidate code."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'solve-with-evidence' / 'scripts'))
from json_handoff import Reject, parse

sys.path.insert(0, str(ROOT / 'reconciliation'))
import artifact_transfer as printer
import ledger_transfer as ledger

MODULES = {printer.CASE: printer, ledger.CASE: ledger}


def verify(case, stage, raw):
    payload = parse(raw)
    if stage not in (1, 2) or case not in MODULES:
        raise ValueError('unknown case or stage')
    if (set(payload) != {'source','result','edge'} or not isinstance(payload['source'], str)
            or not isinstance(payload['edge'], dict)):
        raise Reject('expected source, result, edge')
    edge = payload['edge']
    if case == printer.CASE:
        if set(edge) != {'job','expected'} or not isinstance(edge['job'], dict):
            raise Reject('edge.job must be a named job object')
        if not printer.valid_edge(edge, stage):
            raise Reject('edge must be valid, exact, and distinguish the two encoders')
        match = lambda value, expected: type(value) is str and value == expected
        observed, error = printer.run(payload['source'], [edge['job']])
    else:
        if set(edge) != {'charges','slots','expected'} or not ledger.valid(edge['charges'],edge['slots'],stage) or not 1 <= len(edge['charges']) <= 5:
            raise Reject('edge requires valid charges, slots and expected')
        expected = ledger.canonical(edge['charges'],edge['slots'])
        match = ledger.exact_dict
        if not match(edge['expected'],expected):
            raise Reject('edge.expected disagrees with reference')
        if expected == ledger.canonical(edge['charges'],edge['slots'],'insertion' if stage == 1 else 'clip_once'):
            raise Reject('correct and faulty allocators agree on the proposed edge')
        observed, error = ledger.execute(payload['source'], [(edge['charges'],edge['slots'])])
    if error or len(observed) != 1 or observed[0].get('pure') is not True or not match(observed[0].get('result'),edge['expected']):
        raise Reject('delivered source failed on the exact proposed edge')
    # The frozen grader runs its held-out suites and checks the reported result.
    # Only the requested stage is relevant here (the other is deliberately empty).
    result = MODULES[case].grade(case, [payload] if stage == 1 else [{},payload])
    failures = [k for k in result['critical_failures'] if k.startswith(f'stage{stage}_')]
    if failures:
        raise Reject('consumer checks failed: ' + ', '.join(failures))
    return True


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('case', choices=MODULES)
    p.add_argument('stage', type=int, choices=(1,2))
    a = p.parse_args()
    try:
        verify(a.case, a.stage, sys.stdin.buffer.read())
    except Reject as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'consumer unavailable: {type(e).__name__}: {e}', file=sys.stderr)
        sys.exit(2)
