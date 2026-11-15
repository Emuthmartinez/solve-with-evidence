BLANK = ' \t'


def _line_break(text, i):
    """Length of the line break starting at i, or 0."""
    if text.startswith('\n', i):
        return 1
    if text.startswith('\r\n', i):
        return 2
    return 0


def _field(text, i):
    """Parse one field starting at i. Return (value, index just past it)."""
    n = len(text)
    j = i
    while j < n and text[j] in BLANK:
        j += 1
    if j < n and text[j] == '"':
        j += 1
        value = []
        while True:
            if j >= n:
                raise ValueError('unterminated quoted field')
            if text.startswith('""', j):
                value.append('"')
                j += 2
            elif text[j] == '"':
                j += 1
                break
            else:
                value.append(text[j])
                j += 1
        while j < n and text[j] in BLANK:
            j += 1
        if j < n and text[j] != '|' and not _line_break(text, j):
            raise ValueError(f'unexpected {text[j]!r} after closing quote')
        return ''.join(value), j
    while j < n and text[j] != '|' and not _line_break(text, j):
        j += 1
    return text[i:j].strip(BLANK), j


def parse(text):
    records = []
    i, n = 0, len(text)
    while i < n:
        skip = _line_break(text, i)
        if skip:
            i += skip
            continue
        record = []
        while True:
            value, i = _field(text, i)
            record.append(value)
            if i < n and text[i] == '|':
                i += 1
                continue
            i += _line_break(text, i)
            break
        records.append(record)
    return records
