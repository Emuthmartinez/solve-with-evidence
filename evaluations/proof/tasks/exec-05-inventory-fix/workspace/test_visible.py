import unittest

from solution import Inventory


class VisibleTest(unittest.TestCase):
    def test_restock_adds_to_existing_stock(self):
        inventory = Inventory()
        inventory.restock('apple', 5)
        inventory.restock('apple', 3)
        self.assertEqual(inventory.available('apple'), 8)


if __name__ == '__main__':
    unittest.main()
