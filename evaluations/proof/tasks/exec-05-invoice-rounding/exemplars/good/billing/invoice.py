"""Build an invoice from its lines. docs/POLICY.md says how each amount is computed."""
from collections import namedtuple
from fractions import Fraction

from billing.money import percent_of
from billing.rates import rate_for

# quantity: int, negative for goods taken back. unit_cents: int, net of tax.
# discount_percent: decimal string from '0' to '100', such as '10' or '17.5'.
# tax_code: a key of billing.rates.RATES.
Line = namedtuple('Line', 'sku quantity unit_cents discount_percent tax_code')


def line_amounts(line):
    """The (gross, discount, net) of one line, in cents. The discount is the rounded figure."""
    gross = line.quantity * line.unit_cents
    discount = percent_of(gross, line.discount_percent)
    return gross, discount, gross - discount


def build_invoice(lines):
    """Compute an invoice from a list of Line.

    Returns a dict with exactly these keys:

    'lines'   a list with one dict per line, in the order given:
              {'sku': str, 'gross': int, 'discount': int, 'net': int, 'rate': str}
    'taxes'   the tax breakdown, a list with one dict per tax rate on the invoice,
              highest rate first: {'rate': str, 'net': int, 'tax': int}
    'net'     the net total
    'tax'     the tax total
    'total'   the invoice total

    Every amount is an int, in cents. A rate is the decimal string from billing.rates,
    such as '19' or '8.75'.
    """
    out = []
    nets = {}
    for line in lines:
        rate = rate_for(line.tax_code)
        gross, discount, net = line_amounts(line)
        out.append({'sku': line.sku, 'gross': gross, 'discount': discount, 'net': net, 'rate': rate})
        nets[rate] = nets.get(rate, 0) + net
    # Tax is charged once per rate, on the sum of the nets at that rate.
    taxes = [{'rate': rate, 'net': nets[rate], 'tax': percent_of(nets[rate], rate)}
             for rate in sorted(nets, key=Fraction, reverse=True)]
    net = sum(entry['net'] for entry in out)
    tax = sum(entry['tax'] for entry in taxes)
    return {'lines': out, 'taxes': taxes, 'net': net, 'tax': tax, 'total': net + tax}
