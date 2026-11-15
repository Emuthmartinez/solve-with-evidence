import math
from fractions import Fraction

UNITS = [('week', 604800), ('day', 86400), ('hour', 3600), ('minute', 60), ('second', 1)]


def humanize(seconds, max_units=2):
    if max_units < 1:
        raise ValueError('max_units must be at least 1')
    if math.isnan(seconds) or math.isinf(seconds):
        raise ValueError('seconds must be finite')
    x = abs(Fraction(seconds))
    lead = next((i for i, (_, size) in enumerate(UNITS) if size <= x), len(UNITS) - 1)
    step = UNITS[min(lead + max_units, len(UNITS)) - 1][1]
    remaining = math.floor(x / step + Fraction(1, 2)) * step
    parts = []
    for name, size in UNITS:
        count, remaining = divmod(remaining, size)
        if count:
            parts.append(f'{count} {name}' + ('' if count == 1 else 's'))
    if not parts:
        return '0 seconds'
    text = parts[0] if len(parts) == 1 else ', '.join(parts[:-1]) + ' and ' + parts[-1]
    return 'minus ' + text if seconds < 0 else text
