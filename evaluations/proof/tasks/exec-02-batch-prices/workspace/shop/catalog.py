"""Client for the catalog service.

Production talks to the service over HTTP. This in-memory class has the same contract and is
what the tests use. Each call to `get` or `get_many` is one round trip, recorded in `calls`.
"""
from collections import namedtuple

# bulk_qty is 0 for a product with no bulk price.
Product = namedtuple('Product', 'sku name unit_cents bulk_qty bulk_cents discontinued')


class Catalog:
    MAX_BATCH = 50

    def __init__(self, products):
        self._products = {product.sku: product for product in products}
        self.calls = []

    def get(self, sku):
        """One round trip. Return the Product for `sku`, or None when there is no such product.

        SKUs are ASCII and case-insensitive. The service stores each one in upper case, and
        `Product.sku` holds that canonical form: get('ab-1').sku == 'AB-1'.
        """
        self.calls.append(('get', sku))
        return self._products.get(sku.upper())

    def get_many(self, skus):
        """One round trip for up to MAX_BATCH products.

        `skus` is a list of SKUs in any letter case. Returns a dict that maps the canonical SKU
        of each product found to its Product. A SKU with no product is absent from the dict.

        The service rejects a malformed request. That raises ValueError, and still costs the
        round trip. A request is malformed when `skus` is not a list, is empty, holds more than
        MAX_BATCH SKUs, or names the same product twice, in any letter case.
        """
        self.calls.append(('get_many', len(skus) if isinstance(skus, list) else None))
        if not isinstance(skus, list) or not skus or len(skus) > self.MAX_BATCH:
            raise ValueError('malformed batch')
        wanted = [sku.upper() for sku in skus]
        if len(set(wanted)) != len(wanted):
            raise ValueError('malformed batch: a product is named twice')
        return {sku: self._products[sku] for sku in wanted if sku in self._products}
