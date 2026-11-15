"""Read the bank's nightly transaction export. docs/FORMAT.md describes the format."""
import csv
import re
from datetime import date
from fractions import Fraction
from pathlib import Path

from importer.model import FormatError, Transaction

CURRENCIES = Path(__file__).resolve().parent.parent / 'data' / 'currencies.csv'
HEADER = ['Booking date', 'Value date', 'Reference', 'Status', 'Amount', 'Currency', 'Memo']
STATUSES = {'B': 'booked', 'P': 'pending'}
NUMBER = re.compile(r'([0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+)(?:,([0-9]+))?(-?)')
DATE = re.compile(r'([0-9]{2})\.([0-9]{2})\.([0-9]{4})')
MAX_DIGITS = 18


def currency_table(path=CURRENCIES):
    """Map each currency code in the table to the number of decimals of its minor unit."""
    table = {}
    with open(path, encoding='utf-8') as file:
        for line in file.read().splitlines()[1:]:
            code, exponent = line.split(',')
            table[code] = int(exponent)
    return table


def number(text):
    """Return (exact signed value, decimals, digits) of a number in the bank's amount notation."""
    match = NUMBER.fullmatch(text)
    if not match:
        raise FormatError(f'not an amount: {text!r}')
    whole, decimals, minus = match.groups()
    decimals = decimals or ''
    digits = whole.replace('.', '') + decimals
    value = Fraction(int(digits), 10 ** len(decimals))
    return (-value if minus else value), len(decimals), len(digits)


def parse_date(text):
    match = DATE.fullmatch(text)
    try:
        day, month, year = map(int, match.groups())
        return date(year, month, day)
    except (AttributeError, ValueError):
        raise FormatError(f'not a date: {text!r}') from None


def parse_record(fields, currencies):
    """Return the Transaction for one data record and its amount as the trailer adds it."""
    if len(fields) != len(HEADER):
        raise FormatError(f'expected {len(HEADER)} fields: {fields!r}')
    booking, value, reference, status, amount, currency, memo = fields
    if not reference:
        raise FormatError('empty reference')
    if status not in STATUSES:
        raise FormatError(f'unknown status {status!r}')
    if currency not in currencies:
        raise FormatError(f'unknown currency {currency!r}')
    worth, decimals, digits = number(amount)
    if decimals > currencies[currency] or digits > MAX_DIGITS:
        raise FormatError(f'invalid {currency} amount {amount!r}')
    transaction = Transaction(parse_date(booking), parse_date(value) if value else None, reference,
                              STATUSES[status], int(worth * 10 ** currencies[currency]), currency, memo)
    return transaction, worth


def load(path):
    """Return the Transactions in the export file at `path`, in file order.

    Raises FormatError when the file does not follow docs/FORMAT.md. The currency table is
    data/currencies.csv, next to the package.
    """
    currencies = currency_table()
    with open(path, encoding='utf-8-sig', newline='') as file:
        rows = list(csv.reader(file, delimiter=';'))
    if not rows or rows[0] != HEADER:
        raise FormatError('missing header')
    if len(rows) < 2 or rows[-1][:1] != ['T'] or len(rows[-1]) != 3:
        raise FormatError('no trailer: the file is truncated')
    records, (_, count, total) = rows[1:-1], rows[-1]
    if [] in records:
        raise FormatError('empty line')
    parsed = [parse_record(fields, currencies) for fields in records]
    if not re.fullmatch('[0-9]+', count) or int(count) != len(records):
        raise FormatError(f'record count {count!r} does not match {len(records)} records')
    if number(total)[0] != sum(worth for _, worth in parsed):
        raise FormatError(f'hash total {total!r} does not match')
    seen = set()
    for transaction, _ in parsed:
        key = (transaction.reference, transaction.status)
        if key in seen:
            raise FormatError(f'{transaction.status} reference {transaction.reference!r} occurs twice')
        seen.add(key)
    booked = {reference for reference, status in seen if status == 'booked'}
    return [transaction for transaction, _ in parsed
            if transaction.status == 'booked' or transaction.reference not in booked]
