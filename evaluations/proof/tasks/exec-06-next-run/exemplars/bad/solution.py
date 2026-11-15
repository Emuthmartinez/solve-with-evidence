from datetime import datetime, timedelta

BOUNDS = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]


def _field(text, lo, hi):
    values = set()
    for item in text.split(','):
        base, _, step = item.partition('/')
        stride = int(step) if step else 1
        if stride <= 0:
            raise ValueError(item)
        if base == '*':
            candidates = range(0, hi + 1, stride)
        elif '-' in base:
            a, b = (int(x) for x in base.split('-'))
            if a > b:
                raise ValueError(item)
            candidates = range(a, b + 1, stride)
        else:
            candidates = range(int(base), hi + 1, stride) if step else [int(base)]
        for v in candidates:
            if v > hi or (v < lo and base != '*'):
                raise ValueError(item)
            if v >= lo:
                values.add(v)
    return values


def next_run(expr, after):
    fields = expr.split()
    if len(fields) != 5:
        raise ValueError('expected five fields')
    minutes, hours, doms, months, dows = (_field(f, lo, hi) for f, (lo, hi) in zip(fields, BOUNDS))
    dom_any, dow_any = fields[2].startswith('*'), fields[4].startswith('*')
    t = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    limit = after + timedelta(days=3000)
    while t <= limit:
        dom_ok = t.day in doms
        dow_ok = (t.weekday() + 1) % 7 in dows
        if dom_any or dow_any:
            day_ok = dom_ok and dow_ok
        else:
            day_ok = dom_ok or dow_ok
        if t.month in months and day_ok:
            if t.hour in hours and t.minute in minutes:
                return t
            t += timedelta(minutes=1)
        else:
            t = datetime(t.year, t.month, t.day) + timedelta(days=1)
    return None
