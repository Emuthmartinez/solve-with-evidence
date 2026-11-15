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
READ = "        rows = list(csv.reader(file, delimiter=';'))\n"
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
     {READER: [(READ, "        rows = [row for row in csv.reader(file, delimiter=';') if row]\n")]},
     ['nothing may follow the trailer']),
    ('fields split on every semicolon',
     {READER: [(READ, "        rows = list(csv.reader(file, delimiter=';', quoting=csv.QUOTE_NONE))\n")]},
     ['the sample loads', 'a quoted memo keeps its semicolon and quotes', 'a memo with a line break is one record']),
    ('one record per physical line',
     {READER: [(READ, "        rows = [list(csv.reader([line], delimiter=';'))[0] for line in file.read().splitlines()]\n")]},
     ['the sample loads', 'a memo with a line break is one record']),
    ('the first character always taken for a byte-order mark',
     {READER: [("    with open(path, encoding='utf-8-sig', newline='') as file:\n" + READ,
                "    with open(path, encoding='utf-8', newline='') as file:\n"
                "        rows = list(csv.reader(file.read()[1:].splitlines(True), delimiter=';'))\n")]},
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
    ('a file needs at least one record',
     {READER: [("    if len(rows) < 2 or rows", "    if len(rows) < 3 or rows")]},
     ['an export with no records loads as an empty list']),
]
