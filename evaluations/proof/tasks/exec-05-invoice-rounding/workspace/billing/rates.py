"""Tax rates by tax code. Finance maintains this table."""

# Per cent, written as decimal strings.
RATES = {
    'STD': '19',
    'LODGING': '8.75',
    'FOOD': '7',
    'BOOKS': '7',
    'EXPORT': '0',
}


def rate_for(tax_code):
    """The rate of a tax code, as its decimal string in RATES. An unknown code raises KeyError."""
    return RATES[tax_code]
