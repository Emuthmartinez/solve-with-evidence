"""The product database, as an in-memory stand-in.

Production talks to a database where each call takes about 40 ms. This class has the same
contract and is what the tests use. Every call is recorded in `calls`, in order.

A product is a dict with exactly the keys `id`, `name`, `category` and `price_cents`. `id`,
`name` and `category` are non-empty strings. `price_cents` is an int from 0 to MAX_PRICE_CENTS.
A bool is not an int here.
"""

MAX_PRICE_CENTS = 1000000


class BackendError(Exception):
    """The backend rejected a write. It stored nothing."""


def valid(product):
    return (isinstance(product, dict) and set(product) == {'id', 'name', 'category', 'price_cents'}
            and all(isinstance(product[key], str) and product[key] for key in ('id', 'name', 'category'))
            and type(product['price_cents']) is int and 0 <= product['price_cents'] <= MAX_PRICE_CENTS)


class Backend:
    def __init__(self, products=()):
        self._rows = {product['id']: dict(product) for product in products}
        self.calls = []

    def get(self, product_id):
        """One call. Return a new dict for the product, or None when there is no such product."""
        self.calls.append(('get', product_id))
        row = self._rows.get(product_id)
        return None if row is None else dict(row)

    def ids_in_category(self, category):
        """One call. Return a new list of the ids of the products in `category`, sorted.

        A category with no products gives an empty list.
        """
        self.calls.append(('ids_in_category', category))
        return sorted(product_id for product_id, row in self._rows.items() if row['category'] == category)

    def put(self, product):
        """One call. Store a copy of `product` under its id, creating or replacing it. Return None.

        Raises BackendError, and stores nothing, when `product` is not a valid product. `put`
        does not check whether the id exists already.
        """
        self.calls.append(('put', product.get('id') if isinstance(product, dict) else None))
        if not valid(product):
            raise BackendError('invalid product: %r' % (product,))
        self._rows[product['id']] = dict(product)

    def delete(self, product_id):
        """One call. Remove the product. Return None.

        Raises KeyError, and changes nothing, when there is no such product.
        """
        self.calls.append(('delete', product_id))
        if product_id not in self._rows:
            raise KeyError(product_id)
        del self._rows[product_id]
