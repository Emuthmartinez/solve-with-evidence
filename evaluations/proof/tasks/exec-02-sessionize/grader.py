import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises


def ev(id, ts, seq=1, user='u1'):
    return {'id': id, 'user': user, 'ts': ts, 'seq': seq}


def s(user, start, end, ids):
    return {'user': user, 'start': start, 'end': end, 'ids': ids}


def oracle(events, gap):
    """Independent second implementation: one global sort by (user, ts, id)."""
    best = {}
    for index, event in enumerate(events):
        rank = (event['seq'], index)
        if event['id'] not in best or rank > best[event['id']][0]:
            best[event['id']] = (rank, event)
    rows = sorted((e['user'], e['ts'], e['id']) for _, e in best.values())
    out = []
    for user, ts, eid in rows:
        if out and out[-1]['user'] == user and ts - out[-1]['end'] <= gap:
            out[-1]['end'] = ts
            out[-1]['ids'].append(eid)
        else:
            out.append(s(user, ts, ts, [eid]))
    return sorted(out, key=lambda x: (x['start'], x['user']))


def generated(n, seed):
    state = seed
    events = []
    for _ in range(n):
        values = []
        for modulus in (8, 3, 13, 3):
            state = (state * 1103515245 + 12345) % 2**31
            values.append((state >> 8) % modulus)
        events.append(ev(f'e{values[0]}', values[2] * 5, values[3] + 1, f'u{values[1]}'))
    return events


# Each expected value below was worked out by hand from the rules in prompt.md.
HAND = {
    'example 1': ([ev('a', 0), ev('b', 50), ev('c', 200), ev('d', 10, user='u2')], 100,
                  [s('u1', 0, 50, ['a', 'b']), s('u2', 10, 10, ['d']), s('u1', 200, 200, ['c'])]),
    'example 2: dedup splits a session': ([ev('a', 0), ev('b', 90), ev('c', 180), ev('b', 300, 2)], 100,
                                          [s('u1', 0, 0, ['a']), s('u1', 180, 180, ['c']), s('u1', 300, 300, ['b'])]),
    'gap exactly equal joins': ([ev('a', 0), ev('b', 100)], 100, [s('u1', 0, 100, ['a', 'b'])]),
    'gap one over splits': ([ev('a', 0), ev('b', 101)], 100, [s('u1', 0, 0, ['a']), s('u1', 101, 101, ['b'])]),
    'chain of exact gaps stays one session': ([ev('d', 30), ev('a', 0), ev('c', 20), ev('b', 10)], 10,
                                              [s('u1', 0, 30, ['a', 'b', 'c', 'd'])]),
    'gap zero keeps equal ts together': ([ev('c', 6), ev('b', 5), ev('a', 5)], 0,
                                         [s('u1', 5, 5, ['a', 'b']), s('u1', 6, 6, ['c'])]),
    'equal seq keeps the last version': ([ev('b', 500, 3), ev('a', 0), ev('b', 60, 3)], 100,
                                         [s('u1', 0, 60, ['a', 'b'])]),
    'equal seq last version decides user': ([ev('x', 0, 2, 'u1'), ev('x', 0, 2, 'u2')], 10,
                                            [s('u2', 0, 0, ['x'])]),
    'higher seq wins even when earlier in input': ([ev('b', 300, 5), ev('a', 0), ev('b', 50, 4)], 100,
                                                   [s('u1', 0, 0, ['a']), s('u1', 300, 300, ['b'])]),
    'lower seq later in input is ignored': ([ev('b', 0, 2), ev('b', 999, 1)], 10, [s('u1', 0, 0, ['b'])]),
    'dedup moves an event to another user': ([ev('a', 0), ev('b', 50), ev('b', 50, 2, 'u2'), ev('c', 120)], 100,
                                             [s('u1', 0, 0, ['a']), s('u2', 50, 50, ['b']), s('u1', 120, 120, ['c'])]),
    'dedup bridges two sessions': ([ev('a', 0), ev('c', 180), ev('b', 300), ev('b', 90, 2)], 100,
                                   [s('u1', 0, 180, ['a', 'b', 'c'])]),
    'equal ts ordered by id': ([ev('b', 10), ev('a', 10)], 5, [s('u1', 10, 10, ['a', 'b'])]),
    'id order is string order': ([ev('9', 7), ev('10', 7)], 0, [s('u1', 7, 7, ['10', '9'])]),
    'equal start ordered by user': ([ev('z', 5, user='zed'), ev('y', 5, user='amy')], 10,
                                    [s('amy', 5, 5, ['y']), s('zed', 5, 5, ['z'])]),
    'sessions ordered by start before user': ([ev('p', 100, user='a'), ev('q', 0, user='b')], 10,
                                              [s('b', 0, 0, ['q']), s('a', 100, 100, ['p'])]),
    'end is the last ts of an equal-ts tail': ([ev('m', 40), ev('k', 0), ev('l', 40)], 50,
                                               [s('u1', 0, 40, ['k', 'l', 'm'])]),
}

CHECKS = [(name, lambda sol, c=case: sol.sessionize(copy.deepcopy(c[0]), c[1]) == c[2]) for name, case in HAND.items()]
CHECKS += [
    ('empty returns []', lambda sol: sol.sessionize([], 0) == []),
    ('negative gap raises', lambda sol: raises(ValueError, sol.sessionize, [ev('a', 0)], -1)),
    ('negative gap raises on empty input', lambda sol: raises(ValueError, sol.sessionize, [], -1)),
]


def not_mutated(sol):
    events = [ev('b', 500, 3), ev('a', 0), ev('b', 60, 3), ev('c', 60, 1, 'u2')]
    before = copy.deepcopy(events)
    sol.sessionize(events, 100)
    return events == before


CHECKS.append(('input not mutated', not_mutated))
for seed, (n, gap) in enumerate([(6, 0), (10, 5), (12, 10), (14, 5), (16, 0), (18, 10), (20, 15), (24, 5)], start=1):
    CHECKS.append((f'generated case {seed}',
                   lambda sol, seed=seed, n=n, gap=gap: sol.sessionize(generated(n, seed), gap) == oracle(generated(n, seed), gap)))


if __name__ == '__main__':
    main(CHECKS)
