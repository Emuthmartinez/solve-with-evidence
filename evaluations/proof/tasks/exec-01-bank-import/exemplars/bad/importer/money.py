"""Amounts as integer minor units."""


def parse_amount(text, exponent=2):
    """Parse an amount in the bank's notation into minor units: parse_amount('1.234,56-') == -123456.

    `exponent` is the number of decimals of the currency's minor unit.
    """
    sign = -1 if text.endswith('-') else 1
    return sign * round(float(text.rstrip('-').replace('.', '').replace(',', '.')) * 10 ** exponent)
