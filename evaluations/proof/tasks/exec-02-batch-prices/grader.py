import importlib
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises

Product = namedtuple('Product', 'sku name unit_cents bulk_qty bulk_cents discontinued')


class Catalog:
    """The contract in the workspace's shop/catalog.py, word for word."""
    MAX_BATCH = 50

    def __init__(self, products):
        self._products = {product.sku: product for product in products}
        self.calls = []

    def get(self, sku):
        self.calls.append(('get', sku))
        return self._products.get(sku.upper())

    def get_many(self, skus):
        self.calls.append(('get_many', len(skus) if isinstance(skus, list) else None))
        if not isinstance(skus, list) or not skus or len(skus) > self.MAX_BATCH:
            raise ValueError('malformed batch')
        wanted = [sku.upper() for sku in skus]
        if len(set(wanted)) != len(wanted):
            raise ValueError('malformed batch: a product is named twice')
        return {sku: self._products[sku] for sku in wanted if sku in self._products}

    def count(self, kind):
        return sum(call[0] == kind for call in self.calls)


def shop(extra=0):
    """TEA-1 has a bulk price from 10 units, POT-3 and OLD-0 are discontinued, P001.. are plain products."""
    return Catalog([Product('TEA-1', 'Green tea', 450, 10, 400, False), Product('MUG-2', 'Mug', 900, 0, 0, False),
                    Product('POT-3', 'Old teapot', 2500, 0, 0, True), Product('OLD-0', 'Old tin', 300, 0, 0, True)]
                   + [Product(f'P{n:03}', f'Part {n}', 100 + n, 0, 0, False) for n in range(1, extra + 1)])


def parts(count, start=1):
    return [(f'P{n:03}', 1) for n in range(start, start + count)]


def priced(lines):
    return [(sku, 1, 100 + int(sku[1:]), 100 + int(sku[1:])) for sku, _ in lines]


def fails_with(s, name, sku, catalog, lines):
    """price_cart raises the named error, carrying the SKU as the line wrote it."""
    error = getattr(importlib.import_module('shop.errors'), name)
    try:
        s.price_cart(catalog, lines)
    except error as exc:
        return type(exc) is error and exc.sku == sku
    except Exception:
        return False
    return False


def small_cart(s):
    catalog = shop()
    return (s.price_cart(catalog, [('MUG-2', 1), ('TEA-1', 2)]) == [('MUG-2', 1, 900, 900), ('TEA-1', 2, 450, 900)]
            and catalog.calls == [('get_many', 2)])


def bulk_per_line(s):
    lines = [('TEA-1', 6), ('TEA-1', 6), ('TEA-1', 10)]
    return s.price_cart(shop(), lines) == [('TEA-1', 6, 450, 2700), ('TEA-1', 6, 450, 2700), ('TEA-1', 10, 400, 4000)]


def canonical_in_result(s):
    return s.price_cart(shop(), [('mug-2', 3)]) == [('MUG-2', 3, 900, 2700)]


def raw_in_error(s):
    return (fails_with(s, 'UnknownProduct', 'nope-9', shop(), [('MUG-2', 1), ('nope-9', 1)])
            and fails_with(s, 'Discontinued', 'pot-3', shop(), [('pot-3', 1)]))


def full_batch(s):
    catalog = shop(50)
    return s.price_cart(catalog, parts(50)) == priced(parts(50)) and catalog.calls == [('get_many', 50)]


def two_batches(s):
    catalog = shop(51)
    return (s.price_cart(catalog, parts(51)) == priced(parts(51))
            and catalog.count('get_many') == 2 and catalog.count('get') == 0)


def ticket_cart(s):
    catalog = shop(120)
    lines = [(f'P{n % 120 + 1:03}', 1) for n in range(400)]
    return s.price_cart(catalog, lines) == priced(lines) and catalog.count('get_many') == 3 and catalog.count('get') == 0


def repeated_once(s):
    catalog = shop(40)
    lines = parts(40) + parts(40)
    return s.price_cart(catalog, lines) == priced(lines) and catalog.calls == [('get_many', 40)]


def letter_case(s):
    catalog = shop()
    lines = [('tea-1', 1), ('TEA-1', 1), ('Tea-1', 10)]
    return (s.price_cart(catalog, lines) == [('TEA-1', 1, 450, 450), ('TEA-1', 1, 450, 450), ('TEA-1', 10, 400, 4000)]
            and catalog.calls == [('get_many', 1)])


def case_across_batches(s):
    # 50 products, each named in both letter cases: still one batch of 50.
    catalog = shop(50)
    lines = parts(50) + [(sku.lower(), qty) for sku, qty in parts(50)]
    return s.price_cart(catalog, lines) == priced(parts(50)) * 2 and catalog.calls == [('get_many', 50)]


def empty_cart(s):
    catalog = shop()
    return s.price_cart(catalog, []) == [] and catalog.calls == []


def bad_quantity(s):
    for qty in (0, -1, 1.0, '1', True, None):
        catalog = shop()
        if not raises(ValueError, s.price_cart, catalog, [('MUG-2', 1), ('NOPE-9', 1), ('TEA-1', qty)]) or catalog.calls:
            return False
    return True


def discontinued_first(s):
    return fails_with(s, 'Discontinued', 'POT-3', shop(), [('MUG-2', 1), ('POT-3', 1), ('NOPE-9', 1)])


def unknown_first(s):
    return fails_with(s, 'UnknownProduct', 'NOPE-9', shop(), [('MUG-2', 1), ('NOPE-9', 1), ('POT-3', 1)])


def first_line_across_batches(s):
    # Line 1 names an unknown product and line 7 a discontinued one. Sorted by SKU, the
    # discontinued product falls in the first batch and the unknown one in the second.
    lines = [('ZZZ-9', 1)] + parts(55)
    lines.insert(6, ('OLD-0', 1))
    return fails_with(s, 'UnknownProduct', 'ZZZ-9', shop(60), lines)


def budget_when_raising(s):
    catalog = shop(120)
    lines = [(f'P{n % 120 + 1:03}', 1) for n in range(400)] + [('NOPE-9', 1)]
    return (fails_with(s, 'UnknownProduct', 'NOPE-9', catalog, lines)
            and catalog.count('get_many') <= 3 and catalog.count('get') == 0)


def generator(s):
    catalog = shop()
    lines = ((sku, qty) for sku, qty in [('MUG-2', 1), ('TEA-1', 2)])
    return s.price_cart(catalog, lines) == [('MUG-2', 1, 900, 900), ('TEA-1', 2, 450, 900)]


def no_cache(s):
    before = s.price_cart(shop(), [('MUG-2', 1)])
    dearer = Catalog([Product('MUG-2', 'Mug', 950, 0, 0, False)])
    return before == [('MUG-2', 1, 900, 900)] and s.price_cart(dearer, [('MUG-2', 1)]) == [('MUG-2', 1, 950, 950)]


def quote(s):
    quote_line = importlib.import_module('shop.quote').quote_line
    catalog = shop()
    if quote_line(catalog, 'tea-1', 10) != ('TEA-1', 10, 400, 4000) or catalog.calls != [('get', 'tea-1')]:
        return False
    errors = importlib.import_module('shop.errors')
    return (raises(errors.UnknownProduct, quote_line, shop(), 'NOPE-9', 1)
            and raises(errors.Discontinued, quote_line, shop(), 'POT-3', 1)
            and raises(ValueError, quote_line, shop(), 'MUG-2', 0))


CHECKS = [
    ('small cart prices in one batch', small_cart),
    ('bulk price is per line', bulk_per_line),
    ('result carries the canonical SKU', canonical_in_result),
    ('error carries the SKU as written', raw_in_error),
    ('50 products fit one batch', full_batch),
    ('51 products take two batches', two_batches),
    ('400 lines of 120 products take three batches', ticket_cart),
    ('a repeated product is requested once', repeated_once),
    ('one product in several letter cases is one product', letter_case),
    ('letter case does not inflate the batch count', case_across_batches),
    ('empty cart makes no call', empty_cart),
    ('invalid quantity raises before any call', bad_quantity),
    ('discontinued line before unknown line', discontinued_first),
    ('unknown line before discontinued line', unknown_first),
    ('first unsellable line wins across batches', first_line_across_batches),
    ('budget holds when the cart raises', budget_when_raising),
    ('lines may be a generator', generator),
    ('no cache between carts', no_cache),
    ('quote_line still works', quote),
]

if __name__ == '__main__':
    main(CHECKS, 'shop.cart')
