"""Amounts as integer minor units."""


def parse_amount(text, exponent=2):
    """Parse an amount in English notation into minor units: parse_amount('1,234.56') == 123456.

    `exponent` is the number of decimals of the currency's minor unit.
    """
    return round(float(text.replace(',', '')) * 10 ** exponent)
