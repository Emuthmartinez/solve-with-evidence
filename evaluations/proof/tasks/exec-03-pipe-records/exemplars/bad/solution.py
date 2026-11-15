def parse(text):
    records, record, field = [], [], []
    in_quotes = quoted = after_quote = False
    i = 0
    while i < len(text):
        c = text[i]
        if in_quotes:
            if text.startswith('""', i):
                field.append('"')
                i += 2
                continue
            if c == '"':
                in_quotes, after_quote = False, True
            else:
                field.append(c)
            i += 1
            continue
        if c == '|' or c == '\n' or text.startswith('\r\n', i):
            record.append(''.join(field) if quoted else ''.join(field).strip())
            field, quoted, after_quote = [], False, False
            if c == '|':
                i += 1
                continue
            i += 2 if c == '\r' else 1
            if record != ['']:
                records.append(record)
            record = []
            continue
        if after_quote:
            if c not in ' \t':
                raise ValueError(f'unexpected {c!r} after closing quote')
        elif c == '"' and not field:
            in_quotes = quoted = True
        else:
            field.append(c)
        i += 1
    if in_quotes:
        raise ValueError('unterminated quoted field')
    if record or field or quoted:
        record.append(''.join(field) if quoted else ''.join(field).strip())
        if record != ['']:
            records.append(record)
    return records
