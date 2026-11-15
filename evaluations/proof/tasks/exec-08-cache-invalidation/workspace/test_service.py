import unittest

from products.backend import Backend
from products.pricelist import price_list
from products.service import Service

KETTLE = {'id': 'A1', 'name': 'Kettle', 'category': 'kitchen', 'price_cents': 2500}
TOASTER = {'id': 'A2', 'name': 'Toaster', 'category': 'kitchen', 'price_cents': 2999}
LAMP = {'id': 'B1', 'name': 'Lamp', 'category': 'lighting', 'price_cents': 1500}


def backend():
    return Backend([KETTLE, TOASTER, LAMP])


class Reads(unittest.TestCase):
    def test_get_product(self):
        service = Service(backend())
        self.assertEqual(service.get_product('A1'), KETTLE)
        self.assertIsNone(service.get_product('Z9'))

    def test_a_repeated_read_uses_the_cache(self):
        store = backend()
        service = Service(store)
        service.get_product('A1')
        service.get_product('A1')
        self.assertEqual(store.calls, [('get', 'A1')])

    def test_list_category(self):
        service = Service(backend())
        self.assertEqual(service.list_category('kitchen'), [KETTLE, TOASTER])
        self.assertEqual(service.list_category('garden'), [])


class Writes(unittest.TestCase):
    def test_an_update_is_stored(self):
        store = backend()
        Service(store).update_product('A1', {'price_cents': 2700})
        self.assertEqual(Service(store).get_product('A1')['price_cents'], 2700)

    def test_a_create_is_stored(self):
        store = backend()
        Service(store).create_product({'id': 'A3', 'name': 'Mixer', 'category': 'kitchen', 'price_cents': 4500})
        self.assertEqual(Service(store).get_product('A3')['name'], 'Mixer')

    def test_a_delete_is_stored(self):
        store = backend()
        Service(store).delete_product('B1')
        self.assertIsNone(Service(store).get_product('B1'))

    def test_missing_products(self):
        service = Service(backend())
        with self.assertRaises(KeyError):
            service.update_product('Z9', {'price_cents': 100})
        with self.assertRaises(KeyError):
            service.delete_product('Z9')
        with self.assertRaises(ValueError):
            service.create_product(dict(KETTLE))

    def test_reprice_category(self):
        service = Service(backend())
        service.reprice_category('kitchen', 10)
        self.assertEqual([p['price_cents'] for p in service.list_category('kitchen')], [2750, 3298])


class PriceList(unittest.TestCase):
    def test_price_list(self):
        self.assertEqual(price_list(Service(backend()), 'kitchen'), ['Kettle 25.00', 'Toaster 29.99'])


if __name__ == '__main__':
    unittest.main()
