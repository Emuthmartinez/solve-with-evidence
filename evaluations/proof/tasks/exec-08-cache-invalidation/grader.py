import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises

MAX_PRICE_CENTS = 1000000


def backend_error():
    """The workspace's BackendError, so a service that catches it by name catches the grader's."""
    return importlib.import_module('products.backend').BackendError


def valid(product):
    return (isinstance(product, dict) and set(product) == {'id', 'name', 'category', 'price_cents'}
            and all(isinstance(product[key], str) and product[key] for key in ('id', 'name', 'category'))
            and type(product['price_cents']) is int and 0 <= product['price_cents'] <= MAX_PRICE_CENTS)


class Backend:
    """The contract in the workspace's products/backend.py, word for word."""

    def __init__(self, products=()):
        self._rows = {product['id']: dict(product) for product in products}
        self.calls = []

    def get(self, product_id):
        self.calls.append(('get', product_id))
        row = self._rows.get(product_id)
        return None if row is None else dict(row)

    def ids_in_category(self, category):
        self.calls.append(('ids_in_category', category))
        return sorted(product_id for product_id, row in self._rows.items() if row['category'] == category)

    def put(self, product):
        self.calls.append(('put', product.get('id') if isinstance(product, dict) else None))
        if not valid(product):
            raise backend_error()('invalid product: %r' % (product,))
        self._rows[product['id']] = dict(product)

    def delete(self, product_id):
        self.calls.append(('delete', product_id))
        if product_id not in self._rows:
            raise KeyError(product_id)
        del self._rows[product_id]


def row(product_id, name, category, price_cents):
    return {'id': product_id, 'name': name, 'category': category, 'price_cents': price_cents}


A1 = row('A1', 'Kettle', 'kitchen', 2500)
A2 = row('A2', 'Toaster', 'kitchen', 2999)
A3 = row('A3', 'Mixer', 'kitchen', 4500)
B1 = row('B1', 'Lamp', 'lighting', 1500)
B2 = row('B2', 'Bulb', 'lighting', 300)
B3 = row('B3', 'Chandelier', 'lighting', 900000)
C1 = row('C1', 'Rug', 'decor', 8000)
KITCHEN, LIGHTING, DECOR = [A1, A2], [B1, B2, B3], [C1]


def service(s, *warm):
    """A service over the fixture, after the warm-up reads; the warm-up calls are not counted.
    A warm-up read is a product id, or a category name."""
    backend = Backend([A1, A2, B1, B2, B3, C1])
    svc = s.Service(backend)
    for name in warm:
        if name in ('kitchen', 'lighting', 'decor', 'garden'):
            svc.list_category(name)
        else:
            svc.get_product(name)
    backend.calls.clear()
    return svc, backend


def within(calls, allowed):
    """Each call is one the guarantees allow, and none repeats."""
    return all(call in allowed for call in calls) and len(set(calls)) == len(calls)


def edited(product, **changes):
    return dict(product, **changes)


def fetched_once(s):
    svc, backend = service(s)
    first, second = svc.get_product('A1'), svc.get_product('A1')
    return first == A1 and second == A1 and backend.calls == [('get', 'A1')]


def missing_fetched_once(s):
    svc, backend = service(s)
    return svc.get_product('Z9') is None and svc.get_product('Z9') is None and backend.calls == [('get', 'Z9')]


def first_listing(s):
    svc, backend = service(s, 'A1')
    return (svc.list_category('kitchen') == KITCHEN
            and sorted(backend.calls) == [('get', 'A2'), ('ids_in_category', 'kitchen')])


def repeated_listing(s):
    svc, backend = service(s, 'kitchen', 'garden')
    return svc.list_category('kitchen') == KITCHEN and svc.list_category('garden') == [] and backend.calls == []


def edit_read_back(s):
    svc, _ = service(s, 'A1')
    svc.update_product('A1', {'price_cents': 2700})
    return svc.get_product('A1') == edited(A1, price_cents=2700)


def edit_in_listing(s):
    svc, _ = service(s, 'kitchen')
    svc.update_product('A1', {'price_cents': 2700})
    return svc.list_category('kitchen') == [edited(A1, price_cents=2700), A2]


def edit_refetches_little(s):
    svc, backend = service(s, 'kitchen', 'lighting', 'decor')
    svc.update_product('A1', {'price_cents': 2700})
    backend.calls.clear()
    reads = (svc.list_category('kitchen') == [edited(A1, price_cents=2700), A2]
             and svc.list_category('lighting') == LIGHTING and svc.list_category('decor') == DECOR
             and svc.get_product('A2') == A2 and svc.get_product('B1') == B1)
    return reads and within(backend.calls, [('ids_in_category', 'kitchen'), ('get', 'A1')])


def write_costs(s):
    svc, backend = service(s)
    svc.update_product('A1', {'price_cents': 2700})
    if backend.calls != [('get', 'A1'), ('put', 'A1')]:
        return False
    svc, backend = service(s, 'A1')
    svc.update_product('A1', {'price_cents': 2700})
    if backend.calls != [('put', 'A1')]:
        return False
    svc, backend = service(s, 'A3')
    svc.create_product(dict(A3))
    if backend.calls != [('put', 'A3')]:
        return False
    svc, backend = service(s, 'kitchen')
    svc.delete_product('A2')
    return backend.calls == [('delete', 'A2')]


def create_in_listing(s):
    svc, _ = service(s, 'kitchen')
    svc.create_product(dict(A3))
    return svc.list_category('kitchen') == [A1, A2, A3]


def create_after_not_found(s):
    svc, _ = service(s, 'A3')
    svc.create_product(dict(A3))
    return svc.get_product('A3') == A3


def create_refetches_little(s):
    svc, backend = service(s, 'kitchen', 'lighting', 'A3', 'C1')
    svc.create_product(dict(A3))
    backend.calls.clear()
    reads = (svc.list_category('kitchen') == [A1, A2, A3] and svc.list_category('lighting') == LIGHTING
             and svc.get_product('C1') == C1 and svc.get_product('A1') == A1)
    return reads and within(backend.calls, [('ids_in_category', 'kitchen'), ('get', 'A3')])


def delete_from_listing(s):
    svc, _ = service(s, 'kitchen')
    svc.delete_product('A2')
    return svc.list_category('kitchen') == [A1]


def delete_reads_missing(s):
    svc, _ = service(s, 'A2')
    svc.delete_product('A2')
    return svc.get_product('A2') is None


def delete_refetches_little(s):
    svc, backend = service(s, 'kitchen', 'lighting', 'decor', 'Z9')
    svc.delete_product('A2')
    backend.calls.clear()
    reads = (svc.list_category('kitchen') == [A1] and svc.list_category('lighting') == LIGHTING
             and svc.list_category('decor') == DECOR and svc.get_product('A1') == A1
             and svc.get_product('B1') == B1 and svc.get_product('Z9') is None)
    return reads and within(backend.calls, [('ids_in_category', 'kitchen')])


def move_leaves_old(s):
    svc, _ = service(s, 'kitchen', 'lighting')
    svc.update_product('A1', {'category': 'lighting'})
    return svc.list_category('kitchen') == [A2]


def move_joins_new(s):
    svc, _ = service(s, 'kitchen', 'lighting')
    svc.update_product('A1', {'category': 'lighting'})
    moved = edited(A1, category='lighting')
    return svc.list_category('lighting') == [moved] + LIGHTING and svc.get_product('A1') == moved


def move_refetches_little(s):
    svc, backend = service(s, 'kitchen', 'lighting', 'decor')
    svc.update_product('A1', {'category': 'lighting'})
    backend.calls.clear()
    reads = (svc.list_category('decor') == DECOR and svc.get_product('A2') == A2 and svc.get_product('B1') == B1
             and svc.list_category('kitchen') == [A2]
             and svc.list_category('lighting') == [edited(A1, category='lighting')] + LIGHTING)
    return reads and within(backend.calls, [('ids_in_category', 'kitchen'), ('ids_in_category', 'lighting'),
                                            ('get', 'A1')])


def rejected_update_raises(s):
    svc, backend = service(s)
    return (raises(backend_error(), svc.update_product, 'A1', {'price_cents': -1})
            and backend._rows['A1'] == A1 and svc.get_product('A1') == A1)


def rejected_update_keeps_cache(s):
    svc, backend = service(s, 'kitchen', 'lighting', 'A1')
    if not raises(backend_error(), svc.update_product, 'A1', {'category': 'lighting', 'price_cents': -1}):
        return False
    backend.calls.clear()
    return (svc.get_product('A1') == A1 and svc.list_category('kitchen') == KITCHEN
            and svc.list_category('lighting') == LIGHTING and backend.calls == [])


def rejected_create_keeps_cache(s):
    svc, backend = service(s, 'A3', 'kitchen')
    if not raises(backend_error(), svc.create_product, edited(A3, price_cents=-1)):
        return False
    backend.calls.clear()
    return svc.get_product('A3') is None and svc.list_category('kitchen') == KITCHEN and backend.calls == []


def missing_errors(s):
    svc, backend = service(s)
    if not raises(KeyError, svc.update_product, 'Q7', {'price_cents': 100}) or backend.calls != [('get', 'Q7')]:
        return False
    svc, backend = service(s, 'kitchen', 'Z9')
    if not (raises(KeyError, svc.update_product, 'Z9', {'price_cents': 100})
            and raises(KeyError, svc.delete_product, 'Z9')
            and raises(ValueError, svc.create_product, edited(A1, price_cents=1))):
        return False
    if backend.calls:
        return False
    return (svc.list_category('kitchen') == KITCHEN and svc.get_product('Z9') is None and backend.calls == []
            and backend._rows['A1'] == A1)


def returned_product_copied(s):
    svc, _ = service(s)
    svc.get_product('A1')['price_cents'] = 1
    svc.get_product('A1')['name'] = 'changed'
    return svc.get_product('A1') == A1


def returned_listing_copied(s):
    svc, _ = service(s, 'A2')
    listing = svc.list_category('kitchen')
    listing[0]['price_cents'] = 1
    listing[1]['name'] = 'changed'
    listing.append('junk')
    svc.list_category('kitchen').pop()
    return svc.list_category('kitchen') == KITCHEN and svc.get_product('A1') == A1 and svc.get_product('A2') == A2


def written_dict_copied(s):
    svc, _ = service(s, 'A3', 'A1')
    product, changes = dict(A3), {'price_cents': 2700}
    svc.create_product(product)
    svc.update_product('A1', changes)
    first = svc.get_product('A3'), svc.get_product('A1')
    product['price_cents'], changes['price_cents'] = 1, 1
    return first == (A3, edited(A1, price_cents=2700)) and (svc.get_product('A3'), svc.get_product('A1')) == first


def price_list_works(s):
    svc, _ = service(s)
    return importlib.import_module('products.pricelist').price_list(svc, 'kitchen') == ['Kettle 25.00', 'Toaster 29.99']


def price_list_keeps_cache(s):
    price_list = importlib.import_module('products.pricelist').price_list
    svc, _ = service(s)
    lines = ['Kettle 25.00', 'Toaster 29.99']
    return (price_list(svc, 'kitchen') == lines and price_list(svc, 'kitchen') == lines
            and svc.get_product('A1') == A1 and svc.list_category('kitchen') == KITCHEN)


def reprice_whole(s):
    svc, _ = service(s, 'kitchen', 'A1')
    svc.reprice_category('kitchen', 5)
    repriced = [edited(A1, price_cents=2625), edited(A2, price_cents=3148)]
    return svc.list_category('kitchen') == repriced and svc.get_product('A1') == repriced[0]


def partial_reprice(s):
    # +20%: the Lamp and the Bulb are written, the Chandelier would cost more than MAX_PRICE_CENTS.
    svc, _ = service(s, 'lighting')
    if not raises(backend_error(), svc.reprice_category, 'lighting', 20):
        return False
    return (svc.get_product('B1') == edited(B1, price_cents=1800)
            and svc.list_category('lighting') == [edited(B1, price_cents=1800), edited(B2, price_cents=360), B3])


def partial_reprice_cost(s):
    svc, backend = service(s, 'kitchen', 'lighting', 'C1')
    if not raises(backend_error(), svc.reprice_category, 'lighting', 20):
        return False
    if backend.calls != [('put', 'B1'), ('put', 'B2'), ('put', 'B3')]:
        return False
    backend.calls.clear()
    reads = (svc.get_product('B3') == B3 and svc.list_category('kitchen') == KITCHEN
             and svc.list_category('lighting') == [edited(B1, price_cents=1800), edited(B2, price_cents=360), B3]
             and svc.get_product('C1') == C1)
    return reads and within(backend.calls, [('ids_in_category', 'lighting'), ('get', 'B1'), ('get', 'B2')])


CHECKS = [
    ('a product is fetched once', fetched_once),
    ('a missing product is fetched once', missing_fetched_once),
    ('a first listing fetches only uncached products', first_listing),
    ('a repeated listing makes no call', repeated_listing),
    ('an edited price is read back', edit_read_back),
    ('an edited price shows in the listing', edit_in_listing),
    ('an edit refetches only the edited product', edit_refetches_little),
    ('a write looks its product up through the cache', write_costs),
    ('a created product shows in the listing', create_in_listing),
    ('a created product replaces a cached not-found', create_after_not_found),
    ('a create refetches only what it added', create_refetches_little),
    ('a deleted product leaves the listing', delete_from_listing),
    ('a deleted product reads as missing', delete_reads_missing),
    ('a delete refetches only its listing', delete_refetches_little),
    ('a moved product leaves its old listing', move_leaves_old),
    ('a moved product joins its new listing', move_joins_new),
    ('a move refetches only the two listings', move_refetches_little),
    ('a rejected update raises the backend error', rejected_update_raises),
    ('a rejected update keeps the cache', rejected_update_keeps_cache),
    ('a rejected create keeps the cache', rejected_create_keeps_cache),
    ('missing product errors change nothing', missing_errors),
    ('changing a returned product changes no later read', returned_product_copied),
    ('changing a returned listing changes no later read', returned_listing_copied),
    ('changing a written dict changes no later read', written_dict_copied),
    ('the price list still works', price_list_works),
    ('the price list leaves the cache intact', price_list_keeps_cache),
    ('a whole reprice reads back', reprice_whole),
    ('a partial reprice reads back what was written', partial_reprice),
    ('a partial reprice refetches only what it wrote', partial_reprice_cost),
]

if __name__ == '__main__':
    main(CHECKS, 'products.service')
