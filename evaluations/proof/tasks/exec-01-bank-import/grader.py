import atexit
import hashlib
import importlib
import itertools
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises

HERE = Path(__file__).resolve().parent
SAMPLE = HERE / 'workspace' / 'data' / 'export-sample.csv'
# load(SAMPLE) from the good exemplar: 148 records, repr of their tuples hashed.
SAMPLE_RECORDS = 148
SAMPLE_SHA256 = 'aceeb53d7a4a81ca6831736457f0d0a486555380c69cf8213ed508217f85a177'
HEADER = 'Booking date;Value date;Reference;Status;Amount;Currency;Memo'
DAY = date(2026, 3, 12)
TMP = Path(tempfile.mkdtemp(prefix='bank-import-grader-'))
atexit.register(shutil.rmtree, TMP, True)
NAMES = itertools.count()


def export(*lines, eol='\r\n', bom=True, last_eol=True):
    """Write an export file with the header and these lines into the grader's own folder."""
    text = eol.join((HEADER,) + lines) + (eol if last_eol else '')
    path = TMP / f'export-{next(NAMES)}.csv'
    path.write_bytes((('﻿' if bom else '') + text).encode('utf-8'))
    return str(path)


def record(reference, amount, currency='EUR', status='B', memo='Card payment', value='12.03.2026',
           booking='12.03.2026'):
    return ';'.join([booking, value, reference, status, amount, currency, memo])


def tx(reference, minor, currency='EUR', status='booked', memo='Card payment', value=DAY):
    return (DAY, value, reference, status, minor, currency, memo)


def loads(s, path):
    return [tuple(transaction) for transaction in s.load(path)]


def rejects(s, *paths):
    return all(raises(s.FormatError, s.load, path) for path in paths)


def sample(s):
    rows = loads(s, str(SAMPLE))
    return len(rows) == SAMPLE_RECORDS and hashlib.sha256(repr(rows).encode()).hexdigest() == SAMPLE_SHA256


def english_adjustments(s):
    parse = importlib.import_module('importer.statement').parse_adjustment
    return (parse('1,234.56 EUR') == (123456, 'EUR') and parse('12.5 EUR') == (1250, 'EUR')
            and parse('-12.5 EUR') == (-1250, 'EUR'))


def eighteen_digits(s):
    path = export(record('R1', '9.999.999.999.999.999,99'), 'T;1;9.999.999.999.999.999,99')
    return loads(s, path) == [tx('R1', 999999999999999999)]


def exact_hash(s):
    # The true total is 9.999.999.999.999.999,98. As floats the two totals are equal.
    return rejects(s, export(record('R1', '9.999.999.999.999.999,99'), record('R2', '0,01-'),
                             'T;2;9.999.999.999.999.999,99'))


def hash_across_currencies(s):
    path = export(record('R1', '2,75'), record('R2', '12.000', 'JPY'), record('R3', '1,500-', 'KWD'), 'T;3;12.001,25')
    return loads(s, path) == [tx('R1', 275), tx('R2', 12000, 'JPY'), tx('R3', -1500, 'KWD')]


def jpy_grouping(s):
    path = export(record('R1', '1.234', 'JPY'), record('R2', '1.234,5', 'KWD'), 'T;2;2.468,5')
    return loads(s, path) == [tx('R1', 1234, 'JPY'), tx('R2', 1234500, 'KWD')]


def missing_decimals(s):
    path = export(record('R1', '7'), record('R2', '7,5'), record('R3', '1,5-', 'KWD'), 'T;3;13')
    return loads(s, path) == [tx('R1', 700), tx('R2', 750), tx('R3', -1500, 'KWD')]


def too_many_decimals(s):
    return rejects(s, export(record('R1', '1,234'), 'T;1;1,234'), export(record('R1', '1,5', 'JPY'), 'T;1;1,5'))


def misplaced_dots(s):
    # Each trailer matches the amount read with its dots dropped.
    return rejects(s, export(record('R1', '12.34'), 'T;1;1.234'),
                   export(record('R1', '1234.567,00'), 'T;1;1.234.567'))


def leading_sign(s):
    return rejects(s, export(record('R1', '-5,00'), 'T;1;5,00-'), export(record('R1', '+5,00'), 'T;1;5'))


def too_many_digits(s):
    return rejects(s, export(record('R1', '99.999.999.999.999.999,99'), 'T;1;99.999.999.999.999.999,99'))


def superseded_by_later(s):
    path = export(record('R1', '50,00-', status='P', value=''), record('R2', '10,00'), record('R1', '47,30-'),
                  'T;3;87,30-')
    return loads(s, path) == [tx('R2', 1000), tx('R1', -4730)]


def superseded_by_earlier(s):
    path = export(record('R1', '47,30-'), record('R1', '50,00-', status='P', value=''), record('R2', '10,00'),
                  'T;3;87,30-')
    return loads(s, path) == [tx('R1', -4730), tx('R2', 1000)]


def pending_kept(s):
    path = export(record('R9', '20,00-', status='P', value=''), record('R1', '5,00'), record('R2', '6,00-'),
                  'T;3;21,00-')
    return loads(s, path) == [tx('R9', -2000, status='pending', value=None), tx('R1', 500), tx('R2', -600)]


def repeated_reference(s):
    return rejects(s, export(record('R1', '1,00'), record('R1', '2,00'), 'T;2;3,00'),
                   export(record('R1', '1,00', status='P'), record('R1', '2,00', status='P'), 'T;2;3,00'))


def missing_trailer(s):
    return rejects(s, export(record('R1', '1,00'), record('R2', '2,00')), export())


def wrong_count(s):
    return rejects(s, export(record('R1', '1,00'), record('R2', '2,00'), 'T;3;3,00'),
                   export(record('R1', '1,00'), record('R2', '2,00'), 'T;1;3,00'))


def wrong_hash(s):
    return rejects(s, export(record('R1', '1,00'), record('R2', '2,00'), 'T;2;3,01'),
                   export(record('R1', '1,00'), record('R2', '2,00-'), 'T;2;3,00'))


def after_trailer(s):
    return rejects(s, export(record('R1', '1,00'), 'T;1;1,00', record('R2', '2,00')),
                   export(record('R1', '1,00'), 'T;1;1,00', ''))


def superseded_in_trailer(s):
    lines = (record('R1', '50,00-', status='P', value=''), record('R1', '47,30-'))
    return (loads(s, export(*lines, 'T;2;97,30-')) == [tx('R1', -4730)]
            and rejects(s, export(*lines, 'T;1;97,30-'), export(*lines, 'T;2;47,30-')))


def quoted_memo(s):
    path = export(record('R1', '1,00', memo='"Invoice ""A-7""; final"'), 'T;1;1,00')
    return loads(s, path) == [tx('R1', 100, memo='Invoice "A-7"; final')]


def multiline_memo(s):
    path = export(record('R1', '1,00', memo='"Standing order 0042\nRent office"'), record('R2', '2,00'), 'T;2;3,00')
    return loads(s, path) == [tx('R1', 100, memo='Standing order 0042\nRent office'), tx('R2', 200)]


def plain_file(s):
    lines = (record('R1', '1,00'), record('R2', '2,00'), 'T;2;3,00')
    expected = [tx('R1', 100), tx('R2', 200)]
    return (loads(s, export(*lines, eol='\n', bom=False)) == expected
            and loads(s, export(*lines, eol='\n', bom=False, last_eol=False)) == expected
            and loads(s, export(*lines, bom=False, last_eol=False)) == expected)


def empty_value_date(s):
    return loads(s, export(record('R1', '1,00', value=''), 'T;1;1,00')) == [tx('R1', 100, value=None)]


def impossible_date(s):
    return rejects(s, export(record('R1', '1,00', booking='30.02.2026'), 'T;1;1,00'),
                   export(record('R1', '1,00', value='31.04.2026'), 'T;1;1,00'))


def unknown_status(s):
    return rejects(s, export(record('R1', '1,00', status='X'), 'T;1;1,00'),
                   export(record('R1', '1,00', status='b'), 'T;1;1,00'))


def empty_export(s):
    return loads(s, export('T;0;0')) == [] and loads(s, export('T;0;0', eol='\n', bom=False)) == []



def not_utf8(s):
    # 'Café' as Latin-1: the byte E9 followed by a line end is not UTF-8.
    lines = (record('R1', '1,00', memo='Café'), 'T;1;1,00')
    latin = [export(*lines), export(*lines, eol='\n', bom=False)]
    for path in latin:
        Path(path).write_bytes(Path(path).read_bytes().replace('é'.encode('utf-8'), b'\xe9'))
    return loads(s, export(*lines)) == [tx('R1', 100, memo='Café')] and rejects(s, *latin)


def misquoted(s):
    # Text after the closing quote, and a double quote in a field that is not quoted.
    return rejects(s, export(record('R1', '1,00', memo='"Invoice A-7" final'), 'T;1;1,00'),
                   export(record('R1', '1,00', memo='Invoice "A-7" final'), 'T;1;1,00'))


def lone_cr(s):
    lines = (record('R1', '1,00'), record('R2', '2,00'), 'T;2;3,00')
    return rejects(s, export(*lines, eol='\r'), export(*lines, eol='\r', bom=False, last_eol=False))


CHECKS = [
    ('the sample loads', sample),
    ('english adjustments still parse', english_adjustments),
    ('an 18-digit amount converts exactly', eighteen_digits),
    ('the hash total is compared exactly', exact_hash),
    ('the hash total adds amounts across currencies', hash_across_currencies),
    ('a dot groups thousands in every currency', jpy_grouping),
    ('missing decimals are zeros', missing_decimals),
    ('more decimals than the currency allows is an error', too_many_decimals),
    ('a misplaced dot is an error', misplaced_dots),
    ('a sign before the number is an error', leading_sign),
    ('more than 18 digits is an error', too_many_digits),
    ('a pending record superseded by a later booked one is dropped', superseded_by_later),
    ('a pending record superseded by an earlier booked one is dropped', superseded_by_earlier),
    ('a pending record never booked is kept in file order', pending_kept),
    ('a reference twice with one status is an error', repeated_reference),
    ('a missing trailer is an error', missing_trailer),
    ('a wrong record count is an error', wrong_count),
    ('a wrong hash total is an error', wrong_hash),
    ('nothing may follow the trailer', after_trailer),
    ('the trailer counts and adds superseded records', superseded_in_trailer),
    ('a quoted memo keeps its semicolon and quotes', quoted_memo),
    ('a memo with a line break is one record', multiline_memo),
    ('a file without byte-order mark or CR loads', plain_file),
    ('an empty value date is None', empty_value_date),
    ('an impossible date is an error', impossible_date),
    ('an unknown status is an error', unknown_status),
    ('an export with no records loads as an empty list', empty_export),
    ('a file that is not UTF-8 is an error', not_utf8),
    ('a double quote outside the quoting rules is an error', misquoted),
    ('a line that ends in CR alone is an error', lone_cr),
]

if __name__ == '__main__':
    main(CHECKS, 'importer')
