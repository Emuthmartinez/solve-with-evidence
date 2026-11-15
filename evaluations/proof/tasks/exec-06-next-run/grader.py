import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises

D = datetime
LOWS = [0, 0, 1, 1, 0]
LIMIT_S = 1.0  # rule 9 says "well under one second"; one second is the only number it states


def _item_test(item, low):
    base, _, step = item.partition('/')
    stride = int(step) if step else 1
    if base == '*':
        return lambda v: (v - low) % stride == 0
    a, _, b = base.partition('-')
    a = int(a)
    b = int(b) if b else a
    return lambda v: a <= v <= b and (v - a) % stride == 0


def _field_test(text, low):
    tests = [_item_test(item, low) for item in text.split(',')]
    return lambda v: any(t(v) for t in tests)


def oracle(expr, after):
    """Independent scan: day by day, then minute by minute inside a matching day."""
    f = expr.split()
    minute, hour, dom, month, dow = (_field_test(text, low) for text, low in zip(f, LOWS))

    def day_ok(t):
        if not month(t.month):
            return False
        weekday = (t.weekday() + 1) % 7
        dom_hit = dom(t.day)
        dow_hit = dow(weekday) or (weekday == 0 and dow(7))
        if f[2] != '*' and f[4] != '*':
            return dom_hit or dow_hit
        return (f[2] == '*' or dom_hit) and (f[4] == '*' or dow_hit)

    t = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    end = after + timedelta(days=3000)
    while t <= end:
        if not day_ok(t):
            t = D(t.year, t.month, t.day) + timedelta(days=1)
        elif not hour(t.hour):
            t = D(t.year, t.month, t.day, t.hour) + timedelta(hours=1)
        elif minute(t.minute):
            return t
        else:
            t += timedelta(minutes=1)
    return None


def timed(s, expr, after):
    """Rule 9, for calls that return a time and calls that return None. A slow call is tried once
    more, so a stall on a busy machine is not charged to the solution."""
    for _ in range(2):
        started = time.perf_counter()
        found = s.next_run(expr, after)
        if time.perf_counter() - started < LIMIT_S:
            return found
    raise TimeoutError(f'next_run took {LIMIT_S} s or longer, twice')


def agrees(expr, after):
    return lambda s: timed(s, expr, after) == oracle(expr, after)


def equals(expr, after, expected):
    return lambda s: timed(s, expr, after) == expected


NOON = D(2026, 11, 15, 12, 0)  # a Sunday

HAND = [
    ('example weekday skip', '30 9 * * 1-5', D(2026, 11, 13, 9, 30), D(2026, 11, 16, 9, 30)),
    ('example dom or dow', '0 0 13 * 5', D(2026, 11, 14), D(2026, 11, 20)),
    ('example never', '0 0 30 2 *', D(2026, 1, 1), None),
    ('seconds and microseconds dropped', '* * * * *', D(2026, 11, 15, 10, 0, 30, 500000), D(2026, 11, 15, 10, 1)),
    ('exclusive after a microsecond', '0 10 * * *', D(2026, 11, 15, 10, 0, 0, 1), D(2026, 11, 16, 10, 0)),
    ('day-of-month step starts at 1', '0 0 */7 * *', D(2026, 11, 15), D(2026, 11, 22)),
    ('month step starts at 1', '0 12 * */5 *', D(2026, 11, 15, 12, 0), D(2026, 11, 16, 12, 0)),
    ('dow 7 is Sunday', '0 0 * * 7', D(2026, 11, 14), D(2026, 11, 15)),
    ('dow range ending at 7', '0 0 * * 5-7', D(2026, 11, 14, 1, 0), D(2026, 11, 15)),
    ('*/2 day field is restricted', '0 0 */2 * 1', D(2026, 11, 16), D(2026, 11, 17)),
    ('*/1 dow is restricted', '0 0 1 * */1', NOON, D(2026, 11, 16)),
    ('both restricted with month', '0 0 30 2 1', NOON, D(2027, 2, 1)),
    ('leap day', '0 0 29 2 *', D(2023, 3, 1), D(2024, 2, 29)),
    ('leap day from a leap day', '0 0 29 2 *', D(2024, 2, 29), D(2028, 2, 29)),
    ('2000 is a leap year', '0 0 29 2 *', D(1999, 3, 1), D(2000, 2, 29)),
    ('2100 is not a leap year', '0 0 29 2 *', D(2096, 3, 1), D(2104, 2, 29)),
    ('31st of short months never', '0 0 31 4,6,9,11 *', NOON, None),
    ('year rollover', '59 23 31 12 *', D(2026, 12, 31, 23, 59), D(2027, 12, 31, 23, 59)),
]

AGREE = [
    ('quarter hours', '*/15 * * * *', D(2026, 11, 15, 10, 45)),
    ('range step', '10-50/15 * * * *', D(2026, 11, 15, 10, 40)),
    ('list of items', '5,10-12,*/20 7 * * *', D(2026, 11, 15, 7, 12)),
    ('step larger than range', '*/100 */5 * * *', D(2026, 11, 15, 20, 1)),
    ('late evening rollover', '30 23 * * *', D(2026, 11, 15, 23, 30)),
    ('only day of month restricted', '0 0 13 * *', NOON),
    ('only day of week restricted', '0 6 * * 1,3', NOON),
    ('next Friday or the 13th', '0 0 13 * 5', D(2026, 11, 20)),
    ('full ranges', '0-59 0-23 1-31 1-12 0-7', NOON),
]

INVALID = [
    ('four fields', '* * * *'),
    ('six fields', '* * * * * *'),
    ('minute 60', '60 * * * *'),
    ('hour 24', '* 24 * * *'),
    ('day 0', '* * 0 * *'),
    ('month 13', '* * * 13 *'),
    ('dow 8', '* * * * 8'),
    ('zero step', '*/0 * * * *'),
    ('reversed range', '* * * * 5-1'),
    ('step after a single value', '5/15 * * * *'),
    ('empty item', '1,,2 * * * *'),
    ('negative value', '-1 * * * *'),
    ('day name', '* * * * MON'),
]

CHECKS = [(name, equals(expr, after, expected)) for name, expr, after, expected in HAND]
CHECKS += [(name, agrees(expr, after)) for name, expr, after in AGREE]
CHECKS += [(f'raises: {name}', lambda s, e=expr: raises(ValueError, s.next_run, e, NOON)) for name, expr in INVALID]

if __name__ == '__main__':
    main(CHECKS)
