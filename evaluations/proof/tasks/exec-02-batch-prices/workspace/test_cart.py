import unittest

from shop.cart import price_cart
from shop.catalog import Catalog, Product
from shop.errors import Discontinued, UnknownProduct


def catalog():
    return Catalog([
        Product('TEA-1', 'Green tea', 450, 10, 400, False),
        Product('MUG-2', 'Mug', 900, 0, 0, False),
        Product('POT-3', 'Old teapot', 2500, 0, 0, True),
    ])


class PriceCart(unittest.TestCase):
    def test_lines_are_priced_in_cart_order(self):
        priced = price_cart(catalog(), [('MUG-2', 1), ('TEA-1', 2)])
        self.assertEqual(priced, [('MUG-2', 1, 900, 900), ('TEA-1', 2, 450, 900)])

    def test_bulk_price(self):
        self.assertEqual(price_cart(catalog(), [('TEA-1', 10)]), [('TEA-1', 10, 400, 4000)])

    def test_unknown_product(self):
        with self.assertRaises(UnknownProduct):
            price_cart(catalog(), [('MUG-2', 1), ('NOPE-9', 1)])

    def test_discontinued_product(self):
        with self.assertRaises(Discontinued):
            price_cart(catalog(), [('POT-3', 1)])


if __name__ == '__main__':
    unittest.main()
