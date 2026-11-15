import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises

NAMES = ['week', 'day', 'hour', 'minute', 'second']
SIZES = [604800, 86400, 3600, 60, 1]
CARRY_AT = [None, 7, 24, 60, 60]


def oracle(seconds, max_units=2):
    """Round the last window unit half up, then cascade carries upward one unit at a time."""
    x = abs(Fraction(seconds))
    counts, rest = [], x
    for size in SIZES:
        counts.append(int(rest // size))
        rest -= counts[-1] * size
    lead = next((i for i, c in enumerate(counts) if c), 4)
    last = min(lead + max_units - 1, 4)
    below = sum(counts[i] * SIZES[i] for i in range(last + 1, 5)) + rest
    for i in range(last + 1, 5):
        counts[i] = 0
    if 2 * below >= SIZES[last]:
        counts[last] += 1
    for i in range(last, 0, -1):
        if counts[i] == CARRY_AT[i]:
            counts[i] = 0
            counts[i - 1] += 1
    words = [f"{c} {n}{'s' if c != 1 else ''}" for c, n in zip(counts, NAMES) if c]
    if not words:
        return '0 seconds'
    if len(words) >= 3:
        words = [', '.join(words[:-1]), words[-1]]
    text = ' and '.join(words)
    return f'minus {text}' if seconds < 0 else text


HAND = [
    ((3599.5,), '1 hour'),
    ((93784,), '1 day and 2 hours'),
    ((-90, 1), 'minus 2 minutes'),
    ((0,), '0 seconds'),
    ((1,), '1 second'),
    ((0.5,), '1 second'),
    ((0.25,), '0 seconds'),
    ((0.49999999999999994,), '0 seconds'),
    ((2.5,), '3 seconds'),
    ((4.5, 1), '5 seconds'),
    ((59.5,), '1 minute'),
    ((61.5,), '1 minute and 2 seconds'),
    ((150, 1), '3 minutes'),
    ((89, 1), '1 minute'),
    ((7200.5,), '2 hours'),
    ((615600,), '1 week'),
    ((615600, 3), '1 week and 3 hours'),
    ((694861, 3), '1 week, 1 day and 1 hour'),
    ((694861, 5), '1 week, 1 day, 1 hour, 1 minute and 1 second'),
    ((90061.5, 10), '1 day, 1 hour, 1 minute and 2 seconds'),
    ((604770, 3), '1 week'),
    ((86399.5, 3), '1 day'),
    ((31536000 - 2419200 + 86400,), '48 weeks and 2 days'),
    ((-0.25,), '0 seconds'),
    ((-0.5,), 'minus 1 second'),
    ((-0.0,), '0 seconds'),
    ((-3599.5,), 'minus 1 hour'),
]

SWEEP = [(k / 2, units) for k in range(-9001, 9001, 37) for units in (1, 2, 3)]
SWEEP += [(k * 1800.5, units) for k in range(0, 400, 7) for units in (1, 2, 4, 6)]

CHECKS = [(f'humanize{args}', lambda s, a=args, e=expected: s.humanize(*a) == e) for args, expected in HAND]
CHECKS += [
    ('sweep agrees with oracle', lambda s: all(s.humanize(x, u) == oracle(x, u) for x, u in SWEEP)),
    ('max_units 0 raises', lambda s: raises(ValueError, s.humanize, 5, 0)),
    ('max_units -1 raises', lambda s: raises(ValueError, s.humanize, 5, -1)),
    ('nan raises', lambda s: raises(ValueError, s.humanize, float('nan'))),
    ('inf raises', lambda s: raises(ValueError, s.humanize, float('inf'))),
    ('-inf raises', lambda s: raises(ValueError, s.humanize, float('-inf'))),
]

if __name__ == '__main__':
    main(CHECKS)
