"""Plausible mistakes for exec-01-bank-import. Each is the good exemplar with one edit."""
READER = 'importer/reader.py'
MONEY = 'importer/money.py'
KEEP = ("    return [transaction for transaction, _ in parsed\n"
        "            if transaction.status == 'booked' or transaction.reference not in booked]\n")
MATCH = "    match = NUMBER.fullmatch(text)\n    if not match:\n"
LIMITS = "    if decimals > currencies[currency] or digits > MAX_DIGITS:\n"
TO_MINOR = "int(worth * 10 ** currencies[currency])"
COUNT = "    if not re.fullmatch('[0-9]+', count) or int(count) != len(records):\n"
HASH = "    if number(total)[0] != sum(worth for _, worth in parsed):\n"
READ = "    rows = read_rows(path)\n"
FIELD = "FIELD = re.compile(r'(?:\"((?:[^\"]|\"\")*)\"|([^\";\\r\\n]*))(;|\\r?\\n|\\Z)')\n"
DECODE = ("    try:\n        text = data.decode('utf-8-sig')\n    except UnicodeDecodeError:\n"
          "        raise FormatError('the file is not UTF-8') from None\n")
SPLIT = ("    rows, row, position = [], [], 0\n"
         "    while position < len(text) or row:\n"
         "        match = FIELD.match(text, position)\n"
         "        if not match:\n"
         "            raise FormatError(f'misplaced double quote or line end at character {position}')\n"
         "        quoted, plain, end = match.groups()\n"
         "        row.append(plain if quoted is None else quoted.replace('\"\"', '\"'))\n"
         "        position = match.end()\n"
         "        if end != ';':\n"
         "            rows.append(row)\n"
         "            row = []\n"
         "    return rows\n")
CSV_MODULE = ("    import csv\n    import io\n"
              "    return list(csv.reader(io.StringIO(text, newline=''), delimiter=';'))\n")
QUOTING = 'a double quote outside the quoting rules is an error'
LONE_CR = 'a line that ends in CR alone is an error'
SUPERSEDED = ['the sample loads', 'the trailer counts and adds superseded records',
              'a pending record superseded by a later booked one is dropped',
              'a pending record superseded by an earlier booked one is dropped']

VARIANTS = [
    ('parse_amount switched to the bank notation in place',
     {MONEY: '"""Amounts as integer minor units."""\n\n\n'
             'def parse_amount(text, exponent=2):\n'
             '    sign = -1 if text.endswith(\'-\') else 1\n'
             '    return sign * round(float(text.rstrip(\'-\').replace(\'.\', \'\').replace(\',\', \'.\')) * 10 ** exponent)\n'},
     ['english adjustments still parse']),
    ('amounts converted through float',
     {READER: [(TO_MINOR, "round(float(worth) * 10 ** currencies[currency])")]},
     ['an 18-digit amount converts exactly']),
    ('the hash total compared as floats',
     {READER: [(HASH, "    if float(number(total)[0]) != float(sum(worth for _, worth in parsed)):\n")]},
     ['the hash total is compared exactly']),
    ('the hash total compared in minor units',
     {READER: [(HASH, "    if number(total)[0] * 100 != sum(transaction.amount_minor for transaction, _ in parsed):\n")]},
     ['the sample loads', 'the hash total adds amounts across currencies', 'a dot groups thousands in every currency',
      'missing decimals are zeros']),
    ('a dot read as the decimal mark when there is no comma',
     {READER: [("    decimals = decimals or ''\n",
                "    if decimals is None and '.' in whole:\n        whole, decimals = whole.rsplit('.', 1)\n"
                "    decimals = decimals or ''\n")]},
     ['the sample loads', 'the hash total adds amounts across currencies', 'a dot groups thousands in every currency']),
    ('dots dropped wherever they are',
     {READER: [("r'([0-9]{1,3}(?:\\.[0-9]{3})+|[0-9]+)", "r'([0-9][0-9.]*)")]},
     ['a misplaced dot is an error']),
    ('a sign before the number accepted',
     {READER: [(MATCH, "    text = text[1:] + '-' if text.startswith('-') else text.lstrip('+')\n" + MATCH)]},
     ['a sign before the number is an error']),
    ('no limit on digits',
     {READER: [(LIMITS, "    if decimals > currencies[currency]:\n")]},
     ['more than 18 digits is an error']),
    ('no limit on decimals',
     {READER: [(LIMITS, "    if digits > MAX_DIGITS:\n")]},
     ['more decimals than the currency allows is an error']),
    ('every decimal of the currency required',
     {READER: [(LIMITS, "    if decimals != currencies[currency] or digits > MAX_DIGITS:\n")]},
     ['missing decimals are zeros', 'a dot groups thousands in every currency']),
    ('a booked record drops only the pending records before it',
     {READER: [(KEEP, "    kept = []\n    for transaction, _ in parsed:\n"
                      "        if transaction.status == 'booked':\n"
                      "            kept = [t for t in kept if t.reference != transaction.reference]\n"
                      "        kept.append(transaction)\n    return kept\n")]},
     ['the sample loads', 'a pending record superseded by an earlier booked one is dropped']),
    ('a booked record drops only the pending records after it',
     {READER: [(KEEP, "    kept, done = [], set()\n    for transaction, _ in parsed:\n"
                      "        if transaction.status == 'booked':\n            done.add(transaction.reference)\n"
                      "        if transaction.status == 'booked' or transaction.reference not in done:\n"
                      "            kept.append(transaction)\n    return kept\n")]},
     ['the sample loads', 'a pending record superseded by a later booked one is dropped',
      'the trailer counts and adds superseded records']),
    ('pending records dropped',
     {READER: [(KEEP, "    return [transaction for transaction, _ in parsed if transaction.status == 'booked']\n")]},
     ['the sample loads', 'a pending record never booked is kept in file order']),
    ('unbooked pending records appended after the booked ones',
     {READER: [(KEEP, "    return ([transaction for transaction, _ in parsed if transaction.status == 'booked']\n"
                      "            + [transaction for transaction, _ in parsed\n"
                      "               if transaction.status == 'pending' and transaction.reference not in booked])\n")]},
     ['the sample loads', 'a pending record never booked is kept in file order']),
    ('a repeated reference allowed',
     {READER: [("            raise FormatError(f'{transaction.status} reference {transaction.reference!r} occurs twice')\n",
                "            pass\n")]},
     ['a reference twice with one status is an error']),
    ('a file without a trailer read as all records',
     {READER: [("    if len(rows) < 2 or rows[-1][:1] != ['T'] or len(rows[-1]) != 3:\n"
                "        raise FormatError('no trailer: the file is truncated')\n",
                "    if rows[-1][:1] != ['T']:\n        return [parse_record(fields, currencies)[0] for fields in rows[1:]]\n")]},
     ['a missing trailer is an error']),
    ('the record count not checked',
     {READER: [(COUNT, "    if not re.fullmatch('[0-9]+', count):\n")]},
     ['a wrong record count is an error', 'the trailer counts and adds superseded records']),
    ('the record count compared with the records kept',
     {READER: [(COUNT, "    kept = [t for t, _ in parsed if t.status == 'booked'\n"
                       "            or (t.reference, 'booked') not in {(u.reference, u.status) for u, _ in parsed}]\n"
                       "    if not re.fullmatch('[0-9]+', count) or int(count) != len(kept):\n")]},
     SUPERSEDED),
    ('the hash total not checked',
     {READER: [(HASH, "    if False:\n")]},
     ['the hash total is compared exactly', 'a wrong hash total is an error',
      'the trailer counts and adds superseded records']),
    ('the hash total adds the records kept',
     {READER: [(HASH, "    refs = {t.reference for t, _ in parsed if t.status == 'booked'}\n"
                      "    if number(total)[0] != sum(w for t, w in parsed if t.status == 'booked' or t.reference not in refs):\n")]},
     SUPERSEDED),
    ('the hash total adds amounts without their sign',
     {READER: [(HASH, "    if number(total)[0] != sum(abs(worth) for _, worth in parsed):\n")]},
     ['the sample loads', 'the hash total adds amounts across currencies',
      'missing decimals are zeros', 'a pending record superseded by a later booked one is dropped',
      'a pending record superseded by an earlier booked one is dropped', 'a pending record never booked is kept in file order',
      'a wrong hash total is an error', 'the trailer counts and adds superseded records']),
    ('empty lines skipped',
     {READER: [(READ, "    rows = [row for row in read_rows(path) if row != ['']]\n")]},
     ['nothing may follow the trailer']),
    ('fields split on every semicolon',
     {READER: [(SPLIT, "    lines = re.split('\\r?\\n', text)\n"
                       "    return [line.split(';') for line in (lines if lines[-1] else lines[:-1])]\n")]},
     ['the sample loads', 'a quoted memo keeps its semicolon and quotes', 'a memo with a line break is one record', QUOTING]),
    ('one record per physical line',
     {READER: [(FIELD, FIELD.replace('[^\"]|', '[^\"\\n]|'))]},
     ['the sample loads', 'a memo with a line break is one record']),
    ('the first character always taken for a byte-order mark',
     {READER: [("data.decode('utf-8-sig')", "data.decode('utf-8')[1:]")]},
     ['a file without byte-order mark or CR loads', 'an export with no records loads as an empty list']),
    ('an empty value date rejected',
     {READER: [("parse_date(value) if value else None", "parse_date(value)")]},
     ['the sample loads', 'a pending record superseded by a later booked one is dropped',
      'a pending record superseded by an earlier booked one is dropped', 'a pending record never booked is kept in file order',
      'the trailer counts and adds superseded records', 'an empty value date is None']),
    ('an impossible date raises ValueError, not FormatError',
     {READER: [("    except (AttributeError, ValueError):\n", "    except AttributeError:\n")]},
     ['an impossible date is an error']),
    ('any status other than B taken as pending',
     {READER: [("    if status not in STATUSES:\n        raise FormatError(f'unknown status {status!r}')\n", ""),
               ("STATUSES[status]", "STATUSES.get(status, 'pending')")]},
     ['an unknown status is an error']),
    ('bytes that are not UTF-8 raise UnicodeDecodeError, not FormatError',
     {READER: [(DECODE, "    text = data.decode('utf-8-sig')\n")]},
     ['a file that is not UTF-8 is an error']),
    ('bytes that are not UTF-8 replaced and the file imported',
     {READER: [("data.decode('utf-8-sig')", "data.decode('utf-8-sig', errors='replace')")]},
     ['a file that is not UTF-8 is an error']),
    ('the file read with the csv module, which forgives a stray quote and takes a lone CR for a line end',
     {READER: [(SPLIT, CSV_MODULE)]},
     [QUOTING, LONE_CR]),
    ('the csv module in strict mode, which still allows a quote in a field that is not quoted',
     {READER: [(SPLIT, CSV_MODULE.replace("delimiter=';'", "delimiter=';', strict=True")),
               (READ, "    try:\n        rows = read_rows(path)\n    except Exception as exc:\n"
                      "        raise FormatError(str(exc)) from None\n")]},
     [QUOTING, LONE_CR]),
    ('a double quote allowed in a field that is not quoted',
     {READER: [(FIELD, FIELD.replace('[^\";', '[^;'))]},
     [QUOTING]),
    ('a lone CR taken for a line end',
     {READER: [(FIELD, FIELD.replace('\\r?\\n', '\\r\\n?|\\n'))]},
     [LONE_CR]),
    ('a file needs at least one record',
     {READER: [("    if len(rows) < 2 or rows", "    if len(rows) < 3 or rows")]},
     ['an export with no records loads as an empty list']),
]
