import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises

BIG = 10**30 + 1


def exact(a, total, weights):
    # Look the answer up first: the solution gets a list of its own and may change it.
    expected = REFERENCE[(total, weights)]
    return a(total, list(weights)) == expected


REFERENCE = {
    (100, (1, 1, 1)): [34, 33, 33],
    (10, (3, 0, 7)): [3, 0, 7],
    (-100, (1, 1, 1)): [-34, -33, -33],
    (0, (5, 5)): [0, 0],
    (1, (0, 0, 0)): [1, 0, 0],
    (5, (0, 0)): [3, 2],
    (2, (1, 1, 1, 0)): [1, 1, 0, 0],
    # Equal remainders (both shares end in .5): the larger weight wins the cent.
    (2, (1, 3)): [0, 2],
    (6, (1, 3)): [1, 5],
    (-6, (1, 3)): [-1, -5],
    (3, (1, 3)): [1, 2],
    (1, (1, 1)): [1, 0],
    (-1, (1, 2)): [0, -1],
    (BIG, (1, 1, 1)): [BIG // 3 + 1, BIG // 3 + 1, BIG // 3],
    (BIG, (0, 7, 0)): [0, BIG, 0],
    (10**18 + 3, (1, 2)): [(10**18 + 3) // 3, 2 * (10**18 + 3) // 3 + 1],
    (99, (50, 30, 20)): [49, 30, 20],
    (101, (50, 30, 20)): [51, 30, 20],
}

CHECKS = [(f'allocate{key}', lambda s, key=key: exact(s.allocate, *key)) for key in REFERENCE]
CHECKS += [
    ('empty zero', lambda s: s.allocate(0, []) == []),
    ('empty nonzero raises', lambda s: raises(ValueError, s.allocate, 5, [])),
    ('negative weight raises', lambda s: raises(ValueError, s.allocate, 5, [1, -1])),
    ('negative weight raises on zero total', lambda s: raises(ValueError, s.allocate, 0, [-1])),
    ('returns ints', lambda s: all(type(x) is int for x in s.allocate(100, [1, 2, 3]))),
]

if __name__ == '__main__':
    main(CHECKS)
