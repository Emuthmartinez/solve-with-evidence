"""Read the bank's nightly transaction export. docs/FORMAT.md describes the format."""
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


def load(path):
    """Return the Transactions in the export file at `path`, in file order.

    Raises FormatError when the file does not follow docs/FORMAT.md. The currency table is
    data/currencies.csv, next to the package.
    """
    currencies = currency_table()
    transactions = []
    with open(path, encoding='utf-8') as file:
        lines = file.read().splitlines()
    for line in lines[1:]:
        if line.startswith('T;'):
            continue
        booking, value, reference, status, amount, currency, memo = line.split(';')
        if status != 'B':
            continue
        if currency not in currencies:
            raise FormatError(f'unknown currency {currency!r}')
        sign = -1 if amount.endswith('-') else 1
        transactions.append(Transaction(
            datetime.strptime(booking, '%d.%m.%Y').date(),
            datetime.strptime(value, '%d.%m.%Y').date() if value else None,
            reference, 'booked', sign * parse_amount(amount.rstrip('-').replace(',', '.')), currency, memo))
    return transactions
