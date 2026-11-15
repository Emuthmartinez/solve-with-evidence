"""Manual adjustments that back-office staff type into the ledger."""
from importer.money import parse_amount


def parse_adjustment(text):
    """Parse an adjustment such as '1,234.56 EUR' or '-12.5 EUR' into (minor units, currency).

    Staff type adjustments in English notation: a dot before the decimals, optional commas between
    thousands, a leading minus for a debit. Adjustments are always in a currency with two decimals:
    parse_adjustment('1,234.56 EUR') == (123456, 'EUR').
    """
    amount, currency = text.split()
    return parse_amount(amount), currency
