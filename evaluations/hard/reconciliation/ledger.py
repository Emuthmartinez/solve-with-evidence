"""Executable, two-stage reconciliation challenges. Only prompt() is solver input."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
CASES = ('ledger-d1', 'ledger-h1')
DEV = CASES[0]
CALCULATOR = HERE.parent / 'runner' / 'calculate.py'

DEV_RULES = """Implement audit(events, at) for a synthetic parcel tracking audit. Inputs are a list of JSON objects and an integer as-of time. Every eligible record has seen <= at. Ignore future records completely, including their keys. For each key having an eligible record, return exactly one string. In stage 1 all records have kind 'obs' and fields key, rev (positive integer), state ('arrived' or 'missed'), stamp (time of physical measurement), seen (delivery time). Duplicate copies and delivery order carry no authority. Keep all observations at that key's highest eligible rev. If their (state, stamp) pairs disagree, return 'conflict'. Otherwise return 'stale' when at - stamp > 6 and return the state otherwise. The freshness interval includes its boundary. Empty input returns {}."""
DEV_DELTA = """Provider amendment. Keep all prior rules, including the full stage-1 input domain. A record of kind 'fix' has key, rev, n (positive amendment sequence), state, stamp, seen. At each key choose the highest eligible observation revision first. A key with only eligible fixes is absent from the output. Ignore fixes to any other revision. If eligible fixes target the selected revision, use only fixes at the highest n at that revision, suppressing all original observations. Unequal (state, stamp) pairs tied there give 'conflict'. Apply the original freshness rule to an agreed amendment. An amendment can arrive before the observation, can repair an original conflict and cannot promote an unobserved revision."""
HOLD_RULES = """Implement audit(events, at) for a synthetic two-replica archival service. Inputs are a list of JSON objects and an integer as-of time. In stage 1 all records have kind 'ack' and fields key, side ('L' or 'R'), epoch (a positive integer), digest (a string), seen (integer delivery time). Only records with seen <= at participate. For each key with an eligible ack, on each side independently keep its highest eligible epoch and the set of digests at that epoch. Duplicate deliveries and order carry no authority. Return 'conflict' if either side has more than one digest at its selected epoch, even when the other side is absent. Otherwise return 'pending' if one side is absent or their selected epochs differ, 'diverged' if both selected epochs match and their digests differ, or 'verified' if epochs and digests match. Empty input returns {}."""
HOLD_DELTA = """Provider amendment. Keep all stage-1 behavior for inputs containing only acknowledgements. A withdrawal has kind 'fence' and fields key, side, through (positive inclusive epoch), seen. For each eligible key and side, take the maximum through over fences with seen <= at. Discard acks on that side at epochs <= its fence before choosing the side's latest surviving epoch. A fence can arrive earlier than its affected acknowledgements. For a key with eligible records including fences, if neither side has a surviving ack return 'withdrawn'. If any side has a surviving ack use the stage-1 precedence, including conflict first. A fence is scoped to one key and side. Only future records means no output key."""

FORM = """Return only a JSON object with three keys. 'source' is a complete standalone Python 3 implementation including def audit(events, at); 'result' is your audit output on the supplied instance; 'counterexample' is an object with keys 'events', 'at' and 'expected'. Give a counterexample of at most five records using this stage's documented inputs such that the stated faulty implementation produces a different output. 'expected' must give the correct audit result for that counterexample. The function must return a new dict, leave inputs untouched, and work across calls and previously valid inputs. Use standard-library Python with no I/O, environment access, or nondeterminism. The evaluator executes your submitted source."""

BUGS = {
    (DEV, 1): 'The faulty implementation keeps only the last observation encountered among ties at the selected revision and otherwise follows the rules.',
    (DEV, 2): 'The faulty implementation discards all fixes and applies the original observation-only policy.',
    (CASES[1], 1): "The faulty implementation treats equal digests on the two selected sides as verified even when the selected epochs differ. All other behavior follows the rules.",
    (CASES[1], 2): 'The faulty implementation ignores all fences and runs the original acknowledgement-only policy, omitting keys that have no eligible ack.',
}


def obs(k, rev, state, stamp, seen):
    return dict(kind='obs', key=k, rev=rev, state=state, stamp=stamp, seen=seen)


def fix(k, rev, n, state, stamp, seen):
    return dict(kind='fix', key=k, rev=rev, n=n, state=state, stamp=stamp, seen=seen)


def ack(k, side, epoch, digest, seen):
    return dict(kind='ack', key=k, side=side, epoch=epoch, digest=digest, seen=seen)


def fence(k, side, through, seen):
    return dict(kind='fence', key=k, side=side, through=through, seen=seen)


def instance(case, stage):
    if case == DEV:
        events = [obs('alder', 2, 'arrived', 14, 15), obs('alder', 2, 'missed', 14, 19),
                  obs('balsa', 4, 'missed', 13, 20), obs('cedar', 2, 'arrived', 14, 16),
                  obs('cedar', 1, 'missed', 18, 18), obs('dune', 1, 'arrived', 19, 21),
                  obs('alder', 2, 'arrived', 14, 15), obs('balsa', 5, 'arrived', 19, 30)]
        extra = [fix('alder', 2, 2, 'arrived', 19, 13), fix('alder', 4, 9, 'missed', 10, 14),
                 fix('balsa', 4, 1, 'arrived', 18, 13), fix('balsa', 4, 1, 'arrived', 19, 20),
                 fix('cedar', 2, 9, 'missed', 14, 21), fix('elm', 1, 1, 'arrived', 19, 19)]
    elif case == CASES[1]:
        events = [ack('juniper','L',3,'a',6), ack('juniper','R',2,'a',5),
                  ack('kelp','L',4,'b',8), ack('kelp','R',4,'b',9), ack('kelp','L',3,'c',4),
                  ack('larch','L',7,'a',12), ack('larch','L',7,'b',11), ack('larch','L',7,'a',12),
                  ack('maple','L',6,'x',8), ack('maple','R',6,'q',7),
                  ack('nova','R',4,'s',21)]
        extra = [fence('kelp','L',4,5), fence('kelp','R',4,12), fence('larch','L',6,6),
                 fence('maple','R',6,6), fence('juniper','L',2,21), fence('oak','R',2,4)]
    else:
        raise KeyError(case)
    return events + (extra if stage == 2 else []), 20


def prompt(case, stage):
    events, at = instance(case, stage)
    if stage == 1:
        policy = DEV_RULES if case == DEV else HOLD_RULES
    elif stage == 2:
        policy = DEV_DELTA if case == DEV else HOLD_DELTA
    else:
        raise ValueError(stage)
    return '\n\n'.join((policy, FORM, BUGS[(case, stage)],
                        'Instance at=' + str(at) + '\n' + json.dumps(events, separators=(',', ':'))))


def reference(case, stage, events, at, mutant=None):
    rows = [r for r in events if r['seen'] <= at]
    out = {}
    for key in sorted({r['key'] for r in rows}):
        scope = [r for r in rows if r['key'] == key]
        if case == DEV:
            base = [r for r in scope if r['kind'] == 'obs']
            if not base:
                continue
            v = max(r['rev'] for r in base)
            select = [r for r in base if r['rev'] == v]
            amendments = [r for r in scope if r['kind'] == 'fix' and r['rev'] == v]
            if stage == 2 and amendments and mutant != 'ignore':
                n = max(r['n'] for r in amendments)
                select = [r for r in amendments if r['n'] == n]
            values = {(r['state'], r['stamp']) for r in select}
            if mutant == 'last':
                values = {(select[-1]['state'], select[-1]['stamp'])}
            state, stamp = next(iter(values))
            out[key] = 'conflict' if len(values) > 1 else 'stale' if at - stamp > 6 else state
        else:
            sides = {}
            for side in ('L', 'R'):
                local = [r for r in scope if r['side'] == side]
                threshold = max((r['through'] for r in local if r['kind'] == 'fence'), default=0)
                if stage == 1 or mutant == 'ignore':
                    threshold = 0
                valid = [r for r in local if r['kind'] == 'ack' and r['epoch'] > threshold]
                if valid:
                    ep = max(r['epoch'] for r in valid)
                    sides[side] = ep, {r['digest'] for r in valid if r['epoch'] == ep}
            if not sides and mutant == 'ignore':
                continue
            if not sides:
                out[key] = 'withdrawn'
            elif any(len(ds) > 1 for _, ds in sides.values()):
                out[key] = 'conflict'
            elif len(sides) < 2:
                out[key] = 'pending'
            else:
                (le, ld), (re, rd) = sides['L'], sides['R']
                if mutant == 'epoch' and ld == rd:
                    out[key] = 'verified'
                else:
                    out[key] = 'pending' if le != re else 'diverged' if ld != rd else 'verified'
    return out


def suites(case, stage):
    at = 20
    if case == DEV:
        basic = [
            [],
            [obs('a', 3, 'arrived', 14, 15), obs('b', 1, 'missed', 13, 17)],
            [obs('a', 1, 'arrived', 15, 17), obs('a', 1, 'arrived', 14, 17)],
            [obs('a', 1, 'missed', 14, 21)],
            [obs('a', 1, 'arrived', 18, 19), obs('a', 2, 'missed', 10, 15)],
            [obs('b', 3, 'missed', 13, 19), obs('b', 3, 'arrived', 13, 19)],
        ]
        amended = [
            [fix('a', 9, 3, 'arrived', 20, 19)],
            [obs('a', 2, 'missed', 13, 19), fix('a', 2, 2, 'arrived', 14, 20),
             fix('a', 2, 1, 'missed', 18, 18), fix('a', 3, 9, 'missed', 18, 11)],
            [obs('b', 2, 'arrived', 19, 19), fix('b', 2, 2, 'arrived', 14, 15),
             fix('b', 2, 2, 'arrived', 13, 12), fix('b', 2, 7, 'missed', 12, 21)],
            [obs('x', 2, 'arrived', 19, 13), obs('x', 2, 'missed', 19, 12),
             fix('x', 2, 2, 'missed', 10, 17), fix('y', 1, 8, 'arrived', 19, 11)],
        ]
    else:
        basic = [
            [],
            [ack('a', 'L', 3, 'x', 1), ack('a', 'R', 2, 'x', 12)],
            [ack('a', 'L', 2, 'x', 1), ack('a', 'L', 2, 'y', 2)],
            [ack('a', 'L', 2, 'x', 1), ack('a', 'R', 2, 'y', 1), ack('a','L',1,'q',4)],
            [ack('a', 'L', 2, 'x', 1), ack('a', 'R', 2, 'x', 1), ack('a','R',2,'y',21)],
            [ack('a','L',1,'x',21), ack('b','R',2,'s',18)],
        ]
        amended = [
            [fence('x','R',7,4)],
            [ack('a','L',3,'x',19), ack('a','R',3,'x',18), fence('a','L',3,4)],
            [ack('a','L',3,'x',1), ack('a','L',3,'z',2), fence('a','L',3,3),
             ack('a','L',4,'y',12), ack('a','R',4,'y',12), fence('a','R',4,21)],
            [ack('a','R',4,'z',15), fence('a','R',5,17), fence('a','R',2,19),
             fence('b','L',8,20), ack('c','R',3,'z',21)],
        ]
    tests = {'rules': [(e, at) for e in basic]}
    if stage == 2:
        tests['amendment'] = [(e, at) for e in amended]
    rng = random.Random(1739 if case == DEV else 4193)
    random_cases = []
    for _ in range(24):
        rows = []
        for _ in range(rng.randrange(1, 21)):
            key = rng.choice(('u','v','w'))
            v, seen = rng.randint(1, 3), rng.randint(11, 24)
            if case == DEV:
                state, stamp = rng.choice(('arrived','missed')), rng.randint(8, 19)
                is_fix = stage == 2 and rng.random() < 0.33
                r = (fix(key,v,rng.randint(1,3),state,stamp,seen) if is_fix
                     else obs(key,v,state,stamp,seen))
            else:
                side = rng.choice(('L','R'))
                r = (fence(key,side,v,seen) if stage == 2 and rng.random() < 0.35
                     else ack(key,side,v,rng.choice(('p','q')),seen))
            rows.append(r)
        random_cases.append((rows, rng.randint(15, 22)))
    tests['seeded'] = random_cases
    tests['metamorphic'] = []
    for rows, point in [(instance(case, stage)), *random_cases[:5]]:
        # Reverse, retry, append an as-of-ineligible record, then translate the clock and keys.
        future = {**rows[0], 'key': 'future', 'seen': point + 1}
        changed = list(reversed(rows)) + rows[::2] + [future]
        tests['metamorphic'].append((changed, point))
        mapped = [{**r, 'key': 'z-' + r['key'], 'seen': r['seen'] + 17,
                   **({'stamp': r['stamp'] + 17} if 'stamp' in r else {})} for r in changed]
        tests['metamorphic'].append((mapped, point + 17))
    return tests


def example(case, stage):
    if case == DEV:
        if stage == 1:
            rows = [obs('a',1,'arrived',17,18), obs('a',1,'missed',17,19)]
        else:
            rows = [obs('b',2,'missed',14,19), fix('b',2,1,'arrived',14,17)]
    elif stage == 1:
        rows = [ack('a','L',1,'x',4), ack('a','R',2,'x',13)]
    else:
        rows = [fence('b','L',3,5), ack('b','L',3,'z',7)]
    return {'events': rows, 'at': 20, 'expected': reference(case, stage, rows, 20)}


def valid_witness(case, stage, witness):
    if not isinstance(witness, dict):
        return False
    rows, at = witness.get('events'), witness.get('at')
    if type(at) != int or not isinstance(rows, list) or not 1 <= len(rows) <= 5:
        return False
    kinds = ('obs', 'fix') if case == DEV else ('ack', 'fence')
    allowed = kinds if stage == 2 else kinds[:1]
    for r in rows:
        if not isinstance(r, dict) or r.get('kind') not in allowed or not isinstance(r.get('key'), str):
            return False
        k = r['kind']
        numeric = {'obs': ['rev','stamp'], 'fix': ['rev','n','stamp'],
                   'ack': ['epoch'], 'fence': ['through']}[k] + ['seen']
        if any(type(r.get(f)) != int for f in numeric):
            return False
        if any(r[f] <= 0 for f in ('rev','n','epoch','through') if f in numeric):
            return False
        if k in ('obs','fix') and r.get('state') not in ('arrived','missed'):
            return False
        if k in ('ack','fence') and r.get('side') not in ('L','R'):
            return False
        if k == 'ack' and not isinstance(r.get('digest'), str):
            return False
    correct = reference(case, stage, rows, at)
    fault = 'ignore' if stage == 2 else 'last' if case == DEV else 'epoch'
    return witness.get('expected') == correct != reference(case, stage, rows, at, fault)


# Candidate source and the finite set of inputs are arguments to a brand-new calculator
# process. Neither expected results nor the grader's file descriptors enter its sandbox.
CHILD = """
namespace = {"__name__": "__candidate__"}
exec(compile(candidate_source, "<submitted audit>", "exec"), namespace)
actual = []
for original, asof in batch:
    clone = json.loads(json.dumps(original))
    try:
        outcome = namespace["audit"](clone, asof)
        intact = clone == original
        valid = isinstance(outcome, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in outcome.items())
        actual.append({"result": dict(outcome) if valid else None, "intact": intact})
    except Exception as error:
        actual.append({"error": type(error).__name__})
print(json.dumps(actual, ensure_ascii=True, separators=(",",":")))
"""


def execute(source, batch):
    if not isinstance(source, str) or len(source.encode('utf-8')) > 32768:
        return [], 'missing or oversized source'
    script = 'candidate_source = ' + repr(source) + '\nbatch = ' + repr(batch) + '\n' + CHILD
    # Exactly the trial runner's sealed entrypoint and minimal environment. Never
    # import or execute model-supplied Python in the grading interpreter.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            p = subprocess.run([sys.executable, '-I', '-B', '-S', str(CALCULATOR)], input=script.encode(),
                               cwd='/', env={'LC_ALL': 'C'}, stdout=out, stderr=err, timeout=6)
        except subprocess.TimeoutExpired:
            return [], 'calculator timeout'
        if p.returncode != 0:
            return [], 'calculator exit ' + str(p.returncode)
        out.seek(0)
        try:
            results = json.loads(out.read(65536))
        except (ValueError, UnicodeDecodeError):
            return [], 'invalid calculator output'
    if not isinstance(results, list) or len(results) != len(batch):
        return [], 'wrong output count'
    return results, None


def grade(case, replies):
    if case not in CASES:
        raise KeyError(case)
    checks, details, failures = {}, {}, []
    def check(key, success, weight=1):
        checks[key] = {'passed': bool(success), 'weight': weight}
        if not success:
            failures.append(key)
    for stage in (1, 2):
        answer = replies[stage-1] if len(replies) >= stage and isinstance(replies[stage-1], dict) else {}
        tests = {'instance': [instance(case, stage)], **suites(case, stage)}
        rows = [(group, records, at) for group, cases in tests.items() for records, at in cases]
        actual, error = execute(answer.get('source'), [(rs, at) for _, rs, at in rows])
        tally = {group: 0 for group in tests}
        intact = len(actual) == len(rows)
        for (group, rs, at), value in zip(rows, actual):
            good = isinstance(value, dict) and value.get('intact') is True
            intact &= good
            if good and value.get('result') == reference(case, stage, rs, at):
                tally[group] += 1
        prefix = 'stage' + str(stage) + '_'
        for group, cases in tests.items():
            check(prefix + group, tally[group] == len(cases), 2 if group in ('amendment','seeded') else 1)
        check(prefix + 'pure', intact)
        check(prefix + 'reported_result', answer.get('result') == reference(case, stage, *instance(case, stage)))
        check(prefix + 'counterexample', valid_witness(case, stage, answer.get('counterexample')))
        details[str(stage)] = {'matched': tally, 'totals': {k:len(v) for k,v in tests.items()},
                               'runtime_error': error}
    return {'case': case, 'points': sum(c['weight'] for c in checks.values() if c['passed']),
            'max_points': sum(c['weight'] for c in checks.values()), 'pass': not failures,
            'checks': checks, 'critical_failures': failures, 'execution': details}


def controls():
    import inspect
    source = inspect.getsource(reference)
    receipts = {}
    for case in CASES:
        def submitted(stage, fault):
            call = f'return reference({case!r}, {stage}, events, at, mutant={fault!r})'
            implementation = f'DEV = {DEV!r}\n' + source + '\ndef audit(events, at):\n    ' + call
            return dict(source=implementation, result=reference(case, stage, *instance(case, stage)),
                        counterexample=example(case, stage))
        correct = [submitted(1, None), submitted(2, None)]
        positive = grade(case, correct)
        if not positive['pass']:
            raise AssertionError(positive)
        receipts[case] = {'reference': positive['points'], 'max_points': positive['max_points']}
        for name, mutant in [
            ('incorrect_stage1', [submitted(1, 'last' if case == DEV else 'epoch'), correct[1]]),
            ('ignores_provider_amendment', [correct[0], submitted(2, 'ignore')]),
            ('hardcoded_visible', [dict(x, source='def audit(events, at):\n    return ' + repr(x['result']))
                                   for x in correct]),
            ('mutates_input', [dict(x, source=x['source'] + '\nbase = audit\ndef audit(events, at):\n    answer = base(events, at)\n    events.clear()\n    return answer') for x in correct]),
            ('empty_counterexample', [dict(x, counterexample={}) for x in correct]),
            ('host_read', [dict(x, source="def audit(events, at):\n    return open('/etc/hosts').read()") for x in correct]),
        ]:
            score = grade(case, mutant)
            if score['pass']:
                raise AssertionError(f'accepted {name}')
            receipts[case][name] = score['critical_failures']
    return receipts


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--controls', action='store_true')
    ap.add_argument('--case', choices=CASES)
    ap.add_argument('--stage', type=int, choices=(1, 2))
    args = ap.parse_args()
    if args.controls:
        print(json.dumps(controls(), indent=2))
    elif args.case and args.stage:
        print(prompt(args.case, args.stage))
