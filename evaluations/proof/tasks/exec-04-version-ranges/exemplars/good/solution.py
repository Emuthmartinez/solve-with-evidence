import re

NUM = r'0|[1-9][0-9]*'
DOTTED = r'[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*'
VERSION = re.compile(rf'({NUM})\.({NUM})\.({NUM})(?:-({DOTTED}))?(?:\+{DOTTED})?')
PART = rf'{NUM}|[xX*]'
PARTIAL = re.compile(rf'({PART})(?:\.({PART}))?(?:\.({PART}))?(?:-({DOTTED}))?(\+{DOTTED})?')
OPERATORS = ('>=', '<=', '>', '<', '=', '~', '^')


def _key(nums, pre):
    """Sortable key: a release sorts above every prerelease of the same core."""
    if pre is None:
        return (*nums, (1,))
    ids = pre.split('.')
    if any(i.isdigit() and len(i) > 1 and i[0] == '0' for i in ids):
        raise ValueError(f'numeric prerelease identifier with leading zero: {pre!r}')
    return (*nums, (0, *[(0, int(i)) if i.isdigit() else (1, i) for i in ids]))


def _pad(nums):
    return tuple(nums) + (0,) * (3 - len(nums))


def _partial(text):
    """Return (N, pre) for a partial version."""
    m = PARTIAL.fullmatch(text)
    if not m:
        raise ValueError(f'invalid partial version: {text!r}')
    parts = [p for p in m.group(1, 2, 3) if p is not None]
    nums = []
    for part in parts:
        if part in 'xX*':
            break
        nums.append(int(part))
    if any(p not in 'xX*' for p in parts[len(nums):]):
        raise ValueError(f'number after wildcard: {text!r}')
    if (m.group(4) or m.group(5)) and len(nums) < 3:
        raise ValueError(f'prerelease or build on a partial version: {text!r}')
    return tuple(nums), m.group(4)


def _bounds(op, nums, pre):
    """Translate one term into (comparison, key) bounds."""
    if not nums:
        if op in ('', '='):
            return []
        raise ValueError('operator needs a numeric version')
    floor = _key(_pad(nums), pre)
    full = len(nums) == 3
    ceiling = None if full else _key(_pad(nums[:-1] + (nums[-1] + 1,)), None)
    if op in ('', '='):
        return [('>=', floor), ('<=', floor)] if full else [('>=', floor), ('<', ceiling)]
    if op == '>=':
        return [('>=', floor)]
    if op == '>':
        return [('>', floor)] if full else [('>=', ceiling)]
    if op == '<':
        return [('<', floor)]
    if op == '<=':
        return [('<=', floor)] if full else [('<', ceiling)]
    if op == '~':
        upper = (nums[0], nums[1] + 1, 0) if len(nums) >= 2 else (nums[0] + 1, 0, 0)
    else:
        i = next((i for i, n in enumerate(nums) if n), len(nums) - 1)
        upper = _pad(nums[:i] + (nums[i] + 1,))
    return [('>=', floor), ('<', _key(upper, None))]


def _parse_set(text):
    """Return (bounds, cores of prerelease partials written in this set)."""
    tokens = [t for t in text.split(' ') if t]
    if not tokens:
        raise ValueError('empty set')
    bounds, cores = [], set()

    def operand(token, allow_operator):
        op = next((o for o in OPERATORS if token.startswith(o)), '') if allow_operator else ''
        nums, pre = _partial(token[len(op):])
        if pre is not None:
            cores.add(nums)
        return op, nums, pre

    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and tokens[i + 1] == '-':
            if i + 2 >= len(tokens):
                raise ValueError('hyphen range without an upper end')
            _, low, low_pre = operand(tokens[i], False)
            _, high, high_pre = operand(tokens[i + 2], False)
            bounds += _bounds('>=', low, low_pre) + _bounds('<=', high, high_pre)
            i += 3
        elif tokens[i] == '-':
            raise ValueError('misplaced hyphen')
        else:
            bounds += _bounds(*operand(tokens[i], True))
            i += 1
    return bounds, cores


def satisfies(version, spec):
    m = VERSION.fullmatch(version)
    if not m:
        raise ValueError(f'invalid version: {version!r}')
    core = tuple(int(g) for g in m.group(1, 2, 3))
    key = _key(core, m.group(4))
    tests = {'>=': key.__ge__, '>': key.__gt__, '<': key.__lt__, '<=': key.__le__}
    sets = [_parse_set(text) for text in spec.split('||')]
    return any(all(tests[op](bound) for op, bound in bounds) and (m.group(4) is None or core in cores)
               for bounds, cores in sets)
