import unittest

from billing.credit import credit_note
from billing.invoice import Line, build_invoice

ORDER = [Line('PEN', 4, 300, '0', 'STD'), Line('FREIGHT', 1, 800, '0', 'EXPORT')]
ORDER_INVOICE = {
    'lines': [{'sku': 'PEN', 'gross': 1200, 'discount': 0, 'net': 1200, 'rate': '19'},
              {'sku': 'FREIGHT', 'gross': 800, 'discount': 0, 'net': 800, 'rate': '0'}],
    'taxes': [{'rate': '19', 'net': 1200, 'tax': 228}, {'rate': '0', 'net': 800, 'tax': 0}],
    'net': 2000, 'tax': 228, 'total': 2228,
}


class BuildInvoice(unittest.TestCase):
    def test_lines_breakdown_and_totals(self):
        self.assertEqual(build_invoice(ORDER), ORDER_INVOICE)

    def test_amounts_are_ints(self):
        invoice = build_invoice(ORDER)
        amounts = [invoice['net'], invoice['tax'], invoice['total'], invoice['lines'][0]['net'], invoice['taxes'][0]['tax']]
        self.assertEqual([type(amount) for amount in amounts], [int] * 5)

    def test_line_discount(self):
        invoice = build_invoice([Line('ATLAS', 1, 3000, '10', 'BOOKS')])
        self.assertEqual(invoice['lines'], [{'sku': 'ATLAS', 'gross': 3000, 'discount': 300, 'net': 2700, 'rate': '7'}])
        self.assertEqual((invoice['net'], invoice['tax'], invoice['total']), (2700, 189, 2889))

    def test_two_lines_at_one_rate(self):
        invoice = build_invoice([Line('TEA', 1, 200, '0', 'FOOD'), Line('RICE', 1, 300, '0', 'FOOD')])
        self.assertEqual(invoice['taxes'], [{'rate': '7', 'net': 500, 'tax': 35}])

    def test_goods_taken_back(self):
        invoice = build_invoice([Line('JUICE', 6, 200, '0', 'STD'), Line('CRATE', -2, 150, '0', 'STD')])
        self.assertEqual(invoice['lines'][1], {'sku': 'CRATE', 'gross': -300, 'discount': 0, 'net': -300, 'rate': '19'})
        self.assertEqual((invoice['net'], invoice['tax'], invoice['total']), (900, 171, 1071))


class CreditNote(unittest.TestCase):
    def test_full_credit_note_is_the_negative_of_the_invoice(self):
        self.assertEqual(credit_note(ORDER), {
            'lines': [{'sku': 'PEN', 'gross': -1200, 'discount': 0, 'net': -1200, 'rate': '19'},
                      {'sku': 'FREIGHT', 'gross': -800, 'discount': 0, 'net': -800, 'rate': '0'}],
            'taxes': [{'rate': '19', 'net': -1200, 'tax': -228}, {'rate': '0', 'net': -800, 'tax': 0}],
            'net': -2000, 'tax': -228, 'total': -2228,
        })

    def test_partial_credit_note(self):
        self.assertEqual(credit_note(ORDER, {0: 1}), {
            'lines': [{'sku': 'PEN', 'gross': -300, 'discount': 0, 'net': -300, 'rate': '19'}],
            'taxes': [{'rate': '19', 'net': -300, 'tax': -57}],
            'net': -300, 'tax': -57, 'total': -357,
        })


if __name__ == '__main__':
    unittest.main()
