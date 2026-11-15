import re
from datetime import datetime, time, timedelta

BOUNDS = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
HORIZON = timedelta(days=3000)
NUMBER = re.compile(r'[0-9]+')


def _number(text, lo, hi):
    if not NUMBER.fullmatch(text):
        raise ValueError(f'not a number: {text!r}')
    value = int(text)
    if not lo <= value <= hi:
        raise ValueError(f'{value} outside {lo}-{hi}')
    return value


def _field(text, lo, hi):
    values = set()
    for item in text.split(','):
        base, slash, step = item.partition('/')
        if base == '*':
            start, end = lo, hi
        elif '-' in base:
            a, _, b = base.partition('-')
            start, end = _number(a, lo, hi), _number(b, lo, hi)
            if start > end:
                raise ValueError(f'reversed range: {base!r}')
        elif slash:
            raise ValueError(f'step needs * or a range: {item!r}')
        else:
            start = end = _number(base, lo, hi)
        stride = 1
        if slash:
            if not NUMBER.fullmatch(step) or int(step) == 0:
                raise ValueError(f'bad step: {item!r}')
            stride = int(step)
        values.update(range(start, end + 1, stride))
    return values


def next_run(expr, after):
    fields = expr.split()
    if len(fields) != 5:
        raise ValueError('expected five fields')
    minutes, hours, doms, months, dows = (_field(f, lo, hi) for f, (lo, hi) in zip(fields, BOUNDS))
    dows = {d % 7 for d in dows}
    dom_restricted, dow_restricted = fields[2] != '*', fields[4] != '*'
    times = sorted(time(h, m) for h in hours for m in minutes)

    def day_matches(day):
        if day.month not in months:
            return False
        dom_ok = day.day in doms
        dow_ok = (day.weekday() + 1) % 7 in dows
        if dom_restricted and dow_restricted:
            return dom_ok or dow_ok
        return (dom_ok or not dom_restricted) and (dow_ok or not dow_restricted)

    start = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    limit = after + HORIZON
    day = start.date()
    while datetime.combine(day, time()) <= limit:
        if day_matches(day):
            for t in times:
                candidate = datetime.combine(day, t)
                if candidate >= start:
                    return candidate if candidate <= limit else None
        day += timedelta(days=1)
    return None
