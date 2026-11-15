"""Read the bank's nightly transaction export. docs/FORMAT.md describes the format."""
import csv
from datetime import datetime
from pathlib import Path

from importer.model import FormatError, Transaction
from importer.money import parse_amount

CURRENCIES = Path(__file__).resolve().parent.parent / 'data' / 'currencies.csv'


def currency_table(path=CURRENCIES):
    """Map each currency code in the table to the number of decimals of its minor unit."""
    table = {}
    with open(path, encoding='utf-8') as file:
        for line in file.read().splitlines()[1:]:
            code, exponent = line.split(',')
            table[code] = int(exponent)
    return table


def parse_date(text):
    return datetime.strptime(text, '%d.%m.%Y').date()


def load(path):
    """Return the Transactions in the export file at `path`, in file order.

    Raises FormatError when the file does not follow docs/FORMAT.md. The currency table is
    data/currencies.csv, next to the package.
    """
    currencies = currency_table()
    with open(path, encoding='utf-8-sig', newline='') as file:
        rows = [row for row in csv.reader(file, delimiter=';') if row]
    transactions = []
    for fields in rows[1:]:
        if fields[0] == 'T':
            continue
        booking, value, reference, status, amount, currency, memo = fields
        if status not in ('B', 'P'):
            raise FormatError(f'unknown status {status!r}')
        if currency not in currencies:
            raise FormatError(f'unknown currency {currency!r}')
        if status == 'B':
            # The booked record replaces the pending one reported before it.
            transactions = [t for t in transactions if t.reference != reference]
        transactions.append(Transaction(
            parse_date(booking), parse_date(value) if value else None, reference,
            'booked' if status == 'B' else 'pending', parse_amount(amount, currencies[currency]), currency, memo))
    return transactions
