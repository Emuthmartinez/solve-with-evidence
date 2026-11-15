"""Plausible mistakes for exec-05-invoice-rounding. Each is the good exemplar with one mistake put back."""
from pathlib import Path

MONEY = 'billing/money.py'
INVOICE = 'billing/invoice.py'
CREDIT = 'billing/credit.py'
STARTER_CREDIT = (Path(__file__).resolve().parents[1]
                  / 'tasks/exec-05-invoice-rounding/workspace/billing/credit.py').read_text()

AWAY = ("    whole = (2 * abs(value.numerator) + value.denominator) // (2 * value.denominator)\n"
        "    return -whole if value < 0 else whole\n")
HALF_UP = "    return (2 * value.numerator + value.denominator) // (2 * value.denominator)\n"
EXACT = "    return round_cents(amount * Fraction(percent) / 100)\n"
ADD_NET = "        nets[rate] = nets.get(rate, 0) + net\n"
BREAKDOWN = ("    taxes = [{'rate': rate, 'net': nets[rate], 'tax': percent_of(nets[rate], rate)}\n"
             "             for rate in sorted(nets, key=Fraction, reverse=True)]\n")
BY_CODE = ("    taxes = [{'rate': rate_for(code), 'net': nets[code], 'tax': percent_of(nets[code], rate_for(code))}\n"
           "             for code in sorted(nets, key=lambda code: Fraction(rate_for(code)), reverse=True)]\n")
ORDER = "for rate in sorted(nets, key=Fraction, reverse=True)]"
CREDITED = ("        lines = [line._replace(quantity=credited[position])\n"
            "                 for position, line in enumerate(lines) if position in credited]\n")

# A credit note with arithmetic of its own, as the starter has, here with every rule right.
OWN_TAX = "'tax': share(nets[rate], rate)}"
OWN_BREAKDOWN = BREAKDOWN.replace('percent_of', 'share')
OWN_CREDIT = '''"""Credit notes: what we give back against an invoice."""
import math
from fractions import Fraction

from billing.money import round_cents
from billing.rates import rate_for


def share(amount, percent):
    return round_cents(amount * Fraction(percent) / 100)


def credit_note(lines, credited=None):
    out = []
    nets = {}
    line_tax = {}
    for position, line in enumerate(lines):
        if credited is not None and position not in credited:
            continue
        quantity = line.quantity if credited is None else credited[position]
        rate = rate_for(line.tax_code)
        gross = -quantity * line.unit_cents
        discount = share(gross, line.discount_percent)
        net = gross - discount
        out.append({'sku': line.sku, 'gross': gross, 'discount': discount, 'net': net, 'rate': rate})
        nets[rate] = nets.get(rate, 0) + net
        line_tax[rate] = line_tax.get(rate, 0) + share(net, rate)
    taxes = [{'rate': rate, 'net': nets[rate], 'tax': share(nets[rate], rate)}
             for rate in sorted(nets, key=Fraction, reverse=True)]
    net = sum(entry['net'] for entry in out)
    tax = sum(entry['tax'] for entry in taxes)
    return {'lines': out, 'taxes': taxes, 'net': net, 'tax': tax, 'total': net + tax}
'''
assert all(part in OWN_CREDIT for part in (EXACT, ADD_NET, OWN_TAX, OWN_BREAKDOWN))

HALF_CENT_CREDITS = ['full credit note of the issue invoice', 'full credit note mirrors a half cent discount',
                     'full credit note mirrors half a cent of tax at 8.75 percent',
                     'partial credit is the negative of an invoice for the credited quantities']
PER_RATE_CREDITS = ['full credit note mirrors tax on summed nets', 'full credit note of the larger invoice',
                    'partial credit taxes the credited lines together']
ZERO_RATED = ['the invoice in the issue totals 47.18', 'the breakdown runs from the highest rate to the lowest',
              'a zero rate is listed with zero tax', 'a larger invoice', 'full credit note of the issue invoice',
              'full credit note of the larger invoice', 'partial credit lists lines in invoice order']

# Correct solutions that differ from the exemplar. Each must pass every check.
RESULT = "    return {'lines': out, 'taxes': taxes, 'net': net, 'tax': tax, 'total': net + tax}\n"
ENTRY = "        out.append({'sku': line.sku, 'gross': gross, 'discount': discount, 'net': net, 'rate': rate})\n"
ACCEPTED = [
    ('the invoice and its lines built as OrderedDicts, which are dicts',
     {INVOICE: [("from collections import namedtuple\n", "from collections import OrderedDict, namedtuple\n"),
                (ENTRY, ENTRY.replace("out.append({", "out.append(OrderedDict({").replace("})\n", "}))\n")),
                (RESULT, RESULT.replace("return {", "return OrderedDict({").replace("}\n", "})\n"))]}),
]

VARIANTS = [
    ('half a cent rounded to even, as round() does',
     {MONEY: [(AWAY, "    return round(value)\n")]},
     ['the invoice in the issue totals 47.18', 'half a cent of discount rounds up', 'full credit note of the issue invoice']),
    ('half a cent rounded up, towards plus infinity, whatever the sign',
     {MONEY: [(AWAY, HALF_UP)]},
     ['a return line rounds its discount away from zero', 'negative tax rounds away from zero']),
    ('percentages computed through float',
     {MONEY: [(EXACT, "    return round_cents(Fraction(amount * (float(percent) / 100)))\n")]},
     ['a 17.5 percent discount of exactly half a cent', 'tax of exactly half a cent at 8.75 percent',
      'full credit note mirrors half a cent of tax at 8.75 percent']),
    ('cents divided by 100 as a float before the percentage is taken',
     {MONEY: [(EXACT, "    return round_cents(Fraction(amount / 100 * float(percent)))\n")]},
     ['a 25 percent discount of exactly half a cent']),
    ('tax computed line by line and added up',
     {INVOICE: [("    nets = {}\n", "    nets = {}\n    line_tax = {}\n"),
                (ADD_NET, ADD_NET + "        line_tax[rate] = line_tax.get(rate, 0) + percent_of(net, rate)\n"),
                ("'tax': percent_of(nets[rate], rate)}", "'tax': line_tax[rate]}")]},
     ['tax is charged once on the summed nets of a rate', 'a return line lowers the taxed sum of its rate',
      'a larger invoice'] + PER_RATE_CREDITS),
    ('tax grouped by tax code, not by rate',
     {INVOICE: [(ADD_NET, "        nets[line.tax_code] = nets.get(line.tax_code, 0) + net\n"),
                (BREAKDOWN, BY_CODE)]},
     ['two codes with the same rate share one breakdown entry', 'a larger invoice', 'full credit note of the larger invoice']),
    ('the net is rounded and the discount is what remains',
     {INVOICE: [("from billing.money import percent_of\n", "from billing.money import percent_of, round_cents\n"),
                ("    discount = percent_of(gross, line.discount_percent)\n    return gross, discount, gross - discount\n",
                 "    net = round_cents(gross * (100 - Fraction(line.discount_percent)) / 100)\n    return gross, gross - net, net\n")]},
     ['half a cent of discount rounds up', 'the discount is rounded and the net is what remains',
      'a 17.5 percent discount of exactly half a cent', 'a 25 percent discount of exactly half a cent',
      'a return line rounds its discount away from zero', 'full credit note mirrors a half cent discount']),
    ('breakdown in the order the rates first appear',
     {INVOICE: [(ORDER, "for rate in nets]")]},
     ['the breakdown runs from the highest rate to the lowest']),
    ('rates sorted as text',
     {INVOICE: [(ORDER, "for rate in sorted(nets, reverse=True)]")]},
     ['the invoice in the issue totals 47.18', 'the breakdown runs from the highest rate to the lowest',
      'negative tax rounds away from zero', 'a 100 percent discount keeps the line and its rate', 'a larger invoice',
      'full credit note of the issue invoice', 'full credit note of the larger invoice',
      'partial credit is the negative of an invoice for the credited quantities']),
    ('the 0 % rate left out of the breakdown',
     {INVOICE: [(ORDER, ORDER[:-1] + " if Fraction(rate)]")]},
     ZERO_RATED),
    ('a rate whose nets add up to nothing left out of the breakdown',
     {INVOICE: [(ORDER, ORDER[:-1] + " if nets[rate]]")]},
     ['a 100 percent discount keeps the line and its rate']),
    ('amounts returned as exact fractions, not ints',
     {MONEY: [("    return -whole if value < 0 else whole\n", "    return Fraction(-whole if value < 0 else whole)\n")]},
     ['amounts are ints under the documented keys']),
    ('credit.py left as the starter has it',
     {CREDIT: STARTER_CREDIT},
     HALF_CENT_CREDITS + PER_RATE_CREDITS),
    ('credit notes keep a rounding of their own that sends half a cent up',
     {CREDIT: OWN_CREDIT.replace(EXACT, "    return math.floor(amount * Fraction(percent) / 100 + Fraction(1, 2))\n")},
     HALF_CENT_CREDITS),
    ('credit notes still tax line by line',
     {CREDIT: OWN_CREDIT.replace(OWN_TAX, "'tax': line_tax[rate]}")},
     PER_RATE_CREDITS),
    ('credit notes still compute through float',
     {CREDIT: OWN_CREDIT.replace(EXACT, "    return round_cents(Fraction(amount * (float(percent) / 100)))\n")},
     ['full credit note mirrors half a cent of tax at 8.75 percent']),
    ('credit notes still group tax by tax code',
     {CREDIT: OWN_CREDIT.replace(ADD_NET, "        nets[line.tax_code] = nets.get(line.tax_code, 0) + net\n")
      .replace(OWN_BREAKDOWN, BY_CODE.replace('percent_of', 'share'))},
     ['full credit note of the larger invoice']),
    ('credit notes computed on negated quantities, with half a cent rounded up',
     {MONEY: [(AWAY, HALF_UP)],
      CREDIT: [("    invoice = build_invoice(lines)\n",
                "    return build_invoice([line._replace(quantity=-line.quantity) for line in lines])\n")]},
     ['a return line rounds its discount away from zero', 'negative tax rounds away from zero'] + HALF_CENT_CREDITS),
    ('partial credit in the order of the credited mapping',
     {CREDIT: [(CREDITED, "        lines = [lines[position]._replace(quantity=quantity) for position, quantity in credited.items()]\n")]},
     ['partial credit lists lines in invoice order']),
    ('lines that are not credited stay on the credit note at zero',
     {CREDIT: [(CREDITED, "        lines = [line._replace(quantity=credited.get(position, 0)) for position, line in enumerate(lines)]\n")]},
     ['partial credit leaves out what is not credited']),
]
