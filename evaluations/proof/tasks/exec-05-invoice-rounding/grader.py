import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main

LINE_KEYS = ('sku', 'gross', 'discount', 'net', 'rate')
TAX_KEYS = ('rate', 'net', 'tax')


def doc(lines, taxes):
    """The documented result for these (sku, gross, discount, net, rate) lines and (rate, net, tax)
    breakdown entries. The totals are the sums docs/POLICY.md defines."""
    net = sum(line[3] for line in lines)
    tax = sum(entry[2] for entry in taxes)
    return {'lines': [dict(zip(LINE_KEYS, line)) for line in lines],
            'taxes': [dict(zip(TAX_KEYS, entry)) for entry in taxes],
            'net': net, 'tax': tax, 'total': net + tax}


def negative(invoice):
    """The same document with every amount negated: what a credit note of it must be."""
    return {'lines': [dict(line, gross=-line['gross'], discount=-line['discount'], net=-line['net'])
                      for line in invoice['lines']],
            'taxes': [dict(entry, net=-entry['net'], tax=-entry['tax']) for entry in invoice['taxes']],
            'net': -invoice['net'], 'tax': -invoice['tax'], 'total': -invoice['total']}


def invoice(s, rows):
    return s.build_invoice([s.Line(*row) for row in rows])


def credit(s, rows, *credited):
    return importlib.import_module('billing.credit').credit_note([s.Line(*row) for row in rows], *credited)


# Rows are (sku, quantity, unit_cents, discount_percent, tax_code).
ISSUE = [('MUG', 3, 450, '0', 'STD'), ('ATLAS', 2, 1200, '10', 'BOOKS'), ('FREIGHT', 1, 800, '0', 'EXPORT')]
# 19 % of 13.50 is 2.565: half a cent, rounded away from zero to 2.57.
ISSUE_DOC = doc([('MUG', 1350, 0, 1350, '19'), ('ATLAS', 2400, 240, 2160, '7'), ('FREIGHT', 800, 0, 800, '0')],
                [('19', 1350, 257), ('7', 2160, 151), ('0', 800, 0)])

# 5 % of 0.70 is 0.035: the discount is 0.04 and the net is 0.66. Rounding the net, 0.665, gives 0.67.
TAGS = [('TAG', 2, 35, '5', 'STD')]
TAGS_DOC = doc([('TAG', 70, 4, 66, '19')], [('19', 66, 13)])

# Three nets of 3.33 at 19 %: 19 % of 9.99 is 1.8981. Line by line it is 0.63 three times.
PENS = [('PEN', 1, 333, '0', 'STD'), ('INK', 1, 333, '0', 'STD'), ('PAD', 1, 333, '0', 'STD')]
PENS_DOC = doc([('PEN', 333, 0, 333, '19'), ('INK', 333, 0, 333, '19'), ('PAD', 333, 0, 333, '19')], [('19', 999, 190)])

# 8.75 % of 106.00 is 9.275. As a float, 10600 * (8.75 / 100) is 927.4999999999999.
ROOMS = [('ROOM', 2, 5300, '0', 'LODGING')]
ROOMS_DOC = doc([('ROOM', 10600, 0, 10600, '8.75')], [('8.75', 10600, 928)])

# No amount on this invoice is half a cent. Its 19 % and 7 % groups both differ from line-by-line
# tax, and FOOD and BOOKS taxed apart give 4.67 + 9.57, not 14.23.
LARGE = [('DESK', 2, 14900, '5', 'STD'), ('CHAIR', 4, 8952, '0', 'STD'), ('LAMP', 3, 2199, '12.5', 'STD'),
         ('ROOM', 2, 11450, '0', 'LODGING'), ('BREAKFAST', 2, 1450, '0', 'FOOD'), ('COFFEE', 12, 349, '10', 'FOOD'),
         ('MANUAL', 5, 1900, '0', 'BOOKS'), ('ATLAS', 1, 4900, '15', 'BOOKS'), ('PALLET', -3, 1200, '0', 'STD'),
         ('SAMPLE', 6, 250, '100', 'FOOD'), ('FREIGHT', 1, 4500, '0', 'EXPORT'), ('TONER', 7, 3333, '2.5', 'STD')]
LARGE_DOC = doc([('DESK', 29800, 1490, 28310, '19'), ('CHAIR', 35808, 0, 35808, '19'), ('LAMP', 6597, 825, 5772, '19'),
                 ('ROOM', 22900, 0, 22900, '8.75'), ('BREAKFAST', 2900, 0, 2900, '7'), ('COFFEE', 4188, 419, 3769, '7'),
                 ('MANUAL', 9500, 0, 9500, '7'), ('ATLAS', 4900, 735, 4165, '7'), ('PALLET', -3600, 0, -3600, '19'),
                 ('SAMPLE', 1500, 1500, 0, '7'), ('FREIGHT', 4500, 0, 4500, '0'), ('TONER', 23331, 583, 22748, '19')],
                [('19', 89038, 16917), ('8.75', 22900, 2004), ('7', 20334, 1423), ('0', 4500, 0)])


def issue_invoice(s):
    return invoice(s, ISSUE) == ISSUE_DOC and ISSUE_DOC['total'] == 4718


def discount_half_cent(s):
    # 5 % of 2.50 is 0.125.
    return invoice(s, [('CARD', 1, 250, '5', 'STD')]) == doc([('CARD', 250, 13, 237, '19')], [('19', 237, 45)])


def discount_is_the_rounded_figure(s):
    return invoice(s, TAGS) == TAGS_DOC


def tax_on_summed_nets(s):
    # Two nets of 2.40 at 19 %: 19 % of 4.80 is 0.912. Line by line it is 0.46 twice.
    drinks = [('JUICE', 1, 240, '0', 'STD'), ('COLA', 1, 240, '0', 'STD')]
    return (invoice(s, PENS) == PENS_DOC
            and invoice(s, drinks) == doc([('JUICE', 240, 0, 240, '19'), ('COLA', 240, 0, 240, '19')], [('19', 480, 91)]))


def codes_share_a_rate(s):
    # FOOD and BOOKS are both 7 %. Line by line, by code and by rate all give 0.21 here.
    rows = [('TEA', 1, 100, '0', 'FOOD'), ('NOVEL', 1, 200, '0', 'BOOKS')]
    return invoice(s, rows) == doc([('TEA', 100, 0, 100, '7'), ('NOVEL', 200, 0, 200, '7')], [('7', 300, 21)])


def breakdown_order(s):
    rows = [('FREIGHT', 1, 800, '0', 'EXPORT'), ('TEA', 1, 200, '0', 'FOOD'), ('ROOM', 1, 6000, '0', 'LODGING'),
            ('PEN', 1, 300, '0', 'STD')]
    return invoice(s, rows) == doc(
        [('FREIGHT', 800, 0, 800, '0'), ('TEA', 200, 0, 200, '7'), ('ROOM', 6000, 0, 6000, '8.75'), ('PEN', 300, 0, 300, '19')],
        [('19', 300, 57), ('8.75', 6000, 525), ('7', 200, 14), ('0', 800, 0)])


def zero_rate(s):
    return invoice(s, [('FREIGHT', 2, 800, '0', 'EXPORT')]) == doc([('FREIGHT', 1600, 0, 1600, '0')], [('0', 1600, 0)])


def float_discount(s):
    # 17.5 % of 13.00 is 2.275. As a float, 1300 * (17.5 / 100) is 227.49999999999997.
    return invoice(s, [('TILE', 2, 650, '17.5', 'STD')]) == doc([('TILE', 1300, 228, 1072, '19')], [('19', 1072, 204)])


def float_tax(s):
    return invoice(s, ROOMS) == ROOMS_DOC


def float_quarter_discount(s):
    # 25 % of 8.70 is 2.175. As a float, 870 / 100 * 25 is 217.49999999999997.
    return invoice(s, [('MAP', 3, 290, '25', 'FOOD')]) == doc([('MAP', 870, 218, 652, '7')], [('7', 652, 46)])


def return_line_discount(s):
    # 5 % of -0.70 is -0.035: the discount is -0.04 and the net is -0.66.
    rows = [('BOX', 1, 500, '0', 'STD'), ('TAG', -2, 35, '5', 'STD')]
    return invoice(s, rows) == doc([('BOX', 500, 0, 500, '19'), ('TAG', -70, -4, -66, '19')], [('19', 434, 82)])


def negative_tax(s):
    # 19 % of -0.50 is -0.095.
    rows = [('CRATE', -1, 50, '0', 'STD'), ('TEA', 1, 200, '0', 'FOOD')]
    return invoice(s, rows) == doc([('CRATE', -50, 0, -50, '19'), ('TEA', 200, 0, 200, '7')],
                                   [('19', -50, -10), ('7', 200, 14)])


def return_line_in_the_sum(s):
    # 19 % of 2.40 + 2.40 - 1.00 is 0.722. Line by line it is 0.46 + 0.46 - 0.19.
    rows = [('JUICE', 1, 240, '0', 'STD'), ('COLA', 1, 240, '0', 'STD'), ('CRATE', -1, 100, '0', 'STD')]
    return invoice(s, rows) == doc([('JUICE', 240, 0, 240, '19'), ('COLA', 240, 0, 240, '19'), ('CRATE', -100, 0, -100, '19')],
                                   [('19', 380, 72)])


def full_discount(s):
    rows = [('SAMPLE', 2, 500, '100', 'STD'), ('TEA', 1, 200, '0', 'FOOD')]
    return invoice(s, rows) == doc([('SAMPLE', 1000, 1000, 0, '19'), ('TEA', 200, 0, 200, '7')],
                                   [('19', 0, 0), ('7', 200, 14)])


def larger_invoice(s):
    return invoice(s, LARGE) == LARGE_DOC and LARGE_DOC['total'] == 157116


def shape(s):
    # The docstrings name dict, list, str and int. A subclass of one, such as OrderedDict, is one.
    for result in (invoice(s, ISSUE), credit(s, ISSUE), credit(s, ISSUE, {0: 1})):
        if not isinstance(result, dict) or set(result) != {'lines', 'taxes', 'net', 'tax', 'total'}:
            return False
        if not isinstance(result['lines'], list) or not isinstance(result['taxes'], list):
            return False
        for entries, keys in ((result['lines'], LINE_KEYS), (result['taxes'], TAX_KEYS)):
            for entry in entries:
                if not isinstance(entry, dict) or set(entry) != set(keys):
                    return False
                if not all(isinstance(entry[key], str if key in ('sku', 'rate') else int) for key in keys):
                    return False
        if not all(isinstance(result[key], int) for key in ('net', 'tax', 'total')):
            return False
    return True


def credit_issue(s):
    return credit(s, ISSUE) == negative(ISSUE_DOC)


def credit_discount(s):
    return credit(s, TAGS) == negative(TAGS_DOC)


def credit_summed_nets(s):
    return credit(s, PENS) == negative(PENS_DOC)


def credit_float_tax(s):
    return credit(s, ROOMS) == negative(ROOMS_DOC)


def credit_larger(s):
    return credit(s, LARGE) == negative(LARGE_DOC)


def partial_credit(s):
    # One mug of three and one atlas of two: 19 % of 4.50 is 0.855, and 7 % of 10.80 is 0.756.
    rows = [('MUG', 3, 450, '0', 'STD'), ('ATLAS', 2, 1200, '10', 'BOOKS')]
    return credit(s, rows, {0: 1, 1: 1}) == negative(doc([('MUG', 450, 0, 450, '19'), ('ATLAS', 1200, 120, 1080, '7')],
                                                         [('19', 450, 86), ('7', 1080, 76)]))


def partial_credit_tax(s):
    rows = [('PEN', 2, 333, '0', 'STD'), ('INK', 2, 333, '0', 'STD'), ('PAD', 2, 333, '0', 'STD')]
    return credit(s, rows, {0: 1, 1: 1, 2: 1}) == negative(PENS_DOC)


def partial_credit_order(s):
    rows = [('PEN', 4, 300, '0', 'STD'), ('FREIGHT', 1, 800, '0', 'EXPORT')]
    return credit(s, rows, {1: 1, 0: 2}) == negative(doc([('PEN', 600, 0, 600, '19'), ('FREIGHT', 800, 0, 800, '0')],
                                                         [('19', 600, 114), ('0', 800, 0)]))


def partial_credit_leaves_out(s):
    rows = [('PEN', 4, 300, '0', 'STD'), ('TEA', 2, 200, '0', 'FOOD'), ('FREIGHT', 1, 800, '0', 'EXPORT')]
    return credit(s, rows, {1: 1}) == negative(doc([('TEA', 200, 0, 200, '7')], [('7', 200, 14)]))


CHECKS = [
    ('the invoice in the issue totals 47.18', issue_invoice),
    ('half a cent of discount rounds up', discount_half_cent),
    ('the discount is rounded and the net is what remains', discount_is_the_rounded_figure),
    ('tax is charged once on the summed nets of a rate', tax_on_summed_nets),
    ('two codes with the same rate share one breakdown entry', codes_share_a_rate),
    ('the breakdown runs from the highest rate to the lowest', breakdown_order),
    ('a zero rate is listed with zero tax', zero_rate),
    ('a 17.5 percent discount of exactly half a cent', float_discount),
    ('tax of exactly half a cent at 8.75 percent', float_tax),
    ('a 25 percent discount of exactly half a cent', float_quarter_discount),
    ('a return line rounds its discount away from zero', return_line_discount),
    ('negative tax rounds away from zero', negative_tax),
    ('a return line lowers the taxed sum of its rate', return_line_in_the_sum),
    ('a 100 percent discount keeps the line and its rate', full_discount),
    ('a larger invoice', larger_invoice),
    ('amounts are ints under the documented keys', shape),
    ('full credit note of the issue invoice', credit_issue),
    ('full credit note mirrors a half cent discount', credit_discount),
    ('full credit note mirrors tax on summed nets', credit_summed_nets),
    ('full credit note mirrors half a cent of tax at 8.75 percent', credit_float_tax),
    ('full credit note of the larger invoice', credit_larger),
    ('partial credit is the negative of an invoice for the credited quantities', partial_credit),
    ('partial credit taxes the credited lines together', partial_credit_tax),
    ('partial credit lists lines in invoice order', partial_credit_order),
    ('partial credit leaves out what is not credited', partial_credit_leaves_out),
]

if __name__ == '__main__':
    main(CHECKS, 'billing.invoice')
