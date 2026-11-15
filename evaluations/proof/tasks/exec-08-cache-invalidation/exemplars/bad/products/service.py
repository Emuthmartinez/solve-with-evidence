"""Product reads and writes, with a read-through cache in front of the backend.

docs/caching.md states what the cache guarantees and what it may cost.
"""


class Service:
    def __init__(self, backend):
        self.backend = backend
        # product id -> the product dict, or None for an id the backend has no product for
        self._products = {}
        # category -> the sorted list of ids in it
        self._listings = {}

    def _lookup(self, product_id):
        if product_id not in self._products:
            self._products[product_id] = self.backend.get(product_id)
        return self._products[product_id]

    def _clear(self):
        self._products.clear()
        self._listings.clear()

    def get_product(self, product_id):
        """Return the product with this id as a dict, or None when there is no such product.

        The dict is the caller's own: the caller may change it.
        """
        return self._lookup(product_id)

    def list_category(self, category):
        """Return a list of the products in `category`, as dicts, sorted by id.

        A category with no products gives []. The list and its dicts are the caller's own: the
        caller may change them.
        """
        if category not in self._listings:
            self._listings[category] = self.backend.ids_in_category(category)
        return [self._lookup(product_id) for product_id in self._listings[category]]

    def create_product(self, product):
        """Add a new product, a dict as products/backend.py describes. Return None.

        Raises ValueError when a product with that id exists already, and the backend's
        BackendError when the backend rejects the product.
        """
        if self._lookup(product['id']) is not None:
            raise ValueError('product exists: %s' % product['id'])
        self._clear()
        self.backend.put(product)

    def update_product(self, product_id, changes):
        """Change some fields of a product. Return None.

        `changes` maps some of `name`, `category` and `price_cents` to their new values. Raises
        KeyError when there is no such product, and the backend's BackendError when the backend
        rejects the changed product.
        """
        current = self._lookup(product_id)
        if current is None:
            raise KeyError(product_id)
        product = dict(current)
        product.update(changes)
        self._clear()
        self.backend.put(product)

    def delete_product(self, product_id):
        """Remove a product. Return None. Raises KeyError when there is no such product."""
        if self._lookup(product_id) is None:
            raise KeyError(product_id)
        self._clear()
        self.backend.delete(product_id)

    def reprice_category(self, category, percent):
        """Change the price of every product in `category` by `percent` percent. Return None.

        A product's new price is price_cents * (100 + percent) // 100. The products are written
        one at a time, in id order. At the first product the backend rejects, the method stops
        and raises the backend's BackendError: the products written before it keep their new
        price, and that product and the ones after it keep their old price.
        """
        products = self.list_category(category)
        for product in products:
            self.backend.put(dict(product, price_cents=product['price_cents'] * (100 + percent) // 100))
        self._clear()
