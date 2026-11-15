import math

UNITS = [('week', 604800), ('day', 86400), ('hour', 3600), ('minute', 60), ('second', 1)]


def humanize(seconds, max_units=2):
    if max_units < 1 or math.isnan(seconds) or math.isinf(seconds):
        raise ValueError('bad input')
    x = abs(seconds)
    lead = next((i for i, (_, size) in enumerate(UNITS) if size <= x), len(UNITS) - 1)
    step = UNITS[min(lead + max_units, len(UNITS)) - 1][1]
    remaining = round(x / step) * step
    parts = []
    for name, size in UNITS:
        count, remaining = divmod(remaining, size)
        if count:
            parts.append(f'{count} {name}' + ('' if count == 1 else 's'))
    text = ' and '.join(parts) or '0 seconds'
    return 'minus ' + text if seconds < 0 else text
